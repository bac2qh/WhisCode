import numpy as np

from whiscode.recorder import Recorder


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
