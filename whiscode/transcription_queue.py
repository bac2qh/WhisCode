from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

import numpy as np

DEFAULT_TRANSCRIPTION_QUEUE_CAPACITY = 5


@dataclass(frozen=True)
class RecordingReservation:
    job_id: str
    source: str
    created_at: float


@dataclass(frozen=True)
class TranscriptionJob:
    job_id: str
    source: str
    audio: np.ndarray
    audio_seconds: float
    created_at: float
    queued_at: float
    text_suffix: str = ""


class TranscriptionJobQueue:
    def __init__(self, *, capacity: int = DEFAULT_TRANSCRIPTION_QUEUE_CAPACITY):
        self.capacity = max(1, int(capacity))
        self._pending: queue.Queue[TranscriptionJob] = queue.Queue(maxsize=self.capacity)
        self._lock = threading.Lock()
        self._next_id = 1
        self._reserved: RecordingReservation | None = None
        self._active_job_id: str | None = None

    def try_reserve_recording(self, *, source: str) -> RecordingReservation | None:
        with self._lock:
            if self._reserved is not None or self._pending.qsize() >= self.capacity:
                return None
            reservation = RecordingReservation(
                job_id=f"job-{self._next_id}",
                source=source,
                created_at=time.time(),
            )
            self._next_id += 1
            self._reserved = reservation
            return reservation

    def cancel_recording(self, job_id: str | None = None) -> RecordingReservation | None:
        with self._lock:
            if self._reserved is None:
                return None
            if job_id is not None and self._reserved.job_id != job_id:
                return None
            reservation = self._reserved
            self._reserved = None
            return reservation

    def finish_recording(
        self,
        *,
        audio: np.ndarray,
        audio_seconds: float,
        job_id: str | None = None,
        text_suffix: str = "",
    ) -> TranscriptionJob | None:
        with self._lock:
            if self._reserved is None:
                return None
            if job_id is not None and self._reserved.job_id != job_id:
                return None
            reservation = self._reserved
            self._reserved = None

        job = TranscriptionJob(
            job_id=reservation.job_id,
            source=reservation.source,
            audio=np.asarray(audio, dtype=np.float32).flatten(),
            audio_seconds=float(audio_seconds),
            created_at=reservation.created_at,
            queued_at=time.time(),
            text_suffix=str(text_suffix),
        )
        try:
            self._pending.put_nowait(job)
        except queue.Full:
            return None
        return job

    def get(self, *, timeout: float) -> TranscriptionJob | None:
        try:
            job = self._pending.get(timeout=timeout)
        except queue.Empty:
            return None
        with self._lock:
            self._active_job_id = job.job_id
        return job

    def complete_active(self, job_id: str) -> None:
        with self._lock:
            if self._active_job_id == job_id:
                self._active_job_id = None
        self._pending.task_done()

    def pending_depth(self) -> int:
        return self._pending.qsize()

    def is_recording_reserved(self) -> bool:
        with self._lock:
            return self._reserved is not None

    def reserved_job_id(self) -> str | None:
        with self._lock:
            return self._reserved.job_id if self._reserved is not None else None

    def active_job_id(self) -> str | None:
        with self._lock:
            return self._active_job_id

    def has_transcription_work(self) -> bool:
        with self._lock:
            return self._active_job_id is not None or not self._pending.empty()

    def is_idle(self) -> bool:
        with self._lock:
            return self._reserved is None and self._active_job_id is None and self._pending.empty()

    def queue_depth_for_telemetry(self) -> int:
        with self._lock:
            return self._pending.qsize() + (1 if self._active_job_id is not None else 0)
