from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from itertools import combinations, product
from pathlib import Path
from typing import Callable, Iterable

from whiscode.handsfree import (
    COMMAND_SLOTS,
    DEFAULT_COMMAND_CONFIG_PATH,
    DEFAULT_COMMAND_DIR,
    DEFAULT_END_DIR,
    DEFAULT_WAKE_DIR,
    CommandConfigError,
    active_command_slots,
    command_reference_dirs,
)

DEFAULT_TELEMETRY_PATH = Path.home() / ".config" / "whiscode" / "telemetry" / "events.jsonl"


@dataclass(frozen=True)
class DistanceSummary:
    name: str
    count: int
    minimum: float | None
    p05: float | None
    median: float | None
    p95: float | None
    maximum: float | None


def parse_args(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Report WhisCode hands-free detector calibration data")
    parser.add_argument("--wake-dir", type=Path, default=DEFAULT_WAKE_DIR, help=f"Wake reference folder (default: {DEFAULT_WAKE_DIR})")
    parser.add_argument("--end-dir", type=Path, default=DEFAULT_END_DIR, help=f"End reference folder (default: {DEFAULT_END_DIR})")
    parser.add_argument("--command-dir", type=Path, default=DEFAULT_COMMAND_DIR, help=f"Command reference root folder (default: {DEFAULT_COMMAND_DIR})")
    parser.add_argument("--command-config", type=Path, default=DEFAULT_COMMAND_CONFIG_PATH, help=f"Command enablement config (default: {DEFAULT_COMMAND_CONFIG_PATH})")
    parser.add_argument("--telemetry-path", type=Path, default=DEFAULT_TELEMETRY_PATH, help=f"Local telemetry JSONL path (default: {DEFAULT_TELEMETRY_PATH})")
    return parser.parse_args(argv)


def reference_distance_groups(
    wake_dir: Path,
    end_dir: Path,
    *,
    command_dir: Path = DEFAULT_COMMAND_DIR,
    command_slots=COMMAND_SLOTS,
    compare_fn: Callable[[str, str], float] | None = None,
) -> dict[str, list[float]]:
    if compare_fn is None:
        from lwake import compare

        compare_fn = lambda left, right: float(compare(left, right, method="embedding"))

    wake_files = sorted(Path(wake_dir).glob("*.wav"))
    end_files = sorted(Path(end_dir).glob("*.wav"))
    groups = {
        "wake within references": [_compare(compare_fn, left, right) for left, right in combinations(wake_files, 2)],
        "end within references": [_compare(compare_fn, left, right) for left, right in combinations(end_files, 2)],
        "wake vs end references": [_compare(compare_fn, left, right) for left, right in product(wake_files, end_files)],
    }
    command_files_by_name = {
        name: sorted(path.glob("*.wav"))
        for name, path in command_reference_dirs(command_dir, slots=tuple(command_slots)).items()
    }
    for name, files in command_files_by_name.items():
        groups[f"command {name} within references"] = [
            _compare(compare_fn, left, right) for left, right in combinations(files, 2)
        ]

    cross_command = []
    for left_name, right_name in combinations(command_files_by_name, 2):
        cross_command.extend(
            _compare(compare_fn, left, right)
            for left, right in product(command_files_by_name[left_name], command_files_by_name[right_name])
        )
    groups["command cross references"] = cross_command
    return groups


def telemetry_distance_groups(path: Path) -> dict[str, list[float]]:
    rows = list(_read_jsonl(path))
    groups = {
        "confirmed wake triggers": [],
        "confirmed end triggers": [],
        "confirmed command triggers": [],
        "wake summary minima": [],
        "end summary minima": [],
        "command summary minima": [],
    }
    for row in rows:
        event = row.get("event")
        distance = row.get("distance")
        if event == "handsfree.wake_detected" and isinstance(distance, (int, float)):
            groups["confirmed wake triggers"].append(float(distance))
        elif event == "handsfree.end_detected" and isinstance(distance, (int, float)):
            groups["confirmed end triggers"].append(float(distance))
        elif event == "handsfree.command_detected" and isinstance(distance, (int, float)):
            groups["confirmed command triggers"].append(float(distance))
        elif event == "handsfree.detector_distance_summary":
            detector = row.get("detector")
            minimum = row.get("min_distance")
            if detector == "wake" and isinstance(minimum, (int, float)):
                groups["wake summary minima"].append(float(minimum))
            elif detector == "end" and isinstance(minimum, (int, float)):
                groups["end summary minima"].append(float(minimum))
            elif isinstance(detector, str) and detector.startswith("command.") and isinstance(minimum, (int, float)):
                groups["command summary minima"].append(float(minimum))
    return groups


def summarize(name: str, values: Iterable[float]) -> DistanceSummary:
    vals = sorted(float(value) for value in values)
    if not vals:
        return DistanceSummary(name, 0, None, None, None, None, None)
    return DistanceSummary(
        name,
        len(vals),
        vals[0],
        _percentile(vals, 5),
        _percentile(vals, 50),
        _percentile(vals, 95),
        vals[-1],
    )


def advisory_threshold(groups: dict[str, list[float]]) -> float | None:
    within = groups.get("wake within references", []) + groups.get("end within references", [])
    cross = groups.get("wake vs end references", [])
    if not within or not cross:
        return None
    high_positive = max(within)
    low_negative = min(cross)
    if low_negative <= high_positive:
        return high_positive
    return (high_positive + low_negative) / 2


def build_report(
    wake_dir: Path,
    end_dir: Path,
    telemetry_path: Path,
    *,
    command_dir: Path = DEFAULT_COMMAND_DIR,
    command_slots=COMMAND_SLOTS,
    compare_fn: Callable[[str, str], float] | None = None,
) -> str:
    reference_groups = reference_distance_groups(
        wake_dir,
        end_dir,
        command_dir=command_dir,
        command_slots=command_slots,
        compare_fn=compare_fn,
    )
    telemetry_groups = telemetry_distance_groups(telemetry_path)
    lines = ["WhisCode hands-free calibration report", ""]
    lines.append("Reference distances")
    for name, values in reference_groups.items():
        lines.append(_format_summary(summarize(name, values)))

    lines.append("")
    lines.append("Telemetry distances")
    for name, values in telemetry_groups.items():
        lines.append(_format_summary(summarize(name, values)))

    threshold = advisory_threshold(reference_groups)
    lines.append("")
    if threshold is None:
        lines.append("Advisory threshold: unavailable; record at least two wake and end samples.")
    else:
        lines.append(f"Advisory threshold: {threshold:.6f} based on midpoint between same-command max and cross-command min.")
        lines.append("Treat this as a starting point, then validate against live telemetry before changing runtime defaults.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        command_slots = active_command_slots(args.command_config, base_dir=args.command_dir)
    except CommandConfigError as e:
        print(f"Error: {e}")
        return 1
    print(
        build_report(
            args.wake_dir,
            args.end_dir,
            args.telemetry_path,
            command_dir=args.command_dir,
            command_slots=command_slots,
        )
    )
    return 0


def _compare(compare_fn: Callable[[str, str], float], left: Path, right: Path) -> float:
    return float(compare_fn(str(left), str(right)))


def _format_summary(summary: DistanceSummary) -> str:
    if summary.count == 0:
        return f"- {summary.name}: no data"
    return (
        f"- {summary.name}: n={summary.count} "
        f"min={summary.minimum:.6f} p05={summary.p05:.6f} "
        f"median={summary.median:.6f} p95={summary.p95:.6f} max={summary.maximum:.6f}"
    )


def _percentile(values: list[float], percentile: float) -> float:
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * percentile / 100
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] * (1 - fraction) + values[upper] * fraction


def _read_jsonl(path: Path):
    if not Path(path).exists():
        return
    with Path(path).open() as f:
        for line in f:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


if __name__ == "__main__":
    raise SystemExit(main())
