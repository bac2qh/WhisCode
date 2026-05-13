from pathlib import Path
from unittest.mock import patch

import pytest

from whiscode.enroll import import_samples, parse_args


def make_samples(tmp_path, count=3):
    samples = []
    for index in range(count):
        sample = tmp_path / f"sample-{index}.m4a"
        sample.write_text("audio")
        samples.append(sample)
    return samples


def test_parse_args_accepts_voice_memo_samples():
    args = parse_args(["wake", "one.m4a", "two.m4a", "three.m4a"])

    assert args.kind == "wake"
    assert args.samples == ["one.m4a", "two.m4a", "three.m4a"]


def test_import_samples_converts_to_16khz_mono_wav(tmp_path):
    samples = make_samples(tmp_path)
    wake_dir = tmp_path / "wake"

    with patch("subprocess.run") as mock_run:
        written = import_samples("wake", samples, wake_dir=wake_dir, end_dir=tmp_path / "end")

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

    with patch("subprocess.run"):
        written = import_samples("end", samples, wake_dir=tmp_path / "wake", end_dir=end_dir)

    assert written[0] == end_dir / "end-01.wav"


def test_import_samples_requires_three_samples(tmp_path):
    samples = make_samples(tmp_path, count=2)

    with pytest.raises(ValueError, match="at least 3"):
        import_samples("wake", samples, wake_dir=tmp_path / "wake", end_dir=tmp_path / "end")


def test_import_samples_rejects_missing_file(tmp_path):
    samples = [tmp_path / "missing-1.m4a", tmp_path / "missing-2.m4a", tmp_path / "missing-3.m4a"]

    with pytest.raises(FileNotFoundError, match="Sample not found"):
        import_samples("wake", samples, wake_dir=tmp_path / "wake", end_dir=tmp_path / "end")
