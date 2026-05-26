from __future__ import annotations

import hashlib
import json
import queue
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from whiscode.recorder import SAMPLE_RATE, _resample

DEFAULT_EXTERNAL_EXTENSIONS = (".wav", ".mp3", ".flac", ".ogg", ".opus", ".m4a", ".aac")
DEFAULT_EXTERNAL_POLL_SECONDS = 2.0
DEFAULT_EXTERNAL_STABLE_SECONDS = 5.0
_MAX_ERROR_MESSAGE_CHARS = 500


@dataclass(frozen=True)
class ExternalTranscriptionConfig:
    inbox: Path
    outbox: Path
    extensions: tuple[str, ...] = DEFAULT_EXTERNAL_EXTENSIONS
    poll_seconds: float = DEFAULT_EXTERNAL_POLL_SECONDS
    stable_seconds: float = DEFAULT_EXTERNAL_STABLE_SECONDS


@dataclass(frozen=True)
class ExternalFileJob:
    path: Path
    basename: str
    extension: str
    size_bytes: int
    mtime_ns: int
    file_id: str
    queued_at: float


@dataclass(frozen=True)
class ExternalJobResult:
    status: str
    audio_seconds: float | None
    transcript: str
    processing_seconds: float
    text_path: Path
    json_path: Path
    error_type: str | None = None


@dataclass
class _ObservedFile:
    size_bytes: int
    mtime_ns: int
    changed_at: float
    seen_emitted: bool = False


class ExternalFileQueue:
    def __init__(self):
        self._queue: queue.Queue[ExternalFileJob] = queue.Queue()

    def put(self, job: ExternalFileJob) -> None:
        self._queue.put_nowait(job)

    def get(self, *, timeout: float) -> ExternalFileJob | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def requeue(self, job: ExternalFileJob) -> None:
        self._queue.put_nowait(job)

    def complete(self) -> None:
        self._queue.task_done()

    def pending_depth(self) -> int:
        return self._queue.qsize()


class ExternalAudioWatcher:
    def __init__(
        self,
        config: ExternalTranscriptionConfig,
        external_queue: ExternalFileQueue,
        *,
        telemetry=None,
    ):
        self.config = config
        self.external_queue = external_queue
        self.telemetry = telemetry
        self._observed: dict[Path, _ObservedFile] = {}
        self._queued_keys: set[tuple[str, int, int]] = set()

    def scan_once(self, *, now: float | None = None) -> list[ExternalFileJob]:
        now = time.monotonic() if now is None else now
        self.config.outbox.mkdir(parents=True, exist_ok=True)
        queued: list[ExternalFileJob] = []
        try:
            entries = list(self.config.inbox.iterdir())
        except FileNotFoundError:
            self.config.inbox.mkdir(parents=True, exist_ok=True)
            entries = []

        current_paths: set[Path] = set()
        for path in entries:
            if not path.is_file() or path.name.startswith("."):
                continue
            extension = path.suffix.lower()
            if extension not in self.config.extensions:
                continue
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            current_paths.add(path)
            key = (path.name, int(stat.st_size), int(stat.st_mtime_ns))
            file_id = external_file_id(path.name, int(stat.st_size), int(stat.st_mtime_ns))
            if result_exists(self.config.outbox, source_stem=path.stem, file_id=file_id):
                self._queued_keys.discard(key)
                self._observed.pop(path, None)
                continue

            observed = self._observed.get(path)
            if observed is None or observed.size_bytes != stat.st_size or observed.mtime_ns != stat.st_mtime_ns:
                observed = _ObservedFile(
                    size_bytes=int(stat.st_size),
                    mtime_ns=int(stat.st_mtime_ns),
                    changed_at=now,
                )
                self._observed[path] = observed

            if not observed.seen_emitted:
                observed.seen_emitted = True
                if self.telemetry:
                    self.telemetry.emit(
                        "external.file_seen",
                        file_id=file_id,
                        extension=extension,
                        size_bytes=int(stat.st_size),
                    )

            if key in self._queued_keys:
                continue
            if now - observed.changed_at < self.config.stable_seconds:
                continue

            job = ExternalFileJob(
                path=path,
                basename=path.name,
                extension=extension,
                size_bytes=int(stat.st_size),
                mtime_ns=int(stat.st_mtime_ns),
                file_id=file_id,
                queued_at=time.time(),
            )
            self.external_queue.put(job)
            self._queued_keys.add(key)
            queued.append(job)
            if self.telemetry:
                self.telemetry.emit(
                    "external.file_queued",
                    file_id=file_id,
                    extension=extension,
                    size_bytes=job.size_bytes,
                    queue_depth=self.external_queue.pending_depth(),
                )

        for path in list(self._observed):
            if path not in current_paths:
                self._observed.pop(path, None)
        return queued


def watch_external_inbox(
    watcher: ExternalAudioWatcher,
    *,
    stop_event,
) -> None:
    if watcher.telemetry:
        watcher.telemetry.emit(
            "external.watcher_started",
            extensions=list(watcher.config.extensions),
            poll_seconds=watcher.config.poll_seconds,
            stable_seconds=watcher.config.stable_seconds,
        )
    while not stop_event.is_set():
        watcher.scan_once()
        stop_event.wait(watcher.config.poll_seconds)


def parse_external_extensions(value: str | Iterable[str] | None) -> tuple[str, ...]:
    if value is None:
        return DEFAULT_EXTERNAL_EXTENSIONS
    raw_values = value.split(",") if isinstance(value, str) else list(value)
    extensions: list[str] = []
    for raw in raw_values:
        item = str(raw).strip().lower()
        if not item:
            continue
        if not item.startswith("."):
            item = "." + item
        if item not in extensions:
            extensions.append(item)
    return tuple(extensions) or DEFAULT_EXTERNAL_EXTENSIONS


def default_external_outbox(inbox: Path) -> Path:
    return inbox.expanduser().parent / "outbox"


def load_external_audio(path: Path) -> tuple[np.ndarray, float]:
    try:
        from mlx_audio.audio_io import read

        audio, sample_rate = read(str(path))
    except Exception as e:
        raise RuntimeError(f"could not read external audio file: {e}") from e
    normalized = normalize_audio(audio, int(sample_rate))
    return normalized, len(normalized) / SAMPLE_RATE if len(normalized) else 0.0


def process_external_transcription_job(
    config: ExternalTranscriptionConfig,
    job: ExternalFileJob,
    *,
    transcribe_audio,
    backend: str,
    model_label: str,
    audio_loader=load_external_audio,
) -> ExternalJobResult:
    started = time.monotonic()
    audio_seconds = None
    try:
        audio, audio_seconds = audio_loader(job.path)
        transcript = transcribe_audio(audio)
        text_path, json_path = write_success_sidecars(
            config.outbox,
            job,
            transcript=transcript,
            audio_seconds=audio_seconds,
            backend=backend,
            model_label=model_label,
            processing_seconds=time.monotonic() - started,
        )
        return ExternalJobResult(
            status="success",
            audio_seconds=audio_seconds,
            transcript=transcript,
            processing_seconds=time.monotonic() - started,
            text_path=text_path,
            json_path=json_path,
            error_type=None,
        )
    except Exception as e:
        text_path, json_path = write_error_sidecars(
            config.outbox,
            job,
            error=e,
            audio_seconds=audio_seconds,
            backend=backend,
            model_label=model_label,
            processing_seconds=time.monotonic() - started,
        )
        return ExternalJobResult(
            status="failed",
            audio_seconds=audio_seconds,
            transcript="",
            processing_seconds=time.monotonic() - started,
            text_path=text_path,
            json_path=json_path,
            error_type=type(e).__name__,
        )


def normalize_audio(audio, sample_rate: int) -> np.ndarray:
    array = np.asarray(audio)
    if array.size == 0:
        return np.array([], dtype=np.float32)
    if np.issubdtype(array.dtype, np.integer):
        max_value = max(1, np.iinfo(array.dtype).max)
        array = array.astype(np.float32) / max_value
    else:
        array = array.astype(np.float32)

    if array.ndim > 1:
        array = _mono(array)
    else:
        array = array.flatten()
    array = np.nan_to_num(array, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    if sample_rate <= 0:
        raise ValueError("external audio sample rate must be positive")
    if sample_rate != SAMPLE_RATE:
        array = _resample(array, sample_rate, SAMPLE_RATE)
    return np.asarray(array, dtype=np.float32).flatten()


def write_success_sidecars(
    outbox: Path,
    job: ExternalFileJob,
    *,
    transcript: str,
    audio_seconds: float,
    backend: str,
    model_label: str,
    processing_seconds: float,
) -> tuple[Path, Path]:
    payload = _base_payload(job, status="success", audio_seconds=audio_seconds, backend=backend, model_label=model_label)
    payload["processing_seconds"] = round(processing_seconds, 3)
    payload["transcript"] = transcript
    text_path, json_path = result_paths(outbox, source_stem=Path(job.basename).stem, file_id=job.file_id)
    _write_atomic_text(text_path, transcript)
    _write_atomic_json(json_path, payload)
    return text_path, json_path


def write_error_sidecars(
    outbox: Path,
    job: ExternalFileJob,
    *,
    error: Exception,
    audio_seconds: float | None,
    backend: str,
    model_label: str,
    processing_seconds: float,
) -> tuple[Path, Path]:
    payload = _base_payload(job, status="failed", audio_seconds=audio_seconds, backend=backend, model_label=model_label)
    payload["processing_seconds"] = round(processing_seconds, 3)
    payload["error"] = {
        "type": type(error).__name__,
        "message": str(error)[:_MAX_ERROR_MESSAGE_CHARS],
    }
    text_path, json_path = result_paths(outbox, source_stem=Path(job.basename).stem, file_id=job.file_id)
    _write_atomic_text(text_path, "")
    _write_atomic_json(json_path, payload)
    return text_path, json_path


def result_exists(outbox: Path, *, source_stem: str, file_id: str) -> bool:
    text_path, json_path = result_paths(outbox, source_stem=source_stem, file_id=file_id)
    return text_path.exists() or json_path.exists()


def result_paths(outbox: Path, *, source_stem: str, file_id: str) -> tuple[Path, Path]:
    safe_stem = sanitize_stem(source_stem)
    base = f"{safe_stem}-{file_id}"
    return outbox / f"{base}.txt", outbox / f"{base}.json"


def external_file_id(basename: str, size_bytes: int, mtime_ns: int) -> str:
    material = f"{basename}\0{int(size_bytes)}\0{int(mtime_ns)}".encode("utf-8", errors="replace")
    return hashlib.sha256(material).hexdigest()[:10]


def sanitize_stem(stem: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", stem.strip()).strip(".-")
    return cleaned[:80] or "audio"


def _base_payload(
    job: ExternalFileJob,
    *,
    status: str,
    audio_seconds: float | None,
    backend: str,
    model_label: str,
) -> dict:
    return {
        "status": status,
        "source_basename": job.basename,
        "source_size_bytes": job.size_bytes,
        "source_mtime_ns": job.mtime_ns,
        "audio_seconds": round(audio_seconds, 3) if audio_seconds is not None else None,
        "backend": backend,
        "model_label": model_label,
        "file_id": job.file_id,
    }


def _mono(array: np.ndarray) -> np.ndarray:
    if array.ndim != 2:
        return array.reshape(-1)
    if array.shape[0] <= 8 and array.shape[1] > array.shape[0]:
        return array.mean(axis=0)
    return array.mean(axis=1)


def _write_atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        f.write(text)
        if text and not text.endswith("\n"):
            f.write("\n")
    tmp.replace(path)


def _write_atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        json.dump(payload, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")
    tmp.replace(path)
