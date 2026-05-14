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
