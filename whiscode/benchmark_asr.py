from __future__ import annotations

import argparse
import time
import wave
from pathlib import Path

import numpy as np

from whiscode.crispasr_asr import (
    CrispAsrBackend,
    CrispAsrServerConfig,
    default_crispasr_bin,
    default_crispasr_model_path,
)
from whiscode.hotwords import load_hotwords
from whiscode.llama_cpp_asr import (
    LlamaCppAsrBackend,
    LlamaCppServerConfig,
    default_llama_mmproj_path,
    default_llama_model_path,
    default_llama_server_bin,
)
from whiscode.main import _resolve_model_path, ensure_whisper_processor
from whiscode.mlx_vibevoice_asr import (
    DEFAULT_MLX_VIBEVOICE_MAX_TOKENS,
    DEFAULT_MLX_VIBEVOICE_PREFILL_STEP_SIZE,
    DEFAULT_MLX_VIBEVOICE_TEMPERATURE,
    MlxVibeVoiceBackend,
    MlxVibeVoiceConfig,
    default_mlx_vibevoice_model,
)
from whiscode.recorder import SAMPLE_RATE, _resample
from whiscode.transcriber import transcribe


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Benchmark WhisCode ASR backend latency on a WAV file")
    parser.add_argument("--audio", type=Path, required=True, help="Input WAV file")
    parser.add_argument("--asr-backend", choices=("mlx-whisper", "mlx-vibevoice", "llama-cpp", "crispasr"), default="mlx-whisper")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-mlx", help="Whisper model for mlx-whisper")
    parser.add_argument("--language", default="auto", help="Language code or auto")
    parser.add_argument("--prompt", default=None, help="Additional prompt/context")
    parser.add_argument("--hotwords-file", default=None, help="Path to hotwords config file")

    parser.add_argument("--llama-server-bin", type=Path, default=default_llama_server_bin())
    parser.add_argument("--llama-model", type=Path, default=default_llama_model_path())
    parser.add_argument("--llama-mmproj", type=Path, default=default_llama_mmproj_path())
    parser.add_argument("--llama-host", default="127.0.0.1")
    parser.add_argument("--llama-port", type=int, default=8091)
    parser.add_argument("--llama-ctx", type=int, default=4096)
    parser.add_argument("--llama-ngl", type=int, default=99)
    parser.set_defaults(llama_autostart=True)
    parser.add_argument("--no-llama-autostart", dest="llama_autostart", action="store_false")

    parser.add_argument("--crispasr-bin", type=Path, default=default_crispasr_bin())
    parser.add_argument("--crispasr-model", type=Path, default=default_crispasr_model_path())
    parser.add_argument("--crispasr-backend", default="vibevoice")
    parser.add_argument("--crispasr-host", default="127.0.0.1")
    parser.add_argument("--crispasr-port", type=int, default=8092)
    parser.add_argument("--crispasr-max-tokens", type=int, default=2048)
    parser.add_argument("--crispasr-temperature", type=float, default=0.0)
    parser.add_argument("--crispasr-request-timeout", type=float, default=300.0)
    parser.add_argument("--crispasr-startup-timeout", type=float, default=180.0)
    parser.set_defaults(crispasr_autostart=True)
    parser.add_argument("--no-crispasr-autostart", dest="crispasr_autostart", action="store_false")
    parser.add_argument("--mlx-vibevoice-model", default=default_mlx_vibevoice_model())
    parser.add_argument("--mlx-vibevoice-max-tokens", type=int, default=DEFAULT_MLX_VIBEVOICE_MAX_TOKENS)
    parser.add_argument("--mlx-vibevoice-temperature", type=float, default=DEFAULT_MLX_VIBEVOICE_TEMPERATURE)
    parser.add_argument("--mlx-vibevoice-prefill-step-size", type=int, default=DEFAULT_MLX_VIBEVOICE_PREFILL_STEP_SIZE)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    audio = read_wav_mono_16k(args.audio.expanduser())
    audio_seconds = len(audio) / SAMPLE_RATE if len(audio) else 0.0
    hotwords_path = Path(args.hotwords_file) if args.hotwords_file else None
    hot_words, _ = load_hotwords(hotwords_path) if hotwords_path else load_hotwords()

    backend = None
    mode = "in-process"
    try:
        if args.asr_backend == "mlx-whisper":
            from mlx_audio.stt.utils import load_model

            model_path = _resolve_model_path(args.model)
            model = load_model(model_path)
            ensure_whisper_processor(model, args.model)

            def transcribe_audio():
                return transcribe(
                    model,
                    audio,
                    language=args.language,
                    extra_prompt=args.prompt,
                    hotwords=hot_words,
                )

            model_label = args.model
        elif args.asr_backend == "mlx-vibevoice":
            backend = MlxVibeVoiceBackend(
                MlxVibeVoiceConfig(
                    model=args.mlx_vibevoice_model,
                    max_tokens=args.mlx_vibevoice_max_tokens,
                    temperature=args.mlx_vibevoice_temperature,
                    prefill_step_size=args.mlx_vibevoice_prefill_step_size,
                )
            )
            backend.start()

            def transcribe_audio():
                return backend.transcribe(
                    audio,
                    language=args.language,
                    extra_prompt=args.prompt,
                    hotwords=hot_words,
                )

            model_label = backend.model_label
        elif args.asr_backend == "llama-cpp":
            backend = LlamaCppAsrBackend(
                LlamaCppServerConfig(
                    server_bin=args.llama_server_bin.expanduser(),
                    model=args.llama_model.expanduser(),
                    mmproj=args.llama_mmproj.expanduser(),
                    host=args.llama_host,
                    port=args.llama_port,
                    ctx=args.llama_ctx,
                    ngl=args.llama_ngl,
                    autostart=args.llama_autostart,
                )
            )
            backend.start()
            mode = "cold-server" if getattr(backend, "_owns_process", False) else "warm-server"

            def transcribe_audio():
                return backend.transcribe(
                    audio,
                    language=args.language,
                    extra_prompt=args.prompt,
                    hotwords=hot_words,
                )

            model_label = args.llama_model.name
        else:
            backend = CrispAsrBackend(
                CrispAsrServerConfig(
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
            )
            backend.start()
            mode = "cold-server" if backend.owns_process else "warm-server"

            def transcribe_audio():
                return backend.transcribe(
                    audio,
                    language=args.language,
                    extra_prompt=args.prompt,
                    hotwords=hot_words,
                )

            model_label = args.crispasr_model.name

        started = time.monotonic()
        text = transcribe_audio()
        wall_seconds = time.monotonic() - started
        rtf = wall_seconds / audio_seconds if audio_seconds else 0.0

        print(
            " ".join(
                [
                    f"backend={args.asr_backend}",
                    f"model={model_label}",
                    f"mode={mode}",
                    f"audio_seconds={audio_seconds:.3f}",
                    f"wall_seconds={wall_seconds:.3f}",
                    f"real_time_factor={rtf:.3f}",
                    f"output_chars={len(text)}",
                ]
            )
        )
        if text:
            print(text)
    finally:
        if backend is not None:
            backend.close()


def read_wav_mono_16k(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())

    if sample_width == 1:
        data = (np.frombuffer(frames, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sample_width == 2:
        data = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 4:
        data = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width}")

    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    if sample_rate != SAMPLE_RATE:
        data = _resample(data.astype(np.float32), sample_rate, SAMPLE_RATE)
    return data.astype(np.float32)


if __name__ == "__main__":
    main()
