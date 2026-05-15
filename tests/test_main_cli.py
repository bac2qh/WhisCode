from pathlib import Path

from whiscode.handsfree import command_reference_dirs
from whiscode.main import ensure_hands_free_references, parse_args


def write_reference_samples(path: Path, prefix: str, count: int = 3) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (path / f"{prefix}-{i}.wav").write_text("x")


def test_parse_args_defaults_to_hotkey_mode():
    args = parse_args([])

    assert args.hands_free is False
    assert args.hotkey == "shift_r"
    assert args.hands_free_threshold == 0.055
    assert args.hands_free_end_threshold == 0.055
    assert args.hands_free_wake_confirmations == 2
    assert args.hands_free_command_threshold == 0.055
    assert args.hands_free_command_confirmations == 2
    assert args.max_recording_seconds == 600.0
    assert args.hands_free_max_seconds == 600.0
    assert args.hands_free_audio_queue_seconds == 10.0


def test_parse_args_hands_free_options():
    args = parse_args([
        "--hands-free",
        "--hands-free-wake-dir",
        "/tmp/wake",
        "--hands-free-end-dir",
        "/tmp/end",
        "--hands-free-command-dir",
        "/tmp/commands",
        "--hands-free-threshold",
        "0.2",
        "--hands-free-end-threshold",
        "0.07",
        "--hands-free-command-threshold",
        "0.06",
        "--hands-free-window-seconds",
        "1.5",
        "--hands-free-slide-seconds",
        "0.1",
        "--hands-free-tail-seconds",
        "0.75",
        "--max-recording-seconds",
        "45",
        "--hands-free-max-seconds",
        "30",
        "--hands-free-audio-queue-seconds",
        "3.5",
        "--hands-free-min-rms",
        "0.01",
        "--hands-free-min-active-ratio",
        "0.2",
        "--hands-free-active-level",
        "0.03",
        "--hands-free-wake-confirmations",
        "3",
        "--hands-free-command-confirmations",
        "4",
        "--hands-free-debug",
        "--no-enroll-prompt",
        "--enroll-samples",
        "4",
        "--enroll-seconds",
        "1.25",
        "--telemetry-path",
        "/tmp/whiscode-events.jsonl",
        "--no-telemetry",
        "--no-recording-overlay",
        "--recording-notifications",
    ])

    assert args.hands_free is True
    assert args.hands_free_wake_dir == Path("/tmp/wake")
    assert args.hands_free_end_dir == Path("/tmp/end")
    assert args.hands_free_command_dir == Path("/tmp/commands")
    assert args.hands_free_threshold == 0.2
    assert args.hands_free_end_threshold == 0.07
    assert args.hands_free_command_threshold == 0.06
    assert args.hands_free_window_seconds == 1.5
    assert args.hands_free_slide_seconds == 0.1
    assert args.hands_free_tail_seconds == 0.75
    assert args.max_recording_seconds == 45
    assert args.hands_free_max_seconds == 30
    assert args.hands_free_audio_queue_seconds == 3.5
    assert args.hands_free_min_rms == 0.01
    assert args.hands_free_min_active_ratio == 0.2
    assert args.hands_free_active_level == 0.03
    assert args.hands_free_wake_confirmations == 3
    assert args.hands_free_command_confirmations == 4
    assert args.hands_free_debug is True
    assert args.no_enroll_prompt is True
    assert args.enroll_samples == 4
    assert args.enroll_seconds == 1.25
    assert args.telemetry_path == Path("/tmp/whiscode-events.jsonl")
    assert args.no_telemetry is True
    assert args.recording_overlay is False
    assert args.recording_notifications is True


def test_parse_args_legacy_threshold_applies_to_end_when_end_threshold_omitted():
    args = parse_args(["--hands-free-threshold", "0.08"])

    assert args.hands_free_threshold == 0.08
    assert args.hands_free_end_threshold == 0.08
    assert args.hands_free_command_threshold == 0.08


def test_parse_args_shared_max_recording_seconds_feeds_hands_free_default():
    args = parse_args(["--max-recording-seconds", "45"])

    assert args.max_recording_seconds == 45
    assert args.hands_free_max_seconds == 45


def test_parse_args_zero_disables_shared_max_recording_seconds():
    args = parse_args(["--max-recording-seconds", "0"])

    assert args.max_recording_seconds == 0
    assert args.hands_free_max_seconds == 0


def test_ensure_hands_free_references_returns_true_when_samples_exist(tmp_path):
    wake_dir = tmp_path / "wake"
    end_dir = tmp_path / "end"
    command_dir = tmp_path / "commands"
    write_reference_samples(wake_dir, "wake")
    write_reference_samples(end_dir, "end")
    for name, path in command_reference_dirs(command_dir).items():
        write_reference_samples(path, name)
    args = parse_args([
        "--hands-free",
        "--hands-free-wake-dir",
        str(wake_dir),
        "--hands-free-end-dir",
        str(end_dir),
        "--hands-free-command-dir",
        str(command_dir),
    ])

    assert ensure_hands_free_references(args) is True


def test_ensure_hands_free_references_decline_prompt_exits(tmp_path):
    args = parse_args([
        "--hands-free",
        "--hands-free-wake-dir",
        str(tmp_path / "wake"),
        "--hands-free-end-dir",
        str(tmp_path / "end"),
        "--hands-free-command-dir",
        str(tmp_path / "commands"),
    ])

    assert ensure_hands_free_references(args, input_fn=lambda prompt: "n") is False


def test_ensure_hands_free_references_no_prompt_exits_without_input(tmp_path):
    args = parse_args([
        "--hands-free",
        "--no-enroll-prompt",
        "--hands-free-wake-dir",
        str(tmp_path / "wake"),
        "--hands-free-end-dir",
        str(tmp_path / "end"),
        "--hands-free-command-dir",
        str(tmp_path / "commands"),
    ])

    assert ensure_hands_free_references(args, input_fn=lambda prompt: (_ for _ in ()).throw(AssertionError("prompted"))) is False


def test_ensure_hands_free_references_accept_prompt_runs_enrollment(tmp_path):
    wake_dir = tmp_path / "wake"
    end_dir = tmp_path / "end"
    command_dir = tmp_path / "commands"
    args = parse_args([
        "--hands-free",
        "--hands-free-wake-dir",
        str(wake_dir),
        "--hands-free-end-dir",
        str(end_dir),
        "--hands-free-command-dir",
        str(command_dir),
        "--enroll-samples",
        "3",
        "--enroll-seconds",
        "1.5",
    ])

    def enroll_fn(*, wake_dir, end_dir, command_dir, sample_count, seconds, telemetry=None):
        assert sample_count == 3
        assert seconds == 1.5
        write_reference_samples(wake_dir, "wake")
        write_reference_samples(end_dir, "end")
        for name, path in command_reference_dirs(command_dir).items():
            write_reference_samples(path, name)

    assert ensure_hands_free_references(args, input_fn=lambda prompt: "", enroll_fn=enroll_fn) is True


class FakeTelemetry:
    def __init__(self):
        self.events = []

    def emit(self, event, **properties):
        self.events.append((event, properties))


def test_ensure_hands_free_references_emits_missing_telemetry(tmp_path):
    telemetry = FakeTelemetry()
    args = parse_args([
        "--hands-free",
        "--no-enroll-prompt",
        "--hands-free-wake-dir",
        str(tmp_path / "wake"),
        "--hands-free-end-dir",
        str(tmp_path / "end"),
        "--hands-free-command-dir",
        str(tmp_path / "commands"),
    ])

    assert ensure_hands_free_references(args, telemetry=telemetry) is False

    event_names = [event for event, properties in telemetry.events]
    assert "handsfree.reference_check_started" in event_names
    assert ("handsfree.reference_check_completed", {"outcome": "missing", "missing_count": 7}) in telemetry.events
    assert ("handsfree.enrollment_prompt_skipped", {"reason": "no_enroll_prompt"}) in telemetry.events
