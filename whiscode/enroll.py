from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from whiscode.handsfree import DEFAULT_END_DIR, DEFAULT_WAKE_DIR, MIN_REFERENCE_FILES


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Import WhisCode hands-free trigger samples")
    parser.add_argument("kind", choices=("wake", "end"), help="Reference phrase set to update")
    parser.add_argument("samples", nargs="+", help="Audio samples to import, such as Voice Memo .m4a files")
    parser.add_argument("--wake-dir", type=Path, default=DEFAULT_WAKE_DIR, help=f"Wake reference folder (default: {DEFAULT_WAKE_DIR})")
    parser.add_argument("--end-dir", type=Path, default=DEFAULT_END_DIR, help=f"End reference folder (default: {DEFAULT_END_DIR})")
    return parser.parse_args(argv)


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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        written = import_samples(args.kind, [Path(p) for p in args.samples], args.wake_dir, args.end_dir)
    except (FileNotFoundError, ValueError, subprocess.CalledProcessError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Imported {len(written)} {args.kind} sample(s):")
    for path in written:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
