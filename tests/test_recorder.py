import numpy as np

from whiscode.recorder import Recorder, normalize_for_transcription


def test_recorder_callback_reports_audio_level():
    levels = []
    recorder = Recorder(level_callback=levels.append)
    audio = np.array([[0.04], [0.08]], dtype=np.float32)

    recorder._callback(audio, frames=2, time_info=None, status=None)

    assert len(recorder._chunks) == 1
    assert len(levels) == 1
    assert 0 < levels[0] < 1


def test_recorder_callback_caps_audio_and_reports_timeout_once():
    timeouts = []
    recorder = Recorder(max_seconds=1.0, timeout_callback=lambda: timeouts.append("timeout"))
    recorder._max_frames = 3
    audio = np.array([[0.01], [0.02], [0.03], [0.04], [0.05]], dtype=np.float32)

    recorder._callback(audio, frames=5, time_info=None, status=None)
    recorder._callback(audio, frames=5, time_info=None, status=None)

    captured = np.concatenate(recorder._chunks, axis=0).flatten()
    np.testing.assert_allclose(captured, [0.01, 0.02, 0.03])
    assert timeouts == ["timeout"]


def test_normalize_for_transcription_boosts_quiet_audio():
    audio = np.array([0.005, -0.005], dtype=np.float32)

    normalized = normalize_for_transcription(audio)

    assert normalized.applied is True
    assert normalized.gain == 8.0
    np.testing.assert_allclose(normalized.audio, [0.04, -0.04])
    assert normalized.output_rms > normalized.input_rms


def test_normalize_for_transcription_respects_peak_limit():
    audio = np.concatenate([
        np.full(1000, 0.01, dtype=np.float32),
        np.array([0.5], dtype=np.float32),
    ])

    normalized = normalize_for_transcription(audio)

    assert normalized.applied is True
    assert normalized.gain == 1.9
    assert normalized.output_peak <= 0.95


def test_normalize_for_transcription_leaves_silence_unchanged():
    audio = np.zeros(8, dtype=np.float32)

    normalized = normalize_for_transcription(audio)

    assert normalized.applied is False
    assert normalized.gain == 1.0
    np.testing.assert_array_equal(normalized.audio, audio)
