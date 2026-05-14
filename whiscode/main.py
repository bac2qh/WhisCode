import argparse
import os
import queue
import signal
import sys
import threading
import time
from enum import Enum
from pathlib import Path

from pynput import keyboard

from whiscode.handsfree import (
    DEFAULT_END_DIR,
    DEFAULT_ACTIVE_LEVEL,
    DEFAULT_MAX_SECONDS,
    DEFAULT_MIN_ACTIVE_RATIO,
    DEFAULT_MIN_RMS,
    DEFAULT_SLIDE_SECONDS,
    DEFAULT_TAIL_SECONDS,
    DEFAULT_THRESHOLD,
    DEFAULT_WAKE_DIR,
    DEFAULT_WINDOW_SECONDS,
    HandsFreeAudioLoop,
    HandsFreeSession,
    LocalWakeDetector,
    missing_reference_messages,
    reference_sample_count,
)
from whiscode.enroll import DEFAULT_ENROLL_SECONDS, record_guided_samples
from whiscode.hotwords import load_hotwords
from whiscode.injector import type_text
from whiscode.postprocess import postprocess, postprocess_for_refine
from whiscode.refiner import refine
from whiscode.recorder import Recorder, SAMPLE_RATE
from whiscode.reminders import start_reminders
from whiscode.stats import Stats
from whiscode.status_notifier import notify_recording_completed, notify_recording_now
from whiscode.telemetry import telemetry_from_args
from whiscode.transcriber import transcribe


class State(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="WhisCode: Voice-to-keyboard for code dictation")
    parser.add_argument("--hotkey", default="shift_r", help="Toggle key for recording (default: shift_r)")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-turbo", help="Whisper model to use")
    parser.add_argument("--language", default="auto", help="Language code, e.g. en, zh, ja, de (default: auto). Use 'auto' to detect from audio.")
    parser.add_argument("--prompt", default=None, help="Additional context prompt to improve transcription accuracy")
    parser.add_argument("--hotwords-file", default=None, help="Path to hotwords config file (default: ~/.config/whiscode/hotwords.txt)")
    parser.add_argument("--refine", action="store_true", help="Polish transcription with a local Ollama LLM (prose mode)")
    parser.add_argument("--refine-model", default="qwen3.5:4b", help="Ollama model for refinement (default: qwen3.5:4b)")
    parser.add_argument("--hands-free", action="store_true", help="Use local keyword detection instead of Right Shift as the primary trigger")
    parser.add_argument("--hands-free-wake-dir", type=Path, default=DEFAULT_WAKE_DIR, help=f"Wake phrase reference WAV folder (default: {DEFAULT_WAKE_DIR})")
    parser.add_argument("--hands-free-end-dir", type=Path, default=DEFAULT_END_DIR, help=f"End phrase reference WAV folder (default: {DEFAULT_END_DIR})")
    parser.add_argument("--hands-free-threshold", type=float, default=DEFAULT_THRESHOLD, help=f"Keyword detection threshold (default: {DEFAULT_THRESHOLD})")
    parser.add_argument("--hands-free-window-seconds", type=float, default=DEFAULT_WINDOW_SECONDS, help=f"Detector window size in seconds (default: {DEFAULT_WINDOW_SECONDS})")
    parser.add_argument("--hands-free-slide-seconds", type=float, default=DEFAULT_SLIDE_SECONDS, help=f"Detector slide size in seconds (default: {DEFAULT_SLIDE_SECONDS})")
    parser.add_argument("--hands-free-tail-seconds", type=float, default=DEFAULT_TAIL_SECONDS, help=f"Audio tail to discard when the end phrase is detected (default: {DEFAULT_TAIL_SECONDS})")
    parser.add_argument("--hands-free-max-seconds", type=float, default=DEFAULT_MAX_SECONDS, help=f"Maximum recording length before timeout; 0 disables (default: {DEFAULT_MAX_SECONDS})")
    parser.add_argument("--hands-free-min-rms", type=float, default=DEFAULT_MIN_RMS, help=f"Minimum detector-window RMS required before keyword matching (default: {DEFAULT_MIN_RMS})")
    parser.add_argument("--hands-free-min-active-ratio", type=float, default=DEFAULT_MIN_ACTIVE_RATIO, help=f"Minimum ratio of active samples required before keyword matching (default: {DEFAULT_MIN_ACTIVE_RATIO})")
    parser.add_argument("--hands-free-active-level", type=float, default=DEFAULT_ACTIVE_LEVEL, help=f"Absolute sample level counted as active for keyword matching (default: {DEFAULT_ACTIVE_LEVEL})")
    parser.add_argument("--hands-free-debug", action="store_true", help="Print keyword detector distances for threshold tuning")
    parser.add_argument("--no-enroll-prompt", action="store_true", help="Exit instead of prompting to record missing hands-free samples")
    parser.add_argument("--enroll-samples", type=int, default=3, help="Samples per phrase for guided enrollment when --hands-free needs setup (default: 3)")
    parser.add_argument("--enroll-seconds", type=float, default=DEFAULT_ENROLL_SECONDS, help=f"Seconds per guided enrollment sample (default: {DEFAULT_ENROLL_SECONDS})")
    parser.add_argument("--telemetry-path", type=Path, default=None, help="Local JSONL telemetry path (default: ~/.config/whiscode/telemetry/events.jsonl)")
    parser.add_argument("--no-telemetry", action="store_true", help="Disable local telemetry")
    return parser.parse_args(argv)


def _resolve_model_path(model_name: str) -> str:
    cache_dir = Path.home() / ".cache/huggingface/hub" / f"models--{model_name.replace('/', '--')}" / "snapshots/main"
    return str(cache_dir) if cache_dir.exists() else model_name


def ensure_hands_free_references(args, *, input_fn=input, enroll_fn=record_guided_samples, telemetry=None) -> bool:
    wake_count = reference_sample_count(args.hands_free_wake_dir)
    end_count = reference_sample_count(args.hands_free_end_dir)
    if telemetry:
        telemetry.emit(
            "handsfree.reference_check_started",
            wake_count=wake_count,
            end_count=end_count,
            minimum_samples=3,
            wake_dir=args.hands_free_wake_dir,
            end_dir=args.hands_free_end_dir,
        )
    missing = missing_reference_messages(args.hands_free_wake_dir, args.hands_free_end_dir)
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
        sample_count=args.enroll_samples,
        seconds=args.enroll_seconds,
        telemetry=telemetry,
    )

    missing = missing_reference_messages(args.hands_free_wake_dir, args.hands_free_end_dir)
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


def main():
    args = parse_args()
    telemetry = telemetry_from_args(args, default_enabled=args.hands_free or args.telemetry_path is not None)
    telemetry.emit("app.started", mode="hands_free" if args.hands_free else "hotkey")

    hotkey = getattr(keyboard.Key, args.hotkey, None)
    if hotkey is None:
        telemetry.emit("app.failed", reason="unknown_hotkey")
        print(f"Error: Unknown hotkey '{args.hotkey}'. Use keys like shift_r, f10, ctrl, alt, etc.")
        sys.exit(1)

    if args.hands_free and not ensure_hands_free_references(args, telemetry=telemetry):
        telemetry.emit("app.failed", reason="handsfree_references_incomplete")
        sys.exit(1)

    hotwords_path = Path(args.hotwords_file) if args.hotwords_file else None
    hot_words, replacements = load_hotwords(hotwords_path) if hotwords_path else load_hotwords()
    if hot_words or replacements:
        print(f"Loaded {len(hot_words)} hot word(s) and {len(replacements)} replacement(s).")

    model_path = _resolve_model_path(args.model)
    telemetry.emit("model.load_started")
    print(f"Loading model: {model_path} ...")
    from mlx_audio.stt.utils import load_model
    model = load_model(model_path)
    telemetry.emit("model.load_completed")
    print(f"Model loaded. Press {args.hotkey} to start/stop recording.")
    if args.refine:
        print(f"Refine mode: ON (model: {args.refine_model})")

    stats = Stats()
    start_reminders(stats)

    state = State.IDLE
    state_lock = threading.Lock()
    recorder = Recorder()
    shutdown_event = threading.Event()
    hotkey_queue = queue.Queue()
    handsfree_queue = queue.Queue()
    handsfree_session = None
    handsfree_loop = None
    last_hotkey_time = 0.0
    handsfree_cycle_times: list[float] = []
    DEBOUNCE_SECONDS = 0.3
    LOOP_WINDOW_SECONDS = 30.0
    LOOP_EVENT_COUNT = 3

    def transition_to(new_state, source, **properties):
        nonlocal state
        previous = state
        state = new_state
        telemetry.emit(
            "app.state_transition",
            from_state=previous.value,
            to_state=new_state.value,
            source=source,
            **properties,
        )

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

    def start_transcription(audio, audio_seconds, resume_handsfree=None):
        def process(audio=audio, audio_seconds=audio_seconds):
            nonlocal state
            started = time.monotonic()
            telemetry.emit("transcription.started", audio_seconds=round(audio_seconds, 3), audio_samples=len(audio))
            try:
                text = transcribe(model, audio, language=args.language, extra_prompt=args.prompt, hotwords=hot_words)
                if text:
                    if args.refine:
                        processed = postprocess_for_refine(text, replacements=replacements)
                        print("  Refining...")
                        processed = refine(processed, model=args.refine_model)
                    else:
                        processed = postprocess(text, replacements=replacements)
                    word_count = len(processed.split())
                    stats.record(word_count, audio_seconds)
                    print(f"  > {processed}")
                    type_text(processed)
                    telemetry.emit(
                        "transcription.completed",
                        outcome="typed",
                        duration_seconds=round(time.monotonic() - started, 3),
                        audio_seconds=round(audio_seconds, 3),
                        word_count=word_count,
                        refined=args.refine,
                    )
                else:
                    print("  (no speech detected)")
                    telemetry.emit(
                        "transcription.completed",
                        outcome="empty",
                        duration_seconds=round(time.monotonic() - started, 3),
                        audio_seconds=round(audio_seconds, 3),
                    )
            except Exception as e:
                telemetry.emit(
                    "transcription.failed",
                    duration_seconds=round(time.monotonic() - started, 3),
                    audio_seconds=round(audio_seconds, 3),
                    error_type=type(e).__name__,
                )
                print(f"  Error: {e}", file=sys.stderr)
            finally:
                with state_lock:
                    transition_to(State.IDLE, "transcription.finally")
                    if resume_handsfree:
                        resume_handsfree()

        threading.Thread(target=process, daemon=True).start()

    def hotkey_worker():
        nonlocal state
        while not shutdown_event.is_set():
            try:
                hotkey_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            with state_lock:
                if state == State.TRANSCRIBING:
                    telemetry.emit("hotkey.ignored", reason="transcribing")
                    continue

                if state == State.IDLE:
                    transition_to(State.RECORDING, "hotkey")
                    recorder.start()
                    notify_recording_now()
                    print("Recording...")

                elif state == State.RECORDING:
                    transition_to(State.TRANSCRIBING, "hotkey")
                    audio = recorder.stop()
                    notify_recording_completed()
                    print("Transcribing...")
                    start_transcription(audio, len(audio) / SAMPLE_RATE)

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
            if state == State.TRANSCRIBING:
                telemetry.emit("hotkey.ignored", reason="transcribing")
                return

            if state == State.IDLE:
                transition_to(State.RECORDING, "manual_handsfree_hotkey")
                handsfree_session.manual_start()
                notify_recording_now()
                print("Recording... (manual)")

            elif state == State.RECORDING:
                event = handsfree_session.manual_stop()
                transition_to(State.TRANSCRIBING, "manual_handsfree_hotkey", audio_seconds=round(event.duration_seconds, 3))
                handsfree_session.suspend()
                notify_recording_completed()
                print("Transcribing... (manual)")
                start_transcription(event.audio, event.duration_seconds, handsfree_session.resume)

    def handle_handsfree_event(event):
        nonlocal state
        with state_lock:
            if event.kind == "wake.detected":
                if state == State.IDLE:
                    transition_to(
                        State.RECORDING,
                        "handsfree_wake",
                        detection_distance=round(event.detection.distance, 6) if event.detection else None,
                    )
                    notify_recording_now()
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
                    transition_to(State.TRANSCRIBING, f"handsfree_{event.kind}", audio_seconds=round(event.duration_seconds, 3))
                    handsfree_session.suspend()
                    notify_recording_completed()
                    if event.kind == "timeout":
                        print(f"handsfree.timeout seconds={event.duration_seconds:.2f}")
                        telemetry.emit("handsfree.timeout", audio_seconds=round(event.duration_seconds, 3))
                    else:
                        print(f"handsfree.end.detected distance={event.detection.distance:.4f}")
                        telemetry.emit(
                            "handsfree.end_detected",
                            distance=round(event.detection.distance, 6) if event.detection else None,
                            threshold=args.hands_free_threshold,
                            audio_seconds=round(event.duration_seconds, 3),
                            rms=round(event.detection.rms, 6) if event.detection and event.detection.rms is not None else None,
                            active_ratio=round(event.detection.active_ratio, 6) if event.detection and event.detection.active_ratio is not None else None,
                        )
                    record_handsfree_cycle(event.kind, event.duration_seconds)
                    print("Transcribing...")
                    start_transcription(event.audio, event.duration_seconds, handsfree_session.resume)
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

    if args.hands_free:
        try:
            telemetry.emit("handsfree.detector_load_started", threshold=args.hands_free_threshold)
            wake_detector = LocalWakeDetector(args.hands_free_wake_dir, args.hands_free_threshold)
            end_detector = LocalWakeDetector(args.hands_free_end_dir, args.hands_free_threshold)
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
        )
        handsfree_loop = HandsFreeAudioLoop(handsfree_session, handsfree_queue, stop_event=shutdown_event, telemetry=telemetry)
        handsfree_loop.start()
        print("Hands-free mode enabled. Right Shift remains available as a fallback.")
        threading.Thread(target=handsfree_worker, daemon=True).start()
    else:
        threading.Thread(target=hotkey_worker, daemon=True).start()

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    while listener.is_alive() and not shutdown_event.is_set():
        listener.join(timeout=0.5)

    if last_signal is not None:
        telemetry.emit("app.signal_received", signal=last_signal, count=ctrl_c_count)

    listener.stop()

    if handsfree_loop:
        handsfree_loop.join(timeout=1.0)

    with state_lock:
        if not args.hands_free and state == State.RECORDING:
            recorder.stop()

    print(f"\nSession stats: {stats.summary()}")
    telemetry.emit("app.exiting", stats=stats.summary())
    print("Exiting.")


if __name__ == "__main__":
    main()
