import threading


class Stats:
    def __init__(self):
        self._lock = threading.Lock()
        self._transcriptions = 0
        self._words = 0
        self._audio_seconds = 0.0

    def record(self, word_count: int, audio_seconds: float):
        with self._lock:
            self._transcriptions += 1
            self._words += word_count
            self._audio_seconds += audio_seconds

    def summary(self) -> str:
        with self._lock:
            t = self._transcriptions
            w = self._words
            mins = self._audio_seconds / 60
        return f"{t} transcription{'s' if t != 1 else ''}, {w} word{'s' if w != 1 else ''}, {mins:.1f} min of audio"
