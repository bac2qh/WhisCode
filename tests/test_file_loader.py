import numpy as np
from unittest.mock import MagicMock, patch

from whiscode.file_loader import load_audio_file


class TestLoadAudioFile:
    def test_returns_empty_array_on_error(self):
        with patch('whiscode.file_loader.sf.read') as mock_read:
            mock_read.side_effect = Exception("File not found")
            result = load_audio_file("/nonexistent/file.ogg")
            assert len(result) == 0
            assert result.dtype == np.float32

    def test_converts_stereo_to_mono(self):
        with patch('whiscode.file_loader.sf.read') as mock_read:
            # Stereo audio: shape (100, 2)
            stereo = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]] * 33 + [[0.1, 0.2]], dtype=np.float32)
            mock_read.return_value = (stereo, 16000)

            result = load_audio_file("/path/to/file.wav")

            # Should be mono now
            assert len(result.shape) == 1
            # Mean of [0.1, 0.2] = 0.15
            assert result[0] == 0.15

    def test_resamples_to_target_rate(self):
        with patch('whiscode.file_loader.sf.read') as mock_read:
            # 1 second of 48kHz audio
            audio = np.ones(48000, dtype=np.float32)
            mock_read.return_value = (audio, 48000)

            result = load_audio_file("/path/to/file.wav", target_rate=16000)

            # Should be resampled to 16kHz (1 second)
            assert len(result) == 16000

    def test_no_resampling_when_rates_match(self):
        with patch('whiscode.file_loader.sf.read') as mock_read:
            audio = np.ones(16000, dtype=np.float32)
            mock_read.return_value = (audio, 16000)

            result = load_audio_file("/path/to/file.wav", target_rate=16000)

            assert len(result) == 16000
            np.testing.assert_array_equal(result, audio)
