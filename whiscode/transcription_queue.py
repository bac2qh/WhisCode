from __future__ import annotations

import queue
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_TRANSCRIPTION_QUEUE_CAPACITY = 5
DEFAULT_TRANSCRIPT_RECOVERY_PATH = Path("/tmp/whiscode-last-transcripts.txt")
DEFAULT_TRANSCRIPT_RECOVERY_LIMIT = 5


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

    def finish_recording(self, *, audio: np.ndarray, audio_seconds: float, job_id: str | None = None) -> TranscriptionJob | None:
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

    def queue_depth_for_telemetry(self) -> int:
        with self._lock:
            return self._pending.qsize() + (1 if self._active_job_id is not None else 0)


@dataclass(frozen=True)
class TranscriptRecoveryEntry:
    timestamp: str
    job_id: str
    source: str
    audio_seconds: float
    text: str


@dataclass(frozen=True)
class TranscriptRecoveryWriteResult:
    ok: bool
    entry_count: int
    error_type: str | None = None


class TranscriptRecoveryLog:
    def __init__(
        self,
        *,
        path: Path = DEFAULT_TRANSCRIPT_RECOVERY_PATH,
        limit: int = DEFAULT_TRANSCRIPT_RECOVERY_LIMIT,
        clock: Any | None = None,
    ):
        self.path = Path(path)
        self.limit = max(1, int(limit))
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._entries: deque[TranscriptRecoveryEntry] = deque(maxlen=self.limit)
        self._lock = threading.Lock()

    def record(
        self,
        *,
        text: str,
        job_id: str,
        source: str,
        audio_seconds: float,
    ) -> TranscriptRecoveryWriteResult:
        entry = TranscriptRecoveryEntry(
            timestamp=self.clock().isoformat(timespec="seconds"),
            job_id=job_id,
            source=source,
            audio_seconds=float(audio_seconds),
            text=text,
        )
        with self._lock:
            self._entries.append(entry)
            rendered = self._render_locked()
            entry_count = len(self._entries)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(rendered, encoding="utf-8")
        except OSError as e:
            return TranscriptRecoveryWriteResult(ok=False, entry_count=entry_count, error_type=type(e).__name__)
        return TranscriptRecoveryWriteResult(ok=True, entry_count=entry_count)

    def _render_locked(self) -> str:
        lines = [
            "# WhisCode last transcripts",
            "# Local recovery file. Newest entry is last. This file intentionally contains transcript text.",
            "",
        ]
        for entry in self._entries:
            lines.append(
                "--- "
                f"timestamp={entry.timestamp} "
                f"job_id={entry.job_id} "
                f"source={entry.source} "
                f"audio_seconds={entry.audio_seconds:.3f}"
            )
            lines.append(entry.text)
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"
