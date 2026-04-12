import numpy as np
import soundfile as sf
from pathlib import Path


def _resample(audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    """Resample audio using linear interpolation."""
    if orig_rate == target_rate:
        return audio
    ratio = target_rate / orig_rate
    n_samples = int(len(audio) * ratio)
    indices = np.linspace(0, len(audio) - 1, n_samples)
    return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)


def load_audio_file(path: str | Path, target_rate: int = 16000) -> np.ndarray:
    """Load audio file and resample to target sample rate.

    Returns empty array on error.
    """
    try:
        data, samplerate = sf.read(str(path), dtype='float32')

        # Convert stereo to mono if needed
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)

        # Resample to target rate if needed
        if samplerate != target_rate:
            data = _resample(data, samplerate, target_rate)

        return data
    except Exception as e:
        print(f"  Error loading audio file: {e}")
        return np.array([], dtype=np.float32)
