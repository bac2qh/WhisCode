import argparse
import os
import queue
import signal
import sys
import threading
import time
import warnings
from enum import Enum
from pathlib import Path

from pynput import keyboard

from whiscode.handsfree import (
    DEFAULT_AUDIO_QUEUE_SECONDS,
    DEFAULT_COMMAND_CONFIG_PATH,
    DEFAULT_COMMAND_DIR,
    DEFAULT_COMMAND_CONFIRMATIONS,
    DEFAULT_COMMAND_THRESHOLD,
    DEFAULT_END_DIR,
    DEFAULT_END_THRESHOLD,
    DEFAULT_ACTIVE_LEVEL,
    DEFAULT_MAX_SECONDS,
    DEFAULT_MIN_ACTIVE_RATIO,
    DEFAULT_MIN_RMS,
    DEFAULT_SLIDE_SECONDS,
    DEFAULT_TAIL_SECONDS,
    DEFAULT_THRESHOLD,
    DEFAULT_WAKE_DIR,
    DEFAULT_WAKE_CONFIRMATIONS,
    DEFAULT_WINDOW_SECONDS,
    CommandConfigError,
    HandsFreeAudioLoop,
    HandsFreeSession,
    LocalWakeDetector,
    active_command_slots,
    command_label,
    command_reference_dirs,
    missing_reference_messages,
    reference_sample_count,
)
from whiscode.asr_engine_manager import AsrEngineManager
from whiscode.enroll import DEFAULT_ENROLL_SECONDS, record_guided_samples
from whiscode.external_transcription import (
    DEFAULT_EXTERNAL_POLL_SECONDS,
    DEFAULT_EXTERNAL_STABLE_SECONDS,
    ExternalAudioWatcher,
    ExternalConfigError,
    ExternalFileJob,
    ExternalFileQueue,
    ExternalTranscriptionConfig,
    SmbCredentials,
    build_external_storage,
    parse_external_extensions,
    process_external_transcription_job,
    watch_external_inbox,
)
from whiscode.hotwords import load_hotwords
from whiscode.injector import press_key_command, type_text
from whiscode.crispasr_asr import (
    CrispAsrBackend,
    CrispAsrServerConfig,
    default_crispasr_bin,
    default_crispasr_model_path,
)
from whiscode.llama_cpp_asr import (
    LlamaCppAsrBackend,
    LlamaCppServerConfig,
    default_llama_mmproj_path,
    default_llama_model_path,
    default_llama_server_bin,
)
from whiscode.mlx_vibevoice_asr import (
    DEFAULT_MLX_VIBEVOICE_MAX_TOKENS,
    DEFAULT_MLX_VIBEVOICE_PREFILL_STEP_SIZE,
    DEFAULT_MLX_VIBEVOICE_TEMPERATURE,
    MlxVibeVoiceBackend,
    MlxVibeVoiceConfig,
    default_mlx_vibevoice_model,
)
from whiscode.postprocess import postprocess, postprocess_for_refine
from whiscode.refiner import refine
from whiscode.recorder import Recorder, SAMPLE_RATE
from whiscode.recording_overlay import RecordingOverlayClient
from whiscode.reminders import start_reminders
from whiscode.stats import Stats
from whiscode.status_notifier import notify_recording_completed, notify_recording_now
from whiscode.telemetry import telemetry_from_args
from whiscode.transcriber import transcribe
from whiscode.transcription_queue import (
    DEFAULT_TRANSCRIPTION_QUEUE_CAPACITY,
    TranscriptionJob,
    TranscriptionJobQueue,
)

WHISPER_PROCESSOR_SOURCES = {
    "mlx-community/whisper-large-v3-mlx": "openai/whisper-large-v3",
    "mlx-community/whisper-large-v3-turbo": "openai/whisper-large-v3-turbo",
}


class State(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


def _format_transcript_for_stdout(text: str) -> str:
    return " ".join(text.split())


def _print_transcript_for_stdout(text: str) -> None:
    print()
    print(_format_transcript_for_stdout(text))
    print()


def parse_args(argv: list[str] | None = None):
    raw_argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description="WhisCode: Voice-to-keyboard for code dictation")
    parser.add_argument("--hotkey", default="shift_r", help="Toggle key for recording (default: shift_r)")
    parser.add_argument("--asr-backend", choices=("mlx-whisper", "mlx-vibevoice", "llama-cpp", "crispasr"), default="mlx-whisper", help="ASR backend to use (default: mlx-whisper; use mlx-vibevoice for VibeVoice; crispasr is legacy)")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-mlx", help="Whisper model to use")
    parser.add_argument("--language", default="auto", help="Language code, e.g. en, zh, ja, de (default: auto). Use 'auto' to detect from audio.")
    parser.add_argument("--prompt", default=None, help="Additional context prompt to improve transcription accuracy")
    parser.add_argument("--hotwords-file", default=None, help="Path to hotwords config file (default: ~/.config/whiscode/hotwords.txt)")
    parser.add_argument("--refine", action="store_true", help="Polish transcription with a local Ollama LLM (prose mode)")
    parser.add_argument("--refine-model", default="qwen3.5:4b", help="Ollama model for refinement (default: qwen3.5:4b)")
    parser.add_argument("--hands-free", action="store_true", help="Use local keyword detection instead of Right Shift as the primary trigger")
    parser.add_argument("--hands-free-wake-dir", type=Path, default=DEFAULT_WAKE_DIR, help=f"Wake phrase reference WAV folder (default: {DEFAULT_WAKE_DIR})")
    parser.add_argument("--hands-free-end-dir", type=Path, default=DEFAULT_END_DIR, help=f"End phrase reference WAV folder (default: {DEFAULT_END_DIR})")
    parser.add_argument("--hands-free-command-dir", type=Path, default=DEFAULT_COMMAND_DIR, help=f"Command phrase reference root folder (default: {DEFAULT_COMMAND_DIR})")
    parser.add_argument("--hands-free-command-config", type=Path, default=DEFAULT_COMMAND_CONFIG_PATH, help=f"Hands-free command enablement config (default: {DEFAULT_COMMAND_CONFIG_PATH})")
    parser.add_argument("--hands-free-threshold", type=float, default=None, help=f"Wake keyword detection threshold (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--hands-free-end-threshold", type=float, default=None, help=f"End keyword detection threshold (default: {DEFAULT_END_THRESHOLD})")
    parser.add_argument("--hands-free-command-threshold", type=float, default=None, help=f"Command keyword detection threshold (default: {DEFAULT_COMMAND_THRESHOLD})")
    parser.add_argument("--hands-free-window-seconds", type=float, default=DEFAULT_WINDOW_SECONDS, help=f"Detector window size in seconds (default: {DEFAULT_WINDOW_SECONDS})")
    parser.add_argument("--hands-free-slide-seconds", type=float, default=DEFAULT_SLIDE_SECONDS, help=f"Detector slide size in seconds (default: {DEFAULT_SLIDE_SECONDS})")
    parser.add_argument("--hands-free-tail-seconds", type=float, default=DEFAULT_TAIL_SECONDS, help=f"Audio tail to discard when the end phrase is detected (default: {DEFAULT_TAIL_SECONDS})")
    parser.add_argument("--max-recording-seconds", type=float, default=DEFAULT_MAX_SECONDS, help=f"Maximum recording length before timeout; 0 disables (default: {DEFAULT_MAX_SECONDS})")
    parser.add_argument("--hands-free-max-seconds", type=float, default=None, help="Legacy hands-free-only recording length limit; overrides --max-recording-seconds for hands-free when set")
    parser.add_argument("--hands-free-audio-queue-seconds", type=float, default=DEFAULT_AUDIO_QUEUE_SECONDS, help=f"Queued hands-free audio between mic capture and detection before oldest chunks are dropped (default: {DEFAULT_AUDIO_QUEUE_SECONDS})")
    parser.add_argument("--hands-free-min-rms", type=float, default=DEFAULT_MIN_RMS, help=f"Minimum detector-window RMS required before keyword matching (default: {DEFAULT_MIN_RMS})")
    parser.add_argument("--hands-free-min-active-ratio", type=float, default=DEFAULT_MIN_ACTIVE_RATIO, help=f"Minimum ratio of active samples required before keyword matching (default: {DEFAULT_MIN_ACTIVE_RATIO})")
    parser.add_argument("--hands-free-active-level", type=float, default=DEFAULT_ACTIVE_LEVEL, help=f"Absolute sample level counted as active for keyword matching (default: {DEFAULT_ACTIVE_LEVEL})")
    parser.add_argument("--hands-free-wake-confirmations", type=int, default=DEFAULT_WAKE_CONFIRMATIONS, help=f"Consecutive wake matches required before recording starts (default: {DEFAULT_WAKE_CONFIRMATIONS})")
    parser.add_argument("--hands-free-command-confirmations", type=int, default=DEFAULT_COMMAND_CONFIRMATIONS, help=f"Consecutive command matches required before pressing a key (default: {DEFAULT_COMMAND_CONFIRMATIONS})")
    parser.add_argument("--hands-free-debug", action="store_true", help="Print keyword detector distances for threshold tuning")
    parser.add_argument("--no-enroll-prompt", action="store_true", help="Exit instead of prompting to record missing hands-free samples")
    parser.add_argument("--enroll-samples", type=int, default=3, help="Samples per phrase for guided enrollment when --hands-free needs setup (default: 3)")
    parser.add_argument("--enroll-seconds", type=float, default=DEFAULT_ENROLL_SECONDS, help=f"Seconds per guided enrollment sample (default: {DEFAULT_ENROLL_SECONDS})")
    parser.add_argument("--telemetry-path", type=Path, default=None, help="Local JSONL telemetry path (default: ~/Library/Logs/WhisCode/events.jsonl)")
    parser.add_argument("--no-telemetry", action="store_true", help="Disable local telemetry")
    parser.add_argument("--llama-server-bin", type=Path, default=default_llama_server_bin(), help="Source-built llama-server binary for --asr-backend llama-cpp")
    parser.add_argument("--llama-model", type=Path, default=default_llama_model_path(), help="Qwen3-ASR GGUF model path for --asr-backend llama-cpp")
    parser.add_argument("--llama-mmproj", type=Path, default=default_llama_mmproj_path(), help="Qwen3-ASR mmproj GGUF path for --asr-backend llama-cpp")
    parser.add_argument("--llama-host", default="127.0.0.1", help="llama.cpp ASR server host (default: 127.0.0.1)")
    parser.add_argument("--llama-port", type=int, default=8091, help="llama.cpp ASR server port (default: 8091)")
    parser.add_argument("--llama-ctx", type=int, default=4096, help="llama.cpp context size for ASR server (default: 4096)")
    parser.add_argument("--llama-ngl", type=int, default=99, help="llama.cpp GPU layers for ASR server (default: 99)")
    parser.set_defaults(llama_autostart=True)
    parser.add_argument("--no-llama-autostart", dest="llama_autostart", action="store_false", help="Require an existing llama.cpp ASR server instead of starting one")
    parser.add_argument("--crispasr-bin", type=Path, default=default_crispasr_bin(), help="Legacy source-built crispasr binary for --asr-backend crispasr")
    parser.add_argument("--crispasr-model", type=Path, default=default_crispasr_model_path(), help="Legacy VibeVoice ASR GGUF model path for --asr-backend crispasr")
    parser.add_argument("--crispasr-backend", default="vibevoice", help="Legacy CrispASR backend name (default: vibevoice)")
    parser.add_argument("--crispasr-host", default="127.0.0.1", help="CrispASR server host (default: 127.0.0.1)")
    parser.add_argument("--crispasr-port", type=int, default=8092, help="CrispASR server port (default: 8092)")
    parser.add_argument("--crispasr-max-tokens", type=int, default=2048, help="CrispASR generated-token cap (default: 2048)")
    parser.add_argument("--crispasr-temperature", type=float, default=0.0, help="CrispASR sampling temperature (default: 0.0)")
    parser.add_argument("--crispasr-request-timeout", type=float, default=300.0, help="CrispASR transcription request timeout in seconds (default: 300)")
    parser.add_argument("--crispasr-startup-timeout", type=float, default=180.0, help="CrispASR server startup timeout in seconds (default: 180)")
    parser.set_defaults(crispasr_autostart=True)
    parser.add_argument("--no-crispasr-autostart", dest="crispasr_autostart", action="store_false", help="Require an existing CrispASR server instead of starting one")
    parser.add_argument("--mlx-vibevoice-model", default=default_mlx_vibevoice_model(), help="MLX VibeVoice ASR model path or Hugging Face repo (default: WHISCODE_MLX_VIBEVOICE_MODEL or ~/Documents/models/mlx-community/VibeVoice-ASR-8bit)")
    parser.add_argument("--mlx-vibevoice-max-tokens", type=int, default=DEFAULT_MLX_VIBEVOICE_MAX_TOKENS, help=f"MLX VibeVoice generated-token cap (default: {DEFAULT_MLX_VIBEVOICE_MAX_TOKENS})")
    parser.add_argument("--mlx-vibevoice-temperature", type=float, default=DEFAULT_MLX_VIBEVOICE_TEMPERATURE, help=f"MLX VibeVoice sampling temperature (default: {DEFAULT_MLX_VIBEVOICE_TEMPERATURE})")
    parser.add_argument("--mlx-vibevoice-prefill-step-size", type=int, default=DEFAULT_MLX_VIBEVOICE_PREFILL_STEP_SIZE, help=f"MLX VibeVoice prefill step size (default: {DEFAULT_MLX_VIBEVOICE_PREFILL_STEP_SIZE})")
    parser.set_defaults(recording_overlay=True)
    parser.add_argument("--recording-overlay", dest="recording_overlay", action="store_true", help="Show the floating recording stopwatch/waveform overlay (default)")
    parser.add_argument("--no-recording-overlay", dest="recording_overlay", action="store_false", help="Disable the floating recording overlay")
    parser.add_argument("--recording-notifications", action="store_true", help="Keep macOS start/end notification banners in addition to the overlay")
    parser.add_argument("--external-audio-inbox", default=_env_value("WHISCODE_EXTERNAL_AUDIO_INBOX"), help="Watch this folder or smb:// URL for external audio files to transcribe (mlx-vibevoice only)")
    parser.add_argument("--external-transcript-outbox", default=_env_value("WHISCODE_EXTERNAL_TRANSCRIPT_OUTBOX"), help="Folder or smb:// URL for external .txt/.json transcript results (default: sibling outbox)")
    parser.add_argument("--external-poll-seconds", type=float, default=_env_float("WHISCODE_EXTERNAL_POLL_SECONDS", DEFAULT_EXTERNAL_POLL_SECONDS), help=f"External inbox scan cadence in seconds (default: {DEFAULT_EXTERNAL_POLL_SECONDS})")
    parser.add_argument("--external-stable-seconds", type=float, default=_env_float("WHISCODE_EXTERNAL_STABLE_SECONDS", DEFAULT_EXTERNAL_STABLE_SECONDS), help=f"Seconds an external file must stop changing before queueing (default: {DEFAULT_EXTERNAL_STABLE_SECONDS})")
    args = parser.parse_args(argv)
    wake_threshold_supplied = "--hands-free-threshold" in raw_argv
    if args.hands_free_threshold is None:
        args.hands_free_threshold = DEFAULT_THRESHOLD
    if args.hands_free_end_threshold is None:
        args.hands_free_end_threshold = args.hands_free_threshold if wake_threshold_supplied else DEFAULT_END_THRESHOLD
    if args.hands_free_command_threshold is None:
        args.hands_free_command_threshold = args.hands_free_threshold if wake_threshold_supplied else DEFAULT_COMMAND_THRESHOLD
    if args.hands_free_max_seconds is None:
        args.hands_free_max_seconds = args.max_recording_seconds
    args.external_extensions = parse_external_extensions(os.environ.get("WHISCODE_EXTERNAL_EXTENSIONS"))
    if args.external_poll_seconds <= 0:
        parser.error("--external-poll-seconds must be greater than 0")
    if args.external_stable_seconds < 0:
        parser.error("--external-stable-seconds must be non-negative")
    return args


def _env_value(name: str) -> str | None:
    value = os.environ.get(name)
    return value if value else None


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _resolve_model_path(model_name: str) -> str:
    cache_dir = Path.home() / ".cache/huggingface/hub" / f"models--{model_name.replace('/', '--')}" / "snapshots/main"
    return str(cache_dir) if cache_dir.exists() else model_name


def _default_whisper_processor_source(model_name: str) -> str | None:
    return WHISPER_PROCESSOR_SOURCES.get(model_name)


def _is_whisper_model(model) -> bool:
    return ".whisper" in type(model).__module__


def ensure_whisper_processor(
    model,
    model_name: str,
    *,
    telemetry=None,
    processor_loader=None,
) -> None:
    if not _is_whisper_model(model):
        return
    if getattr(model, "_processor", None) is not None:
        if telemetry:
            telemetry.emit(
                "model.processor_fallback_skipped",
                reason="processor_present",
                model_family="whisper",
            )
        return

    processor_source = _default_whisper_processor_source(model_name)
    if processor_source is None:
        if telemetry:
            telemetry.emit(
                "model.processor_fallback_skipped",
                reason="no_processor_source",
                model_family="whisper",
            )
        raise RuntimeError(
            f"Whisper processor not found for model '{model_name}'. "
            "Use a model repo that includes Hugging Face processor/tokenizer files."
        )

    if telemetry:
        telemetry.emit(
            "model.processor_fallback_attempted",
            model_family="whisper",
            processor_source="openai",
        )
    try:
        if processor_loader is None:
            from transformers import WhisperProcessor

            processor_loader = WhisperProcessor.from_pretrained
        model._processor = processor_loader(processor_source)
    except Exception as e:
        if telemetry:
            telemetry.emit(
                "model.processor_fallback_failed",
                model_family="whisper",
                processor_source="openai",
                error_type=type(e).__name__,
            )
        raise RuntimeError(
            f"Whisper processor not found for model '{model_name}', and fallback "
            f"processor '{processor_source}' could not be loaded."
        ) from e

    if telemetry:
        telemetry.emit(
            "model.processor_fallback_completed",
            model_family="whisper",
            processor_source="openai",
        )


def resolve_active_command_slots(args, *, telemetry=None):
    slots = active_command_slots(args.hands_free_command_config, base_dir=args.hands_free_command_dir)
    config_exists = Path(args.hands_free_command_config).exists() if args.hands_free_command_config else False
    if telemetry:
        telemetry.emit(
            "handsfree.command_config_loaded",
            config_path=args.hands_free_command_config,
            config_exists=config_exists,
            enabled_commands=[slot.name for slot in slots],
            enabled_command_count=len(slots),
            disabled_command_count=len(command_reference_dirs(args.hands_free_command_dir)) - len(slots),
        )
    return slots


def ensure_hands_free_references(
    args,
    *,
    command_slots=None,
    input_fn=input,
    enroll_fn=record_guided_samples,
    telemetry=None,
) -> bool:
    if command_slots is None:
        command_slots = resolve_active_command_slots(args, telemetry=telemetry)
    wake_count = reference_sample_count(args.hands_free_wake_dir)
    end_count = reference_sample_count(args.hands_free_end_dir)
    command_dirs = command_reference_dirs(args.hands_free_command_dir, slots=tuple(command_slots))
    command_counts = {name: reference_sample_count(path) for name, path in command_dirs.items()}
    if telemetry:
        telemetry.emit(
            "handsfree.reference_check_started",
            wake_count=wake_count,
            end_count=end_count,
            command_counts=command_counts,
            minimum_samples=3,
            wake_dir=args.hands_free_wake_dir,
            end_dir=args.hands_free_end_dir,
            command_dir=args.hands_free_command_dir,
            enabled_command_count=len(command_dirs),
        )
    missing = missing_reference_messages(args.hands_free_wake_dir, args.hands_free_end_dir, command_dirs=command_dirs)
    if not missing:
        if telemetry:
            telemetry.emit("handsfree.reference_check_completed", outcome="complete")
        return True

    if telemetry:
        telemetry.emit("handsfree.reference_check_completed", outcome="missing", missing_count=len(missing))
    print("Hands-free enrollment is incomplete:")
    for message in missing:
        print(f"  {message}")

    command = "uv run whiscode-enroll --record"
    if args.no_enroll_prompt:
        if telemetry:
            telemetry.emit("handsfree.enrollment_prompt_skipped", reason="no_enroll_prompt")
        print(f"Run `{command}` to record samples, then start `uv run whiscode --hands-free` again.", file=sys.stderr)
        return False

    if telemetry:
        telemetry.emit("handsfree.enrollment_prompt_shown")
    answer = input_fn("Run guided enrollment now? [Y/n] ").strip().lower()
    if answer not in ("", "y", "yes"):
        if telemetry:
            telemetry.emit("handsfree.enrollment_prompt_declined")
        print(f"Run `{command}` when you are ready, then start `uv run whiscode --hands-free` again.")
        return False

    if telemetry:
        telemetry.emit("handsfree.enrollment_prompt_accepted")
    enroll_fn(
        wake_dir=args.hands_free_wake_dir,
        end_dir=args.hands_free_end_dir,
        command_dir=args.hands_free_command_dir,
        command_slots=tuple(command_slots),
        sample_count=args.enroll_samples,
        seconds=args.enroll_seconds,
        telemetry=telemetry,
    )

    missing = missing_reference_messages(args.hands_free_wake_dir, args.hands_free_end_dir, command_dirs=command_dirs)
    if missing:
        if telemetry:
            telemetry.emit("handsfree.reference_check_after_enrollment", outcome="missing", missing_count=len(missing))
        print("Hands-free enrollment is still incomplete:", file=sys.stderr)
        for message in missing:
            print(f"  {message}", file=sys.stderr)
        return False
    if telemetry:
        telemetry.emit("handsfree.reference_check_after_enrollment", outcome="complete")
    return True


def validate_external_intake_args(args) -> None:
    if args.external_audio_inbox is not None and args.asr_backend != "mlx-vibevoice":
        raise ValueError("external audio inbox support requires --asr-backend mlx-vibevoice")


def main():
    args = parse_args()
    telemetry = telemetry_from_args(args, default_enabled=runtime_telemetry_enabled_by_default(args))
    telemetry.emit("app.started", mode="hands_free" if args.hands_free else "hotkey")
    telemetry.emit("asr.backend_selected", backend=args.asr_backend)

    try:
        validate_external_intake_args(args)
    except ValueError as e:
        telemetry.emit(
            "app.failed",
            reason="external_backend_unsupported",
            backend=args.asr_backend,
        )
        print(f"Error: {e}.", file=sys.stderr)
        sys.exit(1)

    hotkey = getattr(keyboard.Key, args.hotkey, None)
    if hotkey is None:
        telemetry.emit("app.failed", reason="unknown_hotkey")
        print(f"Error: Unknown hotkey '{args.hotkey}'. Use keys like shift_r, f10, ctrl, alt, etc.")
        sys.exit(1)

    active_slots = ()
    if args.hands_free:
        try:
            active_slots = resolve_active_command_slots(args, telemetry=telemetry)
            references_complete = ensure_hands_free_references(args, command_slots=active_slots, telemetry=telemetry)
        except CommandConfigError as e:
            telemetry.emit("app.failed", reason="handsfree_command_config_invalid", error_type=type(e).__name__)
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        if not references_complete:
            telemetry.emit("app.failed", reason="handsfree_references_incomplete")
            sys.exit(1)

    hotwords_path = Path(args.hotwords_file) if args.hotwords_file else None
    hot_words, replacements = load_hotwords(hotwords_path) if hotwords_path else load_hotwords()
    if hot_words or replacements:
        print(f"Loaded {len(hot_words)} hot word(s) and {len(replacements)} replacement(s).")

    asr_backend = None
    if args.asr_backend == "mlx-whisper":
        model_path = _resolve_model_path(args.model)
        telemetry.emit("model.load_started")
        print(f"Loading model: {model_path} ...")
        from mlx_audio.stt.utils import load_model
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"Could not load WhisperProcessor:.*",
                    category=UserWarning,
                    module="mlx_audio.stt.models.whisper.whisper",
                )
                model = load_model(model_path)
            ensure_whisper_processor(model, args.model, telemetry=telemetry)
        except Exception as e:
            telemetry.emit("model.load_failed", error_type=type(e).__name__)
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        telemetry.emit("model.load_completed")

        def transcribe_audio(audio, progress_callback=None):
            return transcribe(
                model,
                audio,
                language=args.language,
                extra_prompt=args.prompt,
                hotwords=hot_words,
                progress_callback=progress_callback,
            )

        print(f"Model loaded. Press {args.hotkey} to start/stop recording.")
    elif args.asr_backend == "mlx-vibevoice":
        config = MlxVibeVoiceConfig(
            model=args.mlx_vibevoice_model,
            max_tokens=args.mlx_vibevoice_max_tokens,
            temperature=args.mlx_vibevoice_temperature,
            prefill_step_size=args.mlx_vibevoice_prefill_step_size,
        )
        primary_vibevoice_backend = MlxVibeVoiceBackend(config, telemetry=telemetry)
        try:
            print(f"Loading MLX VibeVoice model: {primary_vibevoice_backend.model_location} ...")
            primary_vibevoice_backend.start()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        def create_vibevoice_engine():
            engine = MlxVibeVoiceBackend(config, telemetry=telemetry)
            engine.start()
            return engine

        asr_backend = AsrEngineManager(
            primary_engine=primary_vibevoice_backend,
            engine_factory=create_vibevoice_engine,
            telemetry=telemetry,
        )

        def transcribe_audio(audio, progress_callback=None):
            return asr_backend.transcribe_manual(
                audio,
                language=args.language,
                extra_prompt=args.prompt,
                hotwords=hot_words,
                progress_callback=progress_callback,
            )

        print(f"MLX VibeVoice ready ({asr_backend.model_label}). Press {args.hotkey} to start/stop recording.")
    elif args.asr_backend == "llama-cpp":
        config = LlamaCppServerConfig(
            server_bin=args.llama_server_bin.expanduser(),
            model=args.llama_model.expanduser(),
            mmproj=args.llama_mmproj.expanduser(),
            host=args.llama_host,
            port=args.llama_port,
            ctx=args.llama_ctx,
            ngl=args.llama_ngl,
            autostart=args.llama_autostart,
        )
        asr_backend = LlamaCppAsrBackend(config, telemetry=telemetry)
        try:
            asr_backend.start()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        def transcribe_audio(audio, progress_callback=None):
            return asr_backend.transcribe(
                audio,
                language=args.language,
                extra_prompt=args.prompt,
                hotwords=hot_words,
                progress_callback=progress_callback,
            )

        print(f"llama.cpp ASR ready at {args.llama_host}:{args.llama_port}. Press {args.hotkey} to start/stop recording.")
    elif args.asr_backend == "crispasr":
        print("Warning: --asr-backend crispasr is legacy; prefer --asr-backend mlx-vibevoice for local VibeVoice ASR.")
        config = CrispAsrServerConfig(
            server_bin=args.crispasr_bin.expanduser(),
            model=args.crispasr_model.expanduser(),
            backend=args.crispasr_backend,
            host=args.crispasr_host,
            port=args.crispasr_port,
            autostart=args.crispasr_autostart,
            max_tokens=args.crispasr_max_tokens,
            temperature=args.crispasr_temperature,
            startup_timeout_seconds=args.crispasr_startup_timeout,
            request_timeout_seconds=args.crispasr_request_timeout,
        )
        asr_backend = CrispAsrBackend(config, telemetry=telemetry)
        try:
            asr_backend.start()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        def transcribe_audio(audio, progress_callback=None):
            return asr_backend.transcribe(
                audio,
                language=args.language,
                extra_prompt=args.prompt,
                hotwords=hot_words,
                progress_callback=progress_callback,
            )

        print(f"CrispASR ready at {args.crispasr_host}:{args.crispasr_port}. Press {args.hotkey} to start/stop recording.")
    else:
        print(f"Error: Unknown ASR backend '{args.asr_backend}'.", file=sys.stderr)
        sys.exit(1)
    if args.refine:
        print(f"Refine mode: ON (model: {args.refine_model})")

    stats = Stats()
    start_reminders(stats)
    overlay = RecordingOverlayClient(enabled=args.recording_overlay, telemetry=telemetry)
    transcription_jobs = TranscriptionJobQueue(capacity=DEFAULT_TRANSCRIPTION_QUEUE_CAPACITY)
    external_storage = None
    if args.external_audio_inbox is not None:
        try:
            external_storage = build_external_storage(
                inbox=args.external_audio_inbox,
                outbox=args.external_transcript_outbox,
                smb_credentials=_smb_credentials_from_env(),
            )
        except ExternalConfigError as e:
            telemetry.emit("app.failed", reason="external_config_invalid", error_type=type(e).__name__)
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    external_queue = ExternalFileQueue() if args.external_audio_inbox is not None else None
    external_config = (
        ExternalTranscriptionConfig(
            storage=external_storage,
            extensions=args.external_extensions,
            poll_seconds=args.external_poll_seconds,
            stable_seconds=args.external_stable_seconds,
        )
        if external_storage is not None
        else None
    )

    state = State.IDLE
    state_lock = threading.Lock()
    shutdown_event = threading.Event()
    hotkey_queue = queue.Queue()
    handsfree_queue = queue.Queue()
    recorder = Recorder(
        level_callback=overlay.update_level,
        max_seconds=args.max_recording_seconds,
        timeout_callback=lambda: hotkey_queue.put_nowait("timeout"),
    )
    handsfree_session = None
    handsfree_loop = None
    last_hotkey_time = 0.0
    handsfree_cycle_times: list[float] = []
    DEBOUNCE_SECONDS = 0.3
    LOOP_WINDOW_SECONDS = 30.0
    LOOP_EVENT_COUNT = 3

    def transition_to(new_state, source, **properties):
        nonlocal state
        if state == new_state:
            return
        previous = state
        state = new_state
        telemetry.emit(
            "app.state_transition",
            from_state=previous.value,
            to_state=new_state.value,
            source=source,
            **properties,
        )

    def refresh_state_from_queue(source: str) -> None:
        if transcription_jobs.is_recording_reserved():
            transition_to(State.RECORDING, source)
        elif transcription_jobs.has_transcription_work():
            transition_to(State.TRANSCRIBING, source)
        else:
            transition_to(State.IDLE, source)

    def reject_recording_start(source: str) -> None:
        queue_depth = transcription_jobs.queue_depth_for_telemetry()
        telemetry.emit(
            "recording.queue_full",
            source=source,
            queue_depth=queue_depth,
            queue_capacity=DEFAULT_TRANSCRIPTION_QUEUE_CAPACITY,
        )
        print("Recording queue full; wait for transcription to catch up.")

    def reserve_recording(source: str):
        reservation = transcription_jobs.try_reserve_recording(source=source)
        if reservation is None:
            reject_recording_start(source)
            return None
        return reservation

    def enqueue_recording(audio, audio_seconds: float, job_id: str, *, timeout_event: str | None = None) -> TranscriptionJob | None:
        job = transcription_jobs.finish_recording(audio=audio, audio_seconds=audio_seconds, job_id=job_id)
        if job is None:
            overlay.remove_item(job_id)
            reject_recording_start("enqueue")
            return None
        overlay.show_queued_item(job.job_id, audio_seconds=job.audio_seconds)
        telemetry.emit(
            "recording.queued",
            job_id=job.job_id,
            source=job.source,
            queue_depth=transcription_jobs.queue_depth_for_telemetry(),
            audio_seconds=round(job.audio_seconds, 3),
        )
        if timeout_event == "hotkey":
            print(f"Recording limit reached at {audio_seconds:.2f}s.")
            telemetry.emit(
                "recording.timeout",
                mode="hotkey",
                max_seconds=args.max_recording_seconds,
                audio_seconds=round(audio_seconds, 3),
            )
        print(f"Queued recording {job.job_id} ({audio_seconds:.2f}s).")
        refresh_state_from_queue("recording.queued")
        return job

    def record_handsfree_cycle(reason: str, duration_seconds: float) -> None:
        now = time.monotonic()
        handsfree_cycle_times.append(now)
        while handsfree_cycle_times and now - handsfree_cycle_times[0] > LOOP_WINDOW_SECONDS:
            handsfree_cycle_times.pop(0)
        if len(handsfree_cycle_times) >= LOOP_EVENT_COUNT:
            telemetry.emit(
                "handsfree.loop_suspected",
                cycles=len(handsfree_cycle_times),
                window_seconds=LOOP_WINDOW_SECONDS,
                last_reason=reason,
                last_audio_seconds=round(duration_seconds, 3),
            )

    def on_press(key):
        nonlocal last_hotkey_time
        if key != hotkey:
            return
        now = time.monotonic()
        if now - last_hotkey_time < DEBOUNCE_SECONDS:
            return
        last_hotkey_time = now
        hotkey_queue.put_nowait("toggle")

    def show_recording_status(job_id: str) -> None:
        overlay.show_recording_item(job_id)
        if args.recording_notifications:
            notify_recording_now()

    def notify_recording_stopped() -> None:
        if args.recording_notifications:
            notify_recording_completed()

    def process_transcription_job(job: TranscriptionJob) -> None:
        started = time.monotonic()
        progress_state = {"total_frames": None}

        def update_transcription_overlay(**progress) -> None:
            total_frames = progress.get("total_frames")
            if total_frames is not None:
                progress_state["total_frames"] = total_frames
            overlay.update_transcription_progress(item_id=job.job_id, **progress)

        overlay.show_transcribing_item(job.job_id, audio_seconds=job.audio_seconds)
        queue_depth = transcription_jobs.queue_depth_for_telemetry()
        telemetry.emit(
            "transcription.queue_started",
            job_id=job.job_id,
            source=job.source,
            queue_depth=queue_depth,
            audio_seconds=round(job.audio_seconds, 3),
        )
        telemetry.emit("transcription.started", audio_seconds=round(job.audio_seconds, 3), audio_samples=len(job.audio))
        print(f"Transcribing {job.job_id}...")
        try:
            text = transcribe_audio(job.audio, progress_callback=update_transcription_overlay)
            if progress_state["total_frames"] is not None:
                overlay.update_transcription_progress(
                    item_id=job.job_id,
                    current_frames=progress_state["total_frames"],
                    total_frames=progress_state["total_frames"],
                )
            if text:
                if args.refine:
                    processed = postprocess_for_refine(text, replacements=replacements)
                    print("  Refining...")
                    processed = refine(processed, model=args.refine_model)
                else:
                    processed = postprocess(text, replacements=replacements)
                word_count = len(processed.split())
                stats.record(word_count, job.audio_seconds)
                _print_transcript_for_stdout(processed)
                type_text(processed)
                duration_seconds = round(time.monotonic() - started, 3)
                telemetry.emit(
                    "transcription.completed",
                    outcome="typed",
                    duration_seconds=duration_seconds,
                    audio_seconds=round(job.audio_seconds, 3),
                    word_count=word_count,
                    refined=args.refine,
                )
                telemetry.emit(
                    "transcription.queue_completed",
                    job_id=job.job_id,
                    source=job.source,
                    outcome="typed",
                    duration_seconds=duration_seconds,
                    queue_depth=transcription_jobs.queue_depth_for_telemetry(),
                )
            else:
                print("  (no speech detected)")
                duration_seconds = round(time.monotonic() - started, 3)
                telemetry.emit(
                    "transcription.completed",
                    outcome="empty",
                    duration_seconds=duration_seconds,
                    audio_seconds=round(job.audio_seconds, 3),
                )
                telemetry.emit(
                    "transcription.queue_completed",
                    job_id=job.job_id,
                    source=job.source,
                    outcome="empty",
                    duration_seconds=duration_seconds,
                    queue_depth=transcription_jobs.queue_depth_for_telemetry(),
                )
        except Exception as e:
            duration_seconds = round(time.monotonic() - started, 3)
            telemetry.emit(
                "transcription.failed",
                duration_seconds=duration_seconds,
                audio_seconds=round(job.audio_seconds, 3),
                error_type=type(e).__name__,
            )
            telemetry.emit(
                "transcription.queue_failed",
                job_id=job.job_id,
                source=job.source,
                duration_seconds=duration_seconds,
                queue_depth=transcription_jobs.queue_depth_for_telemetry(),
                error_type=type(e).__name__,
            )
            print(f"  Error: {e}", file=sys.stderr)
        finally:
            overlay.remove_item(job.job_id)

    def transcription_worker():
        while not shutdown_event.is_set():
            job = transcription_jobs.get(timeout=0.2)
            if job is None:
                continue
            with state_lock:
                refresh_state_from_queue("transcription.queue_started")
            try:
                process_transcription_job(job)
            finally:
                transcription_jobs.complete_active(job.job_id)
                with state_lock:
                    refresh_state_from_queue("transcription.queue_finished")

    def process_external_file(job: ExternalFileJob) -> None:
        if external_config is None or asr_backend is None:
            return
        started = time.monotonic()
        audio_seconds = None
        telemetry.emit(
            "external.transcription_started",
            file_id=job.file_id,
            extension=job.extension,
            size_bytes=job.size_bytes,
            storage_scheme=external_config.storage.scheme,
            backend=asr_backend.backend_name,
            model=asr_backend.model_label,
        )
        try:
            result = process_external_transcription_job(
                external_config,
                job,
                transcribe_audio=lambda audio: asr_backend.transcribe_external(audio, language=args.language),
                backend=asr_backend.backend_name,
                model_label=asr_backend.model_label,
            )
        except Exception as e:
            telemetry.emit(
                "external.transcription_failed",
                file_id=job.file_id,
                extension=job.extension,
                size_bytes=job.size_bytes,
                storage_scheme=external_config.storage.scheme,
                audio_seconds=round(audio_seconds, 3) if audio_seconds is not None else None,
                duration_seconds=round(time.monotonic() - started, 3),
                backend=asr_backend.backend_name,
                model=asr_backend.model_label,
                error_type=type(e).__name__,
            )
            print(f"External transcription failed for {job.basename}: {e}", file=sys.stderr)
            return

        audio_seconds = result.audio_seconds
        if result.status == "failed":
            telemetry.emit(
                "external.transcription_failed",
                file_id=job.file_id,
                extension=job.extension,
                size_bytes=job.size_bytes,
                storage_scheme=external_config.storage.scheme,
                audio_seconds=round(audio_seconds, 3) if audio_seconds is not None else None,
                duration_seconds=round(result.processing_seconds, 3),
                backend=asr_backend.backend_name,
                model=asr_backend.model_label,
                error_type=result.error_type or "ExternalTranscriptionError",
            )
            print(f"External transcription failed for {job.basename}.", file=sys.stderr)
            return

        telemetry.emit(
            "external.transcription_completed",
            file_id=job.file_id,
            extension=job.extension,
            size_bytes=job.size_bytes,
            storage_scheme=external_config.storage.scheme,
            audio_seconds=round(audio_seconds, 3) if audio_seconds is not None else None,
            duration_seconds=round(result.processing_seconds, 3),
            backend=asr_backend.backend_name,
            model=asr_backend.model_label,
            output_chars=len(result.transcript),
        )
        print(f"External transcript completed for {job.basename}.")

    def external_worker():
        if external_queue is None:
            return
        while not shutdown_event.is_set():
            if not transcription_jobs.is_idle():
                shutdown_event.wait(0.2)
                continue
            job = external_queue.get(timeout=0.2)
            if job is None:
                continue
            try:
                if not transcription_jobs.is_idle():
                    external_queue.requeue(job)
                    shutdown_event.wait(0.2)
                    continue
                process_external_file(job)
            finally:
                external_queue.complete()

    def hotkey_worker():
        nonlocal state
        while not shutdown_event.is_set():
            try:
                event = hotkey_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            with state_lock:
                if event == "timeout" and state != State.RECORDING:
                    telemetry.emit("recording.timeout_ignored", reason=state.value)
                    continue

                if state in {State.IDLE, State.TRANSCRIBING}:
                    if event == "timeout":
                        continue
                    reservation = reserve_recording("hotkey")
                    if reservation is None:
                        continue
                    transition_to(State.RECORDING, "hotkey")
                    recorder.start()
                    show_recording_status(reservation.job_id)
                    print("Recording...")

                elif state == State.RECORDING:
                    job_id = transcription_jobs.reserved_job_id()
                    if job_id is None:
                        telemetry.emit("recording.stop_ignored", reason="missing_reservation")
                        continue
                    transition_to(State.TRANSCRIBING, "recording_timeout" if event == "timeout" else "hotkey")
                    audio = recorder.stop()
                    audio_seconds = len(audio) / SAMPLE_RATE
                    notify_recording_stopped()
                    enqueue_recording(
                        audio,
                        audio_seconds,
                        job_id,
                        timeout_event="hotkey" if event == "timeout" else None,
                    )

    def handsfree_worker():
        while not shutdown_event.is_set():
            handled = False
            try:
                hotkey_queue.get(timeout=0.05)
                handled = True
                handle_handsfree_hotkey()
            except queue.Empty:
                pass

            try:
                event = handsfree_queue.get(timeout=0.05)
                handled = True
                handle_handsfree_event(event)
            except queue.Empty:
                pass

            if not handled:
                time.sleep(0.01)

    def handle_handsfree_hotkey():
        nonlocal state
        with state_lock:
            if state in {State.IDLE, State.TRANSCRIBING}:
                reservation = reserve_recording("manual_handsfree_hotkey")
                if reservation is None:
                    return
                transition_to(State.RECORDING, "manual_handsfree_hotkey")
                handsfree_session.manual_start()
                show_recording_status(reservation.job_id)
                print("Recording... (manual)")

            elif state == State.RECORDING:
                job_id = transcription_jobs.reserved_job_id()
                if job_id is None:
                    telemetry.emit("recording.stop_ignored", reason="missing_reservation")
                    return
                event = handsfree_session.manual_stop()
                transition_to(State.TRANSCRIBING, "manual_handsfree_hotkey", audio_seconds=round(event.duration_seconds, 3))
                notify_recording_stopped()
                enqueue_recording(event.audio, event.duration_seconds, job_id)

    def handle_handsfree_event(event):
        nonlocal state
        with state_lock:
            if event.kind == "command.detected":
                if state != State.RECORDING and event.command:
                    label = command_label(event.command)
                    telemetry.emit(
                        "handsfree.command_detected",
                        command=event.command,
                        distance=round(event.detection.distance, 6) if event.detection else None,
                        threshold=args.hands_free_command_threshold,
                        rms=round(event.detection.rms, 6) if event.detection and event.detection.rms is not None else None,
                        active_ratio=round(event.detection.active_ratio, 6) if event.detection and event.detection.active_ratio is not None else None,
                    )
                    try:
                        press_key_command(event.command)
                    except Exception as e:
                        telemetry.emit("keyboard_command.failed", command=event.command, error_type=type(e).__name__)
                        print(f"handsfree.command.failed command={event.command} error={e}", file=sys.stderr)
                    else:
                        telemetry.emit("keyboard_command.injected", command=event.command, outcome="pressed")
                        print(f"handsfree.command.detected command={event.command} key={label}")
                return

            if event.kind == "wake.detected":
                if state in {State.IDLE, State.TRANSCRIBING}:
                    reservation = reserve_recording("handsfree_wake")
                    if reservation is None:
                        handsfree_session.reset_idle()
                        refresh_state_from_queue("handsfree_wake_queue_full")
                        return
                    transition_to(
                        State.RECORDING,
                        "handsfree_wake",
                        detection_distance=round(event.detection.distance, 6) if event.detection else None,
                    )
                    show_recording_status(reservation.job_id)
                    print(f"handsfree.wake.detected distance={event.detection.distance:.4f}")
                    print("Recording...")
                    telemetry.emit(
                        "handsfree.wake_detected",
                        distance=round(event.detection.distance, 6) if event.detection else None,
                        threshold=args.hands_free_threshold,
                        rms=round(event.detection.rms, 6) if event.detection and event.detection.rms is not None else None,
                        active_ratio=round(event.detection.active_ratio, 6) if event.detection and event.detection.active_ratio is not None else None,
                    )
                return

            if event.kind in {"end.detected", "timeout"}:
                if state == State.RECORDING:
                    job_id = transcription_jobs.reserved_job_id()
                    if job_id is None:
                        telemetry.emit("recording.stop_ignored", reason="missing_reservation")
                        handsfree_session.reset_idle()
                        refresh_state_from_queue(f"handsfree_{event.kind}_missing_reservation")
                        return
                    transition_to(State.TRANSCRIBING, f"handsfree_{event.kind}", audio_seconds=round(event.duration_seconds, 3))
                    notify_recording_stopped()
                    if event.kind == "timeout":
                        print(f"handsfree.timeout seconds={event.duration_seconds:.2f}")
                        telemetry.emit("handsfree.timeout", audio_seconds=round(event.duration_seconds, 3))
                    else:
                        print(f"handsfree.end.detected distance={event.detection.distance:.4f}")
                        telemetry.emit(
                            "handsfree.end_detected",
                            distance=round(event.detection.distance, 6) if event.detection else None,
                            threshold=args.hands_free_end_threshold,
                            audio_seconds=round(event.duration_seconds, 3),
                            rms=round(event.detection.rms, 6) if event.detection and event.detection.rms is not None else None,
                            active_ratio=round(event.detection.active_ratio, 6) if event.detection and event.detection.active_ratio is not None else None,
                        )
                    record_handsfree_cycle(event.kind, event.duration_seconds)
                    enqueue_recording(event.audio, event.duration_seconds, job_id)
                return

            if event.kind == "detector.error":
                telemetry.emit("handsfree.detector_error")
                print("handsfree.detector.error", file=sys.stderr)

    ctrl_c_count = 0
    last_signal = None

    def handle_signal(signum, frame):
        nonlocal ctrl_c_count, last_signal
        ctrl_c_count += 1
        last_signal = signum
        shutdown_event.set()
        if ctrl_c_count >= 2:
            os._exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    threading.Thread(target=transcription_worker, daemon=True).start()
    if external_config is not None and external_queue is not None:
        watcher = ExternalAudioWatcher(external_config, external_queue, telemetry=telemetry)
        threading.Thread(target=watch_external_inbox, kwargs={"watcher": watcher, "stop_event": shutdown_event}, daemon=True).start()
        threading.Thread(target=external_worker, daemon=True).start()
        print(f"External audio inbox enabled: {external_config.storage.safe_description()}")

    if args.hands_free:
        try:
            telemetry.emit(
                "handsfree.detector_load_started",
                wake_threshold=args.hands_free_threshold,
                end_threshold=args.hands_free_end_threshold,
                command_threshold=args.hands_free_command_threshold,
                command_count=len(active_slots),
            )
            wake_detector = LocalWakeDetector(args.hands_free_wake_dir, args.hands_free_threshold)
            end_detector = LocalWakeDetector(args.hands_free_end_dir, args.hands_free_end_threshold)
            command_detectors = {
                name: LocalWakeDetector(path, args.hands_free_command_threshold)
                for name, path in command_reference_dirs(args.hands_free_command_dir, slots=tuple(active_slots)).items()
            }
            telemetry.emit("handsfree.detector_load_completed")
        except ValueError as e:
            telemetry.emit("handsfree.detector_load_failed", error_type=type(e).__name__)
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        handsfree_session = HandsFreeSession(
            wake_detector,
            end_detector,
            window_seconds=args.hands_free_window_seconds,
            slide_seconds=args.hands_free_slide_seconds,
            tail_seconds=args.hands_free_tail_seconds,
            max_seconds=args.hands_free_max_seconds,
            debug=args.hands_free_debug,
            telemetry=telemetry,
            min_rms=args.hands_free_min_rms,
            min_active_ratio=args.hands_free_min_active_ratio,
            active_level=args.hands_free_active_level,
            wake_confirmations=args.hands_free_wake_confirmations,
            command_detectors=command_detectors,
            command_confirmations=args.hands_free_command_confirmations,
            level_callback=overlay.update_level,
        )
        handsfree_loop = HandsFreeAudioLoop(
            handsfree_session,
            handsfree_queue,
            stop_event=shutdown_event,
            telemetry=telemetry,
            audio_queue_seconds=args.hands_free_audio_queue_seconds,
        )
        handsfree_loop.start()
        print("Hands-free mode enabled. Right Shift remains available as a fallback.")
        threading.Thread(target=handsfree_worker, daemon=True).start()
    else:
        threading.Thread(target=hotkey_worker, daemon=True).start()

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    try:
        while listener.is_alive() and not shutdown_event.is_set():
            listener.join(timeout=0.5)
    finally:
        if last_signal is not None:
            telemetry.emit("app.signal_received", signal=last_signal, count=ctrl_c_count)

        listener.stop()

        if handsfree_loop:
            handsfree_loop.join(timeout=1.0)

        overlay.stop()
        if asr_backend is not None:
            asr_backend.close()

        with state_lock:
            if not args.hands_free and state == State.RECORDING:
                job_id = transcription_jobs.reserved_job_id()
                if job_id is not None:
                    transcription_jobs.cancel_recording(job_id)
                    overlay.remove_item(job_id)
                recorder.stop()

        print(f"\nSession stats: {stats.summary()}")
        telemetry.emit("app.exiting", stats=stats.summary())
        print("Exiting.")


def runtime_telemetry_enabled_by_default(args) -> bool:
    del args
    return True


def _smb_credentials_from_env() -> SmbCredentials | None:
    username = os.environ.get("WHISCODE_EXTERNAL_SMB_USERNAME")
    password = os.environ.get("WHISCODE_EXTERNAL_SMB_PASSWORD")
    if not username and not password:
        return None
    if not username or not password:
        raise ExternalConfigError("SMB external intake requires both WHISCODE_EXTERNAL_SMB_USERNAME and WHISCODE_EXTERNAL_SMB_PASSWORD")
    return SmbCredentials(
        username=username,
        password=password,
        domain=os.environ.get("WHISCODE_EXTERNAL_SMB_DOMAIN") or None,
    )


if __name__ == "__main__":
    main()
