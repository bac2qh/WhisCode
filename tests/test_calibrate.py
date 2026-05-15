import json

from whiscode.calibrate import advisory_threshold, build_report, telemetry_distance_groups


def test_advisory_threshold_uses_reference_separation_midpoint():
    threshold = advisory_threshold({
        "wake within references": [0.02, 0.04],
        "end within references": [0.03, 0.05],
        "wake vs end references": [0.08, 0.1],
    })

    assert threshold == 0.065


def test_telemetry_distance_groups_reads_confirmed_and_summary_distances(tmp_path):
    path = tmp_path / "events.jsonl"
    rows = [
        {"event": "handsfree.wake_detected", "distance": 0.04},
        {"event": "handsfree.end_detected", "distance": 0.05},
        {"event": "handsfree.command_detected", "command": "page-up", "distance": 0.045},
        {"event": "handsfree.detector_distance_summary", "detector": "wake", "min_distance": 0.06},
        {"event": "handsfree.detector_distance_summary", "detector": "end", "min_distance": 0.07},
        {"event": "handsfree.detector_distance_summary", "detector": "command.page-up", "min_distance": 0.055},
        {"event": "transcription.completed", "word_count": 100},
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows))

    groups = telemetry_distance_groups(path)

    assert groups["confirmed wake triggers"] == [0.04]
    assert groups["confirmed end triggers"] == [0.05]
    assert groups["confirmed command triggers"] == [0.045]
    assert groups["wake summary minima"] == [0.06]
    assert groups["end summary minima"] == [0.07]
    assert groups["command summary minima"] == [0.055]


def test_build_report_includes_reference_telemetry_and_advisory_threshold(tmp_path):
    wake_dir = tmp_path / "wake"
    end_dir = tmp_path / "end"
    command_dir = tmp_path / "commands"
    wake_dir.mkdir()
    end_dir.mkdir()
    for name in ("wake-01.wav", "wake-02.wav"):
        (wake_dir / name).write_text("x")
    for name in ("end-01.wav", "end-02.wav"):
        (end_dir / name).write_text("x")
    page_up_dir = command_dir / "page-up"
    page_up_dir.mkdir(parents=True)
    for name in ("page-up-01.wav", "page-up-02.wav"):
        (page_up_dir / name).write_text("x")
    telemetry_path = tmp_path / "events.jsonl"
    telemetry_path.write_text(json.dumps({"event": "handsfree.wake_detected", "distance": 0.04}))

    def compare_fn(left, right):
        if "wake" in left and "wake" in right:
            return 0.04
        if "end" in left and "end" in right:
            return 0.05
        return 0.08

    report = build_report(wake_dir, end_dir, telemetry_path, command_dir=command_dir, compare_fn=compare_fn)

    assert "wake within references: n=1 min=0.040000 p05=0.040000 median=0.040000 p95=0.040000 max=0.040000" in report
    assert "command page-up within references: n=1" in report
    assert "command shift-enter within references: no data" in report
    assert "command shift-tab within references: no data" in report
    assert "command tab within references: no data" in report
    assert "command arrow-up within references: no data" in report
    assert "command arrow-down within references: no data" in report
    assert "confirmed wake triggers: n=1 min=0.040000 p05=0.040000 median=0.040000 p95=0.040000 max=0.040000" in report
    assert "Advisory threshold: 0.065000" in report
