from pathlib import Path

from whiscode.handsfree import command_reference_dirs
from whiscode.main import (
    _default_whisper_processor_source,
    _format_transcript_for_stdout,
    _print_transcript_for_stdout,
    ensure_hands_free_references,
    ensure_whisper_processor,
    parse_args,
    runtime_telemetry_enabled_by_default,
)
from whiscode.telemetry import telemetry_from_args


WhisperModel = type("Model", (), {"__module__": "mlx_audio.stt.models.whisper.whisper"})


def write_reference_samples(path: Path, prefix: str, count: int = 3) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (path / f"{prefix}-{i}.wav").write_text("x")


def test_format_transcript_for_stdout_collapses_multiline_text():
    assert _format_transcript_for_stdout("  first line\nsecond\tline  ") == "first line second line"


def test_format_transcript_for_stdout_preserves_mixed_english_chinese_text():
    assert _format_transcript_for_stdout("调用 API\nwith retry  逻辑") == "调用 API with retry 逻辑"


def test_print_transcript_for_stdout_uses_copy_friendly_block(capsys):
    _print_transcript_for_stdout("  hello\nworld  ")

    assert capsys.readouterr().out == "\nhello world\n\n"


def test_parse_args_defaults_to_hotkey_mode():
    args = parse_args([])

    assert args.hands_free is False
    assert args.hotkey == "shift_r"
    assert args.asr_backend == "mlx-whisper"
    assert args.hands_free_threshold == 0.055
    assert args.hands_free_end_threshold == 0.055
    assert args.hands_free_wake_confirmations == 2
    assert args.hands_free_command_threshold == 0.055
    assert args.hands_free_command_confirmations == 2
    assert args.hands_free_command_config.name == "commands.ini"
    assert args.max_recording_seconds == 600.0
    assert args.hands_free_max_seconds == 600.0
    assert args.hands_free_audio_queue_seconds == 10.0
    assert args.model == "mlx-community/whisper-large-v3-mlx"
    assert args.llama_port == 8091
    assert args.llama_autostart is True
    assert args.crispasr_port == 8092
    assert args.crispasr_backend == "vibevoice"
    assert args.crispasr_autostart is True


def test_runtime_telemetry_is_enabled_by_default_for_hotkey_mode():
    args = parse_args([])

    telemetry = telemetry_from_args(args, default_enabled=runtime_telemetry_enabled_by_default(args))

    assert telemetry.enabled is True


def test_runtime_telemetry_can_be_disabled():
    args = parse_args(["--no-telemetry"])

    telemetry = telemetry_from_args(args, default_enabled=runtime_telemetry_enabled_by_default(args))

    assert telemetry.enabled is False


def test_parse_args_llama_cpp_options():
    args = parse_args([
        "--asr-backend",
        "llama-cpp",
        "--llama-server-bin",
        "/tmp/llama-server",
        "--llama-model",
        "/tmp/qwen-asr.gguf",
        "--llama-mmproj",
        "/tmp/mmproj.gguf",
        "--llama-host",
        "127.0.0.2",
        "--llama-port",
        "8099",
        "--llama-ctx",
        "8192",
        "--llama-ngl",
        "42",
        "--no-llama-autostart",
    ])

    assert args.asr_backend == "llama-cpp"
    assert args.llama_server_bin == Path("/tmp/llama-server")
    assert args.llama_model == Path("/tmp/qwen-asr.gguf")
    assert args.llama_mmproj == Path("/tmp/mmproj.gguf")
    assert args.llama_host == "127.0.0.2"
    assert args.llama_port == 8099
    assert args.llama_ctx == 8192
    assert args.llama_ngl == 42
    assert args.llama_autostart is False


def test_parse_args_crispasr_options():
    args = parse_args([
        "--asr-backend",
        "crispasr",
        "--crispasr-bin",
        "/tmp/crispasr",
        "--crispasr-model",
        "/tmp/vibevoice.gguf",
        "--crispasr-backend",
        "vibevoice",
        "--crispasr-host",
        "127.0.0.3",
        "--crispasr-port",
        "8098",
        "--crispasr-max-tokens",
        "1024",
        "--crispasr-temperature",
        "0.1",
        "--crispasr-request-timeout",
        "12",
        "--crispasr-startup-timeout",
        "34",
        "--no-crispasr-autostart",
    ])

    assert args.asr_backend == "crispasr"
    assert args.crispasr_bin == Path("/tmp/crispasr")
    assert args.crispasr_model == Path("/tmp/vibevoice.gguf")
    assert args.crispasr_backend == "vibevoice"
    assert args.crispasr_host == "127.0.0.3"
    assert args.crispasr_port == 8098
    assert args.crispasr_max_tokens == 1024
    assert args.crispasr_temperature == 0.1
    assert args.crispasr_request_timeout == 12
    assert args.crispasr_startup_timeout == 34
    assert args.crispasr_autostart is False


def test_parse_args_hands_free_options():
    args = parse_args([
        "--hands-free",
        "--hands-free-wake-dir",
        "/tmp/wake",
        "--hands-free-end-dir",
        "/tmp/end",
        "--hands-free-command-dir",
        "/tmp/commands",
        "--hands-free-command-config",
        "/tmp/commands.ini",
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
    assert args.hands_free_command_config == Path("/tmp/commands.ini")
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


def test_default_whisper_processor_source_maps_mlx_default_to_openai_model():
    assert (
        _default_whisper_processor_source("mlx-community/whisper-large-v3-mlx")
        == "openai/whisper-large-v3"
    )


def test_default_whisper_processor_source_maps_mlx_turbo_to_openai_model():
    assert (
        _default_whisper_processor_source("mlx-community/whisper-large-v3-turbo")
        == "openai/whisper-large-v3-turbo"
    )


def test_ensure_whisper_processor_attaches_fallback_processor():
    telemetry = FakeTelemetry()
    model = WhisperModel()
    model._processor = None

    ensure_whisper_processor(
        model,
        "mlx-community/whisper-large-v3-mlx",
        telemetry=telemetry,
        processor_loader=lambda source: {"source": source},
    )

    assert model._processor == {"source": "openai/whisper-large-v3"}
    assert (
        "model.processor_fallback_attempted",
        {"model_family": "whisper", "processor_source": "openai"},
    ) in telemetry.events
    assert (
        "model.processor_fallback_completed",
        {"model_family": "whisper", "processor_source": "openai"},
    ) in telemetry.events


def test_ensure_whisper_processor_skips_when_processor_exists():
    telemetry = FakeTelemetry()
    model = WhisperModel()
    model._processor = object()

    ensure_whisper_processor(
        model,
        "mlx-community/whisper-large-v3-turbo",
        telemetry=telemetry,
        processor_loader=lambda source: (_ for _ in ()).throw(
            AssertionError("loaded processor")
        ),
    )

    assert telemetry.events == [
        (
            "model.processor_fallback_skipped",
            {"reason": "processor_present", "model_family": "whisper"},
        )
    ]


def test_ensure_whisper_processor_fails_for_unknown_missing_processor():
    telemetry = FakeTelemetry()
    model = WhisperModel()
    model._processor = None

    try:
        ensure_whisper_processor(model, "mlx-community/unknown-whisper", telemetry=telemetry)
    except RuntimeError as e:
        assert "Whisper processor not found" in str(e)
    else:
        raise AssertionError("expected RuntimeError")

    assert telemetry.events == [
        (
            "model.processor_fallback_skipped",
            {"reason": "no_processor_source", "model_family": "whisper"},
        )
    ]


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
        "--hands-free-command-config",
        str(tmp_path / "missing-config.ini"),
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
        "--hands-free-command-config",
        str(tmp_path / "missing-config.ini"),
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
        "--hands-free-command-config",
        str(tmp_path / "missing-config.ini"),
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
        "--hands-free-command-config",
        str(tmp_path / "missing-config.ini"),
        "--enroll-samples",
        "3",
        "--enroll-seconds",
        "1.5",
    ])

    def enroll_fn(*, wake_dir, end_dir, command_dir, sample_count, seconds, telemetry=None, command_slots=None):
        assert sample_count == 3
        assert seconds == 1.5
        write_reference_samples(wake_dir, "wake")
        write_reference_samples(end_dir, "end")
        for name, path in command_reference_dirs(command_dir, slots=command_slots).items():
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
        "--hands-free-command-config",
        str(tmp_path / "missing-config.ini"),
    ])

    assert ensure_hands_free_references(args, telemetry=telemetry) is False

    event_names = [event for event, properties in telemetry.events]
    assert "handsfree.reference_check_started" in event_names
    assert ("handsfree.reference_check_completed", {"outcome": "missing", "missing_count": 10}) in telemetry.events
    assert ("handsfree.enrollment_prompt_skipped", {"reason": "no_enroll_prompt"}) in telemetry.events


def test_ensure_hands_free_references_only_requires_enabled_commands(tmp_path):
    telemetry = FakeTelemetry()
    wake_dir = tmp_path / "wake"
    end_dir = tmp_path / "end"
    command_dir = tmp_path / "commands"
    config_path = tmp_path / "commands.ini"
    config_path.write_text("[commands]\nenter = true\n")
    write_reference_samples(wake_dir, "wake")
    write_reference_samples(end_dir, "end")
    write_reference_samples(command_dir / "enter", "enter")
    args = parse_args([
        "--hands-free",
        "--hands-free-wake-dir",
        str(wake_dir),
        "--hands-free-end-dir",
        str(end_dir),
        "--hands-free-command-dir",
        str(command_dir),
        "--hands-free-command-config",
        str(config_path),
    ])

    assert ensure_hands_free_references(args, telemetry=telemetry) is True
    assert (
        "handsfree.command_config_loaded",
        {
            "config_path": config_path,
            "config_exists": True,
            "enabled_commands": ["enter"],
            "enabled_command_count": 1,
            "disabled_command_count": 7,
        },
    ) in telemetry.events
