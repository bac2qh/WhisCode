from typing import Callable

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
_FALLBACK_RATES = [16000, 44100, 48000, 8000, 22050, 32000, 96000]


def _get_native_samplerate() -> int:
    """Get the default input device's native sample rate."""
    info = sd.query_devices(kind="input")
    return int(info["default_samplerate"])


def _open_stream(callback=None) -> tuple[sd.InputStream, int]:
    """Open an input stream, trying native rate then fallbacks."""
    native_rate = _get_native_samplerate()
    rates_to_try = [native_rate] + [r for r in _FALLBACK_RATES if r != native_rate]

    for rate in rates_to_try:
        try:
            kwargs = {}
            if callback is not None:
                kwargs["callback"] = callback
            stream = sd.InputStream(
                samplerate=rate,
                channels=1,
                dtype="float32",
                **kwargs,
            )
            return stream, rate
        except sd.PortAudioError:
            continue

    raise RuntimeError(
        f"Could not open audio input at any sample rate. "
        f"Tried: {rates_to_try}. Check your audio device settings."
    )


def open_input_stream(callback=None) -> tuple[sd.InputStream, int]:
    return _open_stream(callback)


def _resample(audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    """Resample audio using linear interpolation."""
    if orig_rate == target_rate:
        return audio
    ratio = target_rate / orig_rate
    n_samples = int(len(audio) * ratio)
    indices = np.linspace(0, len(audio) - 1, n_samples)
    return np.interp(indices, np.arange(len(audio)), audio).astype(np.float32)


class Recorder:
    def __init__(self, level_callback: Callable[[float], None] | None = None):
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._actual_rate: int = SAMPLE_RATE
        self._level_callback = level_callback

    def start(self):
        self._chunks = []
        self._stream, self._actual_rate = _open_stream(self._callback)
        if self._actual_rate != SAMPLE_RATE:
            print(f"  (recording at {self._actual_rate}Hz, will resample to {SAMPLE_RATE}Hz)")
        self._stream.start()

    def _callback(self, indata: np.ndarray, frames, time_info, status):
        self._chunks.append(indata.copy())
        if self._level_callback:
            self._level_callback(_audio_level(indata))

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if not self._chunks:
            return np.array([], dtype=np.float32)
        audio = np.concatenate(self._chunks, axis=0).flatten()
        if self._actual_rate != SAMPLE_RATE:
            audio = _resample(audio, self._actual_rate, SAMPLE_RATE)
        return audio


def _audio_level(audio: np.ndarray) -> float:
    audio = np.asarray(audio, dtype=np.float32).flatten()
    if len(audio) == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float32))))
    return min(1.0, rms / 0.08)
