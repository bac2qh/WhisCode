from __future__ import annotations

import argparse
import inspect
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np

from whiscode.handsfree import (
    COMMAND_SLOTS,
    DEFAULT_COMMAND_DIR,
    DEFAULT_END_DIR,
    DEFAULT_WAKE_DIR,
    DEFAULT_WINDOW_SECONDS,
    MIN_REFERENCE_FILES,
    command_reference_dirs,
)
from whiscode.recorder import SAMPLE_RATE, _resample, open_input_stream
from whiscode.recording_overlay import RecordingOverlayClient
from whiscode.telemetry import telemetry_from_args

DEFAULT_ENROLL_SECONDS = 2.0
DEFAULT_REFERENCE_SECONDS = DEFAULT_WINDOW_SECONDS


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Import WhisCode hands-free trigger samples")
    choices = ("wake", "end", *(slot.name for slot in COMMAND_SLOTS))
    parser.add_argument("kind", nargs="?", choices=choices, help="Reference phrase set to update for file import")
    parser.add_argument("samples", nargs="*", help="Audio samples to import, such as Voice Memo .m4a files")
    parser.add_argument("--record", action="store_true", help="Record wake, end, and key-command samples directly from the microphone")
    parser.add_argument("--sample-count", "--samples", dest="sample_count", type=int, default=MIN_REFERENCE_FILES, help=f"Samples to record per phrase (default: {MIN_REFERENCE_FILES})")
    parser.add_argument("--seconds", type=float, default=DEFAULT_ENROLL_SECONDS, help=f"Seconds to record per sample (default: {DEFAULT_ENROLL_SECONDS})")
    parser.add_argument("--wake-dir", type=Path, default=DEFAULT_WAKE_DIR, help=f"Wake reference folder (default: {DEFAULT_WAKE_DIR})")
    parser.add_argument("--end-dir", type=Path, default=DEFAULT_END_DIR, help=f"End reference folder (default: {DEFAULT_END_DIR})")
    parser.add_argument("--command-dir", type=Path, default=DEFAULT_COMMAND_DIR, help=f"Command reference root folder (default: {DEFAULT_COMMAND_DIR})")
    parser.add_argument("--telemetry-path", type=Path, default=None, help="Local JSONL telemetry path (default: ~/.config/whiscode/telemetry/events.jsonl)")
    parser.add_argument("--no-telemetry", action="store_true", help="Disable local telemetry for guided recording")
    parser.set_defaults(recording_overlay=True)
    parser.add_argument("--recording-overlay", dest="recording_overlay", action="store_true", help="Show the floating recording stopwatch/waveform overlay during guided recording (default)")
    parser.add_argument("--no-recording-overlay", dest="recording_overlay", action="store_false", help="Disable the floating recording overlay during guided recording")
    args = parser.parse_args(argv)
    if not args.record and args.kind is None:
        parser.error("kind is required unless --record is used")
    if not args.record and len(args.samples) < MIN_REFERENCE_FILES:
        parser.error(f"provide at least {MIN_REFERENCE_FILES} samples or use --record")
    return args


def validate_recording_options(sample_count: int, seconds: float) -> None:
    if sample_count < MIN_REFERENCE_FILES:
        raise ValueError(f"Record at least {MIN_REFERENCE_FILES} samples per phrase; got {sample_count}.")
    if seconds <= 0:
        raise ValueError(f"Recording duration must be positive; got {seconds}.")


def convert_sample(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "afconvert",
            str(input_path),
            str(output_path),
            "-f",
            "WAVE",
            "-d",
            "LEI16@16000",
            "-c",
            "1",
        ],
        check=True,
    )


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as f:
        channels = f.getnchannels()
        sample_width = f.getsampwidth()
        frames = f.getnframes()
        data = f.readframes(frames)

    if sample_width != 2:
        raise ValueError(f"Expected 16-bit PCM WAV for {path}; got sample width {sample_width}.")
    audio = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32767.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    return audio.astype(np.float32)


def preprocess_reference_audio(
    audio: np.ndarray,
    *,
    sample_rate: int = SAMPLE_RATE,
    trim_silence: bool = True,
    trim_fn=None,
    min_samples: int | None = None,
) -> np.ndarray:
    audio = np.asarray(audio, dtype=np.float32).flatten()
    if trim_silence and len(audio):
        if trim_fn is None:
            from lwake.record import trim_silence_with_vad

            trim_fn = trim_silence_with_vad
        trimmed = trim_fn(audio.reshape(-1, 1), sample_rate)
        audio = np.asarray(trimmed, dtype=np.float32).flatten()

    if min_samples is None:
        min_samples = int(DEFAULT_REFERENCE_SECONDS * sample_rate)

    if len(audio) < min_samples:
        pad_total = min_samples - len(audio)
        pad_left = pad_total // 2
        pad_right = pad_total - pad_left
        audio = np.pad(audio, (pad_left, pad_right), mode="constant")
    return audio.astype(np.float32)


def import_samples(
    kind: str,
    samples: list[Path],
    wake_dir: Path = DEFAULT_WAKE_DIR,
    end_dir: Path = DEFAULT_END_DIR,
    *,
    command_dir: Path = DEFAULT_COMMAND_DIR,
    preprocess_fn=preprocess_reference_audio,
) -> list[Path]:
    if len(samples) < MIN_REFERENCE_FILES:
        raise ValueError(f"Provide at least {MIN_REFERENCE_FILES} samples for {kind}; got {len(samples)}.")

    for sample in samples:
        if not sample.exists():
            raise FileNotFoundError(f"Sample not found: {sample}")

    if kind == "wake":
        target_dir = wake_dir
    elif kind == "end":
        target_dir = end_dir
    else:
        command_dirs = command_reference_dirs(command_dir)
        if kind not in command_dirs:
            raise ValueError(f"Unknown reference kind: {kind}")
        target_dir = command_dirs[kind]
    written = []
    for index, sample in enumerate(samples, start=1):
        output_path = target_dir / f"{kind}-{index:02d}.wav"
        convert_sample(sample, output_path)
        audio = preprocess_fn(read_wav(output_path))
        write_wav(output_path, audio)
        written.append(output_path)
    return written


def capture_audio(seconds: float, stream_factory=open_input_stream, *, level_callback=None) -> np.ndarray:
    if seconds <= 0:
        raise ValueError(f"Recording duration must be positive; got {seconds}.")

    stream, actual_rate = stream_factory()
    frames_remaining = int(seconds * actual_rate)
    chunks = []
    read_size = max(1, min(frames_remaining, int(0.1 * actual_rate)))

    with stream:
        while frames_remaining > 0:
            frames = min(read_size, frames_remaining)
            data, overflowed = stream.read(frames)
            if overflowed:
                print("  Warning: enrollment audio overflowed", file=sys.stderr)
            chunk = np.asarray(data[:, 0], dtype=np.float32).copy()
            chunks.append(chunk)
            if level_callback:
                level_callback(chunk)
            frames_remaining -= frames

    audio = np.concatenate(chunks) if chunks else np.array([], dtype=np.float32)
    if actual_rate != SAMPLE_RATE:
        audio = _resample(audio, actual_rate, SAMPLE_RATE)
    return audio.astype(np.float32)


def write_wav(path: Path, audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767).astype("<i2")
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm.tobytes())


def record_one_sample(
    kind: str,
    index: int,
    seconds: float,
    target_dir: Path,
    *,
    input_fn=input,
    capture_fn=capture_audio,
    preprocess_fn=preprocess_reference_audio,
    prompt_label: str | None = None,
    telemetry: Any | None = None,
    overlay: Any | None = None,
) -> Path:
    output_path = target_dir / f"{kind}-{index:02d}.wav"
    spoken_label = prompt_label or f"{kind} phrase"
    input_fn(f"Press Enter, say your {spoken_label}, recording for {seconds:.1f} seconds...")
    _emit(telemetry, "enrollment.sample_started", kind=kind, index=index, seconds=seconds, label=spoken_label)
    try:
        if overlay:
            overlay.show()
        audio = _capture_with_level_callback(capture_fn, seconds, overlay.update_level if overlay else None)
    except Exception:
        output_path.unlink(missing_ok=True)
        _emit(telemetry, "enrollment.sample_failed", kind=kind, index=index)
        raise
    finally:
        if overlay:
            overlay.hide()
    audio = preprocess_fn(audio)
    write_wav(output_path, audio)
    _emit(
        telemetry,
        "enrollment.sample_completed",
        kind=kind,
        index=index,
        audio_seconds=round(len(audio) / SAMPLE_RATE, 3),
        audio_samples=len(audio),
        label=spoken_label,
    )
    print(f"  Wrote {output_path}")
    return output_path


def record_guided_samples(
    *,
    wake_dir: Path = DEFAULT_WAKE_DIR,
    end_dir: Path = DEFAULT_END_DIR,
    command_dir: Path = DEFAULT_COMMAND_DIR,
    sample_count: int = MIN_REFERENCE_FILES,
    seconds: float = DEFAULT_ENROLL_SECONDS,
    input_fn=input,
    capture_fn=capture_audio,
    preprocess_fn=preprocess_reference_audio,
    telemetry: Any | None = None,
    overlay: Any | None = None,
) -> list[Path]:
    validate_recording_options(sample_count, seconds)
    _emit(telemetry, "enrollment.guided_started", sample_count=sample_count, seconds=seconds)
    written = []
    command_dirs = command_reference_dirs(command_dir)
    phrase_sets = [
        ("wake", wake_dir, "wake phrase"),
        ("end", end_dir, "end phrase"),
        *(
            (slot.name, command_dirs[slot.name], f"command phrase for {slot.label}")
            for slot in COMMAND_SLOTS
        ),
    ]
    for kind, target_dir, prompt_label in phrase_sets:
        print(f"Recording {sample_count} {prompt_label} sample(s).")
        for index in range(1, sample_count + 1):
            written.append(
                record_one_sample(
                    kind,
                    index,
                    seconds,
                    target_dir,
                    input_fn=input_fn,
                    capture_fn=capture_fn,
                    preprocess_fn=preprocess_fn,
                    prompt_label=prompt_label,
                    telemetry=telemetry,
                    overlay=overlay,
                )
            )
    _emit(telemetry, "enrollment.guided_completed", samples_written=len(written))
    return written


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    telemetry = telemetry_from_args(args, default_enabled=args.record or args.telemetry_path is not None)
    telemetry.emit("enrollment.cli_started", mode="record" if args.record else "import")
    overlay = RecordingOverlayClient(enabled=args.recording_overlay, telemetry=telemetry) if args.record else None
    try:
        if args.record:
            written = record_guided_samples(
                wake_dir=args.wake_dir,
                end_dir=args.end_dir,
                command_dir=args.command_dir,
                sample_count=args.sample_count,
                seconds=args.seconds,
                telemetry=telemetry,
                overlay=overlay,
            )
        else:
            written = import_samples(
                args.kind,
                [Path(p) for p in args.samples],
                args.wake_dir,
                args.end_dir,
                command_dir=args.command_dir,
            )
    except (FileNotFoundError, ValueError, subprocess.CalledProcessError, RuntimeError) as e:
        telemetry.emit("enrollment.cli_failed", error_type=type(e).__name__)
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        if overlay:
            overlay.stop()

    action = "Recorded" if args.record else "Imported"
    print(f"{action} {len(written)} sample(s):")
    for path in written:
        print(f"  {path}")
    telemetry.emit("enrollment.cli_completed", samples_written=len(written))
    return 0


def _emit(telemetry: Any | None, event: str, **properties) -> None:
    if telemetry:
        telemetry.emit(event, **properties)


def _capture_with_level_callback(capture_fn, seconds: float, level_callback) -> np.ndarray:
    if level_callback is None:
        return capture_fn(seconds)

    try:
        parameters = inspect.signature(capture_fn).parameters
    except (TypeError, ValueError):
        parameters = {}

    accepts_level_callback = "level_callback" in parameters or any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    )
    if accepts_level_callback:
        return capture_fn(seconds, level_callback=level_callback)

    audio = capture_fn(seconds)
    level_callback(audio)
    return audio


if __name__ == "__main__":
    raise SystemExit(main())
