from __future__ import annotations

import argparse
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

from whiscode.handsfree import DEFAULT_END_DIR, DEFAULT_WAKE_DIR, MIN_REFERENCE_FILES
from whiscode.recorder import SAMPLE_RATE, _resample, open_input_stream
from whiscode.status_notifier import notify_recording_completed, notify_recording_now

DEFAULT_ENROLL_SECONDS = 2.0


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Import WhisCode hands-free trigger samples")
    parser.add_argument("kind", nargs="?", choices=("wake", "end"), help="Reference phrase set to update for file import")
    parser.add_argument("samples", nargs="*", help="Audio samples to import, such as Voice Memo .m4a files")
    parser.add_argument("--record", action="store_true", help="Record wake and end samples directly from the microphone")
    parser.add_argument("--sample-count", "--samples", dest="sample_count", type=int, default=MIN_REFERENCE_FILES, help=f"Samples to record per phrase (default: {MIN_REFERENCE_FILES})")
    parser.add_argument("--seconds", type=float, default=DEFAULT_ENROLL_SECONDS, help=f"Seconds to record per sample (default: {DEFAULT_ENROLL_SECONDS})")
    parser.add_argument("--wake-dir", type=Path, default=DEFAULT_WAKE_DIR, help=f"Wake reference folder (default: {DEFAULT_WAKE_DIR})")
    parser.add_argument("--end-dir", type=Path, default=DEFAULT_END_DIR, help=f"End reference folder (default: {DEFAULT_END_DIR})")
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


def import_samples(kind: str, samples: list[Path], wake_dir: Path = DEFAULT_WAKE_DIR, end_dir: Path = DEFAULT_END_DIR) -> list[Path]:
    if len(samples) < MIN_REFERENCE_FILES:
        raise ValueError(f"Provide at least {MIN_REFERENCE_FILES} samples for {kind}; got {len(samples)}.")

    for sample in samples:
        if not sample.exists():
            raise FileNotFoundError(f"Sample not found: {sample}")

    target_dir = wake_dir if kind == "wake" else end_dir
    written = []
    for index, sample in enumerate(samples, start=1):
        output_path = target_dir / f"{kind}-{index:02d}.wav"
        convert_sample(sample, output_path)
        written.append(output_path)
    return written


def capture_audio(seconds: float, stream_factory=open_input_stream) -> np.ndarray:
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
            chunks.append(np.asarray(data[:, 0], dtype=np.float32).copy())
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


def record_one_sample(kind: str, index: int, seconds: float, target_dir: Path, *, input_fn=input, capture_fn=capture_audio) -> Path:
    output_path = target_dir / f"{kind}-{index:02d}.wav"
    input_fn(f"Press Enter, say your {kind} phrase, recording for {seconds:.1f} seconds...")
    try:
        notify_recording_now()
        audio = capture_fn(seconds)
        notify_recording_completed()
    except Exception:
        output_path.unlink(missing_ok=True)
        raise
    write_wav(output_path, audio)
    print(f"  Wrote {output_path}")
    return output_path


def record_guided_samples(
    *,
    wake_dir: Path = DEFAULT_WAKE_DIR,
    end_dir: Path = DEFAULT_END_DIR,
    sample_count: int = MIN_REFERENCE_FILES,
    seconds: float = DEFAULT_ENROLL_SECONDS,
    input_fn=input,
    capture_fn=capture_audio,
) -> list[Path]:
    validate_recording_options(sample_count, seconds)
    written = []
    for kind, target_dir in (("wake", wake_dir), ("end", end_dir)):
        print(f"Recording {sample_count} {kind} sample(s).")
        for index in range(1, sample_count + 1):
            written.append(
                record_one_sample(
                    kind,
                    index,
                    seconds,
                    target_dir,
                    input_fn=input_fn,
                    capture_fn=capture_fn,
                )
            )
    return written


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.record:
            written = record_guided_samples(
                wake_dir=args.wake_dir,
                end_dir=args.end_dir,
                sample_count=args.sample_count,
                seconds=args.seconds,
            )
        else:
            written = import_samples(args.kind, [Path(p) for p in args.samples], args.wake_dir, args.end_dir)
    except (FileNotFoundError, ValueError, subprocess.CalledProcessError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    action = "Recorded" if args.record else "Imported"
    print(f"{action} {len(written)} sample(s):")
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
