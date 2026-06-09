from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class DeferredDeliveryState:
    batch_id: str
    successful_chunks: int
    skipped_chunks: int
    text_chars: int


@dataclass(frozen=True)
class DeferredDeliveryFlush:
    batch_id: str
    text: str
    successful_chunks: int
    skipped_chunks: int
    text_chars: int


@dataclass
class _DeferredBatch:
    text: str = ""
    successful_chunks: int = 0
    skipped_chunks: int = 0


class DeferredTranscriptBuffer:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._batches: dict[str, _DeferredBatch] = {}
        self._final_job_ids: set[str] = set()

    def append(self, batch_id: str, text: str) -> DeferredDeliveryState:
        with self._lock:
            batch = self._batches.setdefault(batch_id, _DeferredBatch())
            batch.text += text
            batch.successful_chunks += 1
            return self._state(batch_id, batch)

    def skip(self, batch_id: str) -> DeferredDeliveryState:
        with self._lock:
            batch = self._batches.setdefault(batch_id, _DeferredBatch())
            batch.skipped_chunks += 1
            return self._state(batch_id, batch)

    def flush(self, batch_id: str) -> DeferredDeliveryFlush:
        with self._lock:
            batch = self._batches.pop(batch_id, _DeferredBatch())
            return DeferredDeliveryFlush(
                batch_id=batch_id,
                text=batch.text,
                successful_chunks=batch.successful_chunks,
                skipped_chunks=batch.skipped_chunks,
                text_chars=len(batch.text),
            )

    def mark_final_job(self, job_id: str) -> None:
        with self._lock:
            self._final_job_ids.add(job_id)

    def consume_final_job(self, job_id: str) -> bool:
        with self._lock:
            if job_id not in self._final_job_ids:
                return False
            self._final_job_ids.remove(job_id)
            return True

    @staticmethod
    def _state(batch_id: str, batch: _DeferredBatch) -> DeferredDeliveryState:
        return DeferredDeliveryState(
            batch_id=batch_id,
            successful_chunks=batch.successful_chunks,
            skipped_chunks=batch.skipped_chunks,
            text_chars=len(batch.text),
        )
