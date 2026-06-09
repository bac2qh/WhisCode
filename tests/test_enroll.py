from pathlib import Path
from unittest.mock import patch
import wave

import numpy as np
import pytest

from whiscode.enroll import (
    DEFAULT_REFERENCE_SECONDS,
    capture_audio,
    import_samples,
    parse_args,
    preprocess_reference_audio,
    read_wav,
    record_guided_samples,
    record_one_sample,
    validate_recording_options,
    write_wav,
)
from whiscode.handsfree import active_command_slots


def make_samples(tmp_path, count=3):
    samples = []
    for index in range(count):
        sample = tmp_path / f"sample-{index}.m4a"
        sample.write_text("audio")
        samples.append(sample)
    return samples


def write_existing_wavs(path: Path, prefix: str, indexes: list[int]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for index in indexes:
        (path / f"{prefix}-{index:02d}.wav").write_text(f"existing-{index}")


def test_parse_args_accepts_voice_memo_samples():
    args = parse_args(["wake", "one.m4a", "two.m4a", "three.m4a"])

    assert args.kind == "wake"
    assert args.samples == ["one.m4a", "two.m4a", "three.m4a"]


def test_parse_args_accepts_command_samples():
    args = parse_args(["scroll-down", "one.m4a", "two.m4a", "three.m4a", "--command-dir", "/tmp/commands"])

    assert args.kind == "scroll-down"
    assert args.command_dir == Path("/tmp/commands")


def test_parse_args_accepts_record_mode():
    args = parse_args([
        "--record",
        "--sample-count",
        "4",
        "--seconds",
        "1.5",
        "--telemetry-path",
        "/tmp/events.jsonl",
        "--command-dir",
        "/tmp/commands",
        "--command-config",
        "/tmp/commands.ini",
        "--no-recording-overlay",
        "--no-telemetry",
    ])

    assert args.record is True
    assert args.sample_count == 4
    assert args.seconds == 1.5
    assert args.telemetry_path == Path("/tmp/events.jsonl")
    assert args.command_dir == Path("/tmp/commands")
    assert args.command_config == Path("/tmp/commands.ini")
    assert args.recording_overlay is False
    assert args.no_telemetry is True


def test_parse_args_accepts_record_missing_mode():
    args = parse_args(["--record", "--record-missing", "--sample-count", "4"])

    assert args.record is True
    assert args.record_missing is True
    assert args.sample_count == 4


@pytest.mark.parametrize(
    "argv",
    [
        ["--record-missing"],
        ["wake", "one.m4a", "two.m4a", "three.m4a", "--record-missing"],
    ],
)
def test_parse_args_rejects_record_missing_without_record(argv):
    with pytest.raises(SystemExit):
        parse_args(argv)


@pytest.mark.parametrize(
    "argv",
    [
        ["chunk", "one.m4a", "two.m4a", "three.m4a"],
        ["--record", "--include-chunk"],
        ["--record", "--chunk-dir", "/tmp/chunk"],
    ],
)
def test_parse_args_rejects_removed_chunk_enrollment_options(argv):
    with pytest.raises(SystemExit):
        parse_args(argv)


def test_parse_args_recording_overlay_defaults_on():
    args = parse_args(["--record"])

    assert args.recording_overlay is True


def test_import_samples_converts_to_16khz_mono_wav(tmp_path):
    samples = make_samples(tmp_path)
    wake_dir = tmp_path / "wake"

    def fake_run(command, check):
        write_wav(Path(command[2]), np.array([0.25, -0.25], dtype=np.float32))

    with patch("subprocess.run", side_effect=fake_run) as mock_run:
        written = import_samples(
            "wake",
            samples,
            wake_dir=wake_dir,
            end_dir=tmp_path / "end",
            preprocess_fn=lambda audio: audio,
        )

    assert written == [wake_dir / "wake-01.wav", wake_dir / "wake-02.wav", wake_dir / "wake-03.wav"]
    first_call = mock_run.call_args_list[0].args[0]
    assert first_call == [
        "afconvert",
        str(samples[0]),
        str(wake_dir / "wake-01.wav"),
        "-f",
        "WAVE",
        "-d",
        "LEI16@16000",
        "-c",
        "1",
    ]


def test_import_samples_uses_end_folder(tmp_path):
    samples = make_samples(tmp_path)
    end_dir = tmp_path / "end"

    def fake_run(command, check):
        write_wav(Path(command[2]), np.array([0.25, -0.25], dtype=np.float32))

    with patch("subprocess.run", side_effect=fake_run):
        written = import_samples(
            "end",
            samples,
            wake_dir=tmp_path / "wake",
            end_dir=end_dir,
            preprocess_fn=lambda audio: audio,
        )

    assert written[0] == end_dir / "end-01.wav"


def test_import_samples_uses_command_folder(tmp_path):
    samples = make_samples(tmp_path)
    command_dir = tmp_path / "commands"

    def fake_run(command, check):
        write_wav(Path(command[2]), np.array([0.25, -0.25], dtype=np.float32))

    with patch("subprocess.run", side_effect=fake_run):
        written = import_samples(
            "scroll-up",
            samples,
            wake_dir=tmp_path / "wake",
            end_dir=tmp_path / "end",
            command_dir=command_dir,
            preprocess_fn=lambda audio: audio,
        )

    assert written[0] == command_dir / "scroll-up" / "scroll-up-01.wav"


def test_import_samples_requires_three_samples(tmp_path):
    samples = make_samples(tmp_path, count=2)

    with pytest.raises(ValueError, match="at least 3"):
        import_samples("wake", samples, wake_dir=tmp_path / "wake", end_dir=tmp_path / "end")


def test_import_samples_rejects_missing_file(tmp_path):
    samples = [tmp_path / "missing-1.m4a", tmp_path / "missing-2.m4a", tmp_path / "missing-3.m4a"]

    with pytest.raises(FileNotFoundError, match="Sample not found"):
        import_samples("wake", samples, wake_dir=tmp_path / "wake", end_dir=tmp_path / "end")


def test_record_guided_samples_records_wake_and_end_defaults(tmp_path):
    captured_prompts = []
    audio = np.array([0.1, -0.1], dtype=np.float32)

    written = record_guided_samples(
        wake_dir=tmp_path / "wake",
        end_dir=tmp_path / "end",
        command_dir=tmp_path / "commands",
        input_fn=lambda prompt: captured_prompts.append(prompt),
        capture_fn=lambda seconds: audio,
        preprocess_fn=lambda audio: audio,
    )

    assert len(written) == 36
    assert written[0] == tmp_path / "wake" / "wake-01.wav"
    assert written[3] == tmp_path / "end" / "end-01.wav"
    assert written[6] == tmp_path / "commands" / "page-up" / "page-up-01.wav"
    assert written[9] == tmp_path / "commands" / "page-down" / "page-down-01.wav"
    assert written[12] == tmp_path / "commands" / "enter" / "enter-01.wav"
    assert written[15] == tmp_path / "commands" / "shift-enter" / "shift-enter-01.wav"
    assert written[18] == tmp_path / "commands" / "shift-tab" / "shift-tab-01.wav"
    assert written[21] == tmp_path / "commands" / "tab" / "tab-01.wav"
    assert written[24] == tmp_path / "commands" / "arrow-up" / "arrow-up-01.wav"
    assert written[27] == tmp_path / "commands" / "arrow-down" / "arrow-down-01.wav"
    assert written[30] == tmp_path / "commands" / "scroll-up" / "scroll-up-01.wav"
    assert written[33] == tmp_path / "commands" / "scroll-down" / "scroll-down-01.wav"
    assert len(captured_prompts) == 36
    assert any("command phrase for Page Up" in prompt for prompt in captured_prompts)
    assert any("command phrase for Shift+Enter" in prompt for prompt in captured_prompts)
    assert any("command phrase for Shift+Tab" in prompt for prompt in captured_prompts)
    assert any("command phrase for Tab" in prompt for prompt in captured_prompts)
    assert any("command phrase for Arrow Up" in prompt for prompt in captured_prompts)
    assert any("command phrase for Arrow Down" in prompt for prompt in captured_prompts)
    assert any("command phrase for Scroll Up" in prompt for prompt in captured_prompts)
    assert any("command phrase for Scroll Down" in prompt for prompt in captured_prompts)
    assert all(path.exists() for path in written)


def test_record_guided_samples_honors_count_and_seconds(tmp_path):
    seconds_seen = []

    written = record_guided_samples(
        wake_dir=tmp_path / "wake",
        end_dir=tmp_path / "end",
        command_dir=tmp_path / "commands",
        sample_count=4,
        seconds=1.25,
        input_fn=lambda prompt: None,
        capture_fn=lambda seconds: seconds_seen.append(seconds) or np.array([0.0], dtype=np.float32),
        preprocess_fn=lambda audio: audio,
    )

    assert len(written) == 48
    assert seconds_seen == [1.25] * 48


def test_record_guided_samples_accepts_enabled_command_slots(tmp_path):
    audio = np.array([0.1, -0.1], dtype=np.float32)

    written = record_guided_samples(
        wake_dir=tmp_path / "wake",
        end_dir=tmp_path / "end",
        command_dir=tmp_path / "commands",
        input_fn=lambda prompt: None,
        capture_fn=lambda seconds: audio,
        preprocess_fn=lambda audio: audio,
        command_slots=(),
    )

    assert len(written) == 6
    assert written[0] == tmp_path / "wake" / "wake-01.wav"
    assert written[3] == tmp_path / "end" / "end-01.wav"
    assert not (tmp_path / "commands").exists()


def test_record_guided_samples_full_record_ignores_existing_counts(tmp_path):
    wake_dir = tmp_path / "wake"
    end_dir = tmp_path / "end"
    write_existing_wavs(wake_dir, "wake", [1, 2, 3])

    written = record_guided_samples(
        wake_dir=wake_dir,
        end_dir=end_dir,
        command_dir=tmp_path / "commands",
        input_fn=lambda prompt: None,
        capture_fn=lambda seconds: np.array([0.2], dtype=np.float32),
        preprocess_fn=lambda audio: audio,
        command_slots=(),
    )

    assert written == [
        wake_dir / "wake-01.wav",
        wake_dir / "wake-02.wav",
        wake_dir / "wake-03.wav",
        end_dir / "end-01.wav",
        end_dir / "end-02.wav",
        end_dir / "end-03.wav",
    ]
    with wave.open(str(wake_dir / "wake-01.wav"), "rb") as f:
        assert f.getnframes() == 1


def test_record_guided_samples_record_missing_tops_up_enabled_sets_without_overwrite(tmp_path, capsys):
    wake_dir = tmp_path / "wake"
    end_dir = tmp_path / "end"
    command_dir = tmp_path / "commands"
    config_path = tmp_path / "commands.ini"
    config_path.write_text("[commands]\nenter = false\nscroll-up = true\nscroll-down = true\n")
    write_existing_wavs(wake_dir, "wake", [1, 2, 3])
    write_existing_wavs(end_dir, "end", [1, 3])
    write_existing_wavs(command_dir / "scroll-up", "scroll-up", [1, 2, 3])
    write_existing_wavs(command_dir / "scroll-down", "scroll-down", [1])
    slots = active_command_slots(config_path, base_dir=command_dir)
    prompts = []

    written = record_guided_samples(
        wake_dir=wake_dir,
        end_dir=end_dir,
        command_dir=command_dir,
        input_fn=lambda prompt: prompts.append(prompt),
        capture_fn=lambda seconds: np.array([0.2], dtype=np.float32),
        preprocess_fn=lambda audio: audio,
        command_slots=slots,
        record_missing=True,
    )

    assert written == [
        end_dir / "end-02.wav",
        command_dir / "scroll-down" / "scroll-down-02.wav",
        command_dir / "scroll-down" / "scroll-down-03.wav",
    ]
    assert (wake_dir / "wake-01.wav").read_text() == "existing-1"
    assert (end_dir / "end-01.wav").read_text() == "existing-1"
    assert (end_dir / "end-03.wav").read_text() == "existing-3"
    assert (command_dir / "scroll-up" / "scroll-up-01.wav").read_text() == "existing-1"
    assert not (command_dir / "enter").exists()
    assert len(prompts) == 3
    assert any("end phrase" in prompt for prompt in prompts)
    assert any("command phrase for Scroll Down" in prompt for prompt in prompts)
    assert all("Scroll Up" not in prompt for prompt in prompts)

    out = capsys.readouterr().out
    assert "Skipping wake phrase" in out
    assert "Skipping command phrase for Scroll Up" in out
    assert "Recorded phrase set(s): end phrase +1" in out
    assert "command phrase for Scroll Down +2" in out


class FakeTelemetry:
    def __init__(self):
        self.events = []

    def emit(self, event, **properties):
        self.events.append((event, properties))


def test_record_guided_samples_emits_telemetry(tmp_path):
    telemetry = FakeTelemetry()

    record_guided_samples(
        wake_dir=tmp_path / "wake",
        end_dir=tmp_path / "end",
        command_dir=tmp_path / "commands",
        input_fn=lambda prompt: None,
        capture_fn=lambda seconds: np.array([0.0], dtype=np.float32),
        preprocess_fn=lambda audio: audio,
        telemetry=telemetry,
    )

    event_names = [event for event, properties in telemetry.events]
    assert event_names[0] == "enrollment.guided_started"
    assert event_names.count("enrollment.sample_started") == 36
    assert event_names.count("enrollment.sample_completed") == 36
    assert event_names[-1] == "enrollment.guided_completed"


class FakeOverlay:
    def __init__(self):
        self.calls = []
        self.levels = []

    def show(self):
        self.calls.append("show")

    def hide(self):
        self.calls.append("hide")

    def update_level(self, audio):
        self.levels.append(np.asarray(audio, dtype=np.float32).copy())


def test_record_guided_samples_uses_overlay_for_each_sample(tmp_path):
    overlay = FakeOverlay()

    def capture_fn(seconds, *, level_callback=None):
        audio = np.array([0.25, -0.25], dtype=np.float32)
        level_callback(audio)
        return audio

    record_guided_samples(
        wake_dir=tmp_path / "wake",
        end_dir=tmp_path / "end",
        command_dir=tmp_path / "commands",
        input_fn=lambda prompt: None,
        capture_fn=capture_fn,
        preprocess_fn=lambda audio: audio,
        overlay=overlay,
    )

    assert overlay.calls == ["show", "hide"] * 36
    assert len(overlay.levels) == 36
    np.testing.assert_array_equal(overlay.levels[0], np.array([0.25, -0.25], dtype=np.float32))


def test_record_one_sample_hides_overlay_when_capture_fails(tmp_path):
    overlay = FakeOverlay()

    def capture_fn(seconds, *, level_callback=None):
        raise RuntimeError("microphone failed")

    with pytest.raises(RuntimeError, match="microphone failed"):
        record_one_sample(
            "wake",
            1,
            2.0,
            tmp_path / "wake",
            input_fn=lambda prompt: None,
            capture_fn=capture_fn,
            preprocess_fn=lambda audio: audio,
            overlay=overlay,
        )

    assert overlay.calls == ["show", "hide"]


class FakeStream:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, frames):
        return np.ones((frames, 1), dtype=np.float32) * 0.5, False


def test_capture_audio_reports_levels_for_chunks():
    levels = []

    audio = capture_audio(
        0.2,
        stream_factory=lambda: (FakeStream(), 10),
        level_callback=lambda chunk: levels.append(chunk.copy()),
    )

    assert len(levels) == 2
    np.testing.assert_array_equal(levels[0], np.array([0.5], dtype=np.float32))
    assert len(audio) == int(0.2 * 16000)
    np.testing.assert_allclose(audio, np.full(len(audio), 0.5, dtype=np.float32))


def test_record_guided_samples_rejects_invalid_options():
    with pytest.raises(ValueError, match="at least 3"):
        validate_recording_options(2, 2.0)
    with pytest.raises(ValueError, match="positive"):
        validate_recording_options(3, 0)


def test_write_wav_writes_16khz_mono_file(tmp_path):
    path = tmp_path / "sample.wav"

    write_wav(path, np.array([0.0, 0.5], dtype=np.float32))

    with wave.open(str(path), "rb") as f:
        assert f.getnchannels() == 1
        assert f.getframerate() == 16000
        assert f.getsampwidth() == 2
        assert f.getnframes() == 2


def test_read_wav_round_trips_written_audio(tmp_path):
    path = tmp_path / "sample.wav"

    write_wav(path, np.array([0.0, 0.5], dtype=np.float32))

    audio = read_wav(path)
    assert audio.shape == (2,)
    assert audio[0] == 0.0
    assert audio[1] > 0.49


def test_preprocess_reference_audio_trims_and_pads():
    audio = np.arange(10, dtype=np.float32)

    processed = preprocess_reference_audio(
        audio,
        trim_fn=lambda shaped, sample_rate: shaped[3:7],
        min_samples=8,
    )

    np.testing.assert_array_equal(processed, np.array([0, 0, 3, 4, 5, 6, 0, 0], dtype=np.float32))


def test_preprocess_reference_audio_defaults_to_detector_window_length():
    audio = np.arange(10, dtype=np.float32)

    processed = preprocess_reference_audio(
        audio,
        sample_rate=10,
        trim_fn=lambda shaped, sample_rate: shaped[3:7],
    )

    assert len(processed) == int(DEFAULT_REFERENCE_SECONDS * 10)
    np.testing.assert_array_equal(processed[8:12], np.array([3, 4, 5, 6], dtype=np.float32))


def test_preprocess_reference_audio_preserves_audio_when_trim_finds_no_speech():
    audio = np.array([0.1, -0.1], dtype=np.float32)

    processed = preprocess_reference_audio(
        audio,
        trim_fn=lambda shaped, sample_rate: shaped,
        min_samples=4,
    )

    np.testing.assert_allclose(processed, np.array([0.0, 0.1, -0.1, 0.0], dtype=np.float32))
