from __future__ import annotations

import hashlib
import json
import queue
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol
from urllib.parse import unquote, urlparse

import numpy as np

from whiscode.recorder import SAMPLE_RATE, _resample

DEFAULT_EXTERNAL_EXTENSIONS = (".wav", ".mp3", ".flac", ".ogg", ".opus", ".m4a", ".aac")
DEFAULT_EXTERNAL_POLL_SECONDS = 2.0
DEFAULT_EXTERNAL_STABLE_SECONDS = 5.0
DEFAULT_EXTERNAL_TARGET_ID = "default"
_MAX_ERROR_MESSAGE_CHARS = 500


class ExternalConfigError(ValueError):
    pass


@dataclass(frozen=True)
class SmbCredentials:
    username: str
    password: str
    domain: str | None = None


@dataclass(frozen=True)
class SmbLocation:
    raw_url: str
    host: str
    share: str
    parts: tuple[str, ...]

    @property
    def basename(self) -> str:
        return self.parts[-1] if self.parts else self.share

    @property
    def parent(self) -> "SmbLocation":
        return SmbLocation(
            raw_url=_smb_url(self.host, self.share, self.parts[:-1]),
            host=self.host,
            share=self.share,
            parts=self.parts[:-1],
        )

    def child(self, name: str) -> "SmbLocation":
        return SmbLocation(
            raw_url=_smb_url(self.host, self.share, (*self.parts, name)),
            host=self.host,
            share=self.share,
            parts=(*self.parts, name),
        )

    def sibling(self, name: str) -> "SmbLocation":
        return self.parent.child(name)

    def unc(self) -> str:
        segments = [self.host, self.share, *self.parts]
        return "\\\\" + "\\".join(segments)


@dataclass(frozen=True)
class ExternalFileEntry:
    location: str
    basename: str
    extension: str
    size_bytes: int
    mtime_ns: int

    @property
    def stem(self) -> str:
        return Path(self.basename).stem


@dataclass(frozen=True)
class ExternalTranscriptionConfig:
    storage: "ExternalStorage"
    extensions: tuple[str, ...] = DEFAULT_EXTERNAL_EXTENSIONS
    poll_seconds: float = DEFAULT_EXTERNAL_POLL_SECONDS
    stable_seconds: float = DEFAULT_EXTERNAL_STABLE_SECONDS


@dataclass(frozen=True)
class ExternalTranscriptionTarget:
    target_id: str
    config: ExternalTranscriptionConfig


@dataclass(frozen=True)
class ExternalFileJob:
    location: str
    basename: str
    extension: str
    size_bytes: int
    mtime_ns: int
    file_id: str
    queued_at: float
    target_id: str = DEFAULT_EXTERNAL_TARGET_ID


@dataclass(frozen=True)
class ExternalJobResult:
    status: str
    audio_seconds: float | None
    transcript: str
    processing_seconds: float
    text_location: str
    json_location: str
    error_type: str | None = None


@dataclass
class _ObservedFile:
    size_bytes: int
    mtime_ns: int
    changed_at: float
    seen_emitted: bool = False


class ExternalStorage(Protocol):
    scheme: str

    def safe_description(self) -> str:
        ...

    def ensure_ready(self) -> None:
        ...

    def list_files(self) -> list[ExternalFileEntry]:
        ...

    def result_exists(self, *, source_stem: str, file_id: str) -> bool:
        ...

    def load_audio(self, job: ExternalFileJob) -> tuple[np.ndarray, float]:
        ...

    def write_success_sidecars(
        self,
        job: ExternalFileJob,
        *,
        transcript: str,
        audio_seconds: float,
        backend: str,
        model_label: str,
        processing_seconds: float,
    ) -> tuple[str, str]:
        ...

    def write_error_sidecars(
        self,
        job: ExternalFileJob,
        *,
        error: Exception,
        audio_seconds: float | None,
        backend: str,
        model_label: str,
        processing_seconds: float,
    ) -> tuple[str, str]:
        ...


class LocalExternalStorage:
    scheme = "file"

    def __init__(self, *, inbox: Path, outbox: Path):
        self.inbox = inbox.expanduser()
        self.outbox = outbox.expanduser()

    def safe_description(self) -> str:
        return str(self.inbox)

    def ensure_ready(self) -> None:
        self.inbox.mkdir(parents=True, exist_ok=True)
        self.outbox.mkdir(parents=True, exist_ok=True)

    def list_files(self) -> list[ExternalFileEntry]:
        try:
            entries = list(self.inbox.iterdir())
        except FileNotFoundError:
            self.inbox.mkdir(parents=True, exist_ok=True)
            entries = []

        files: list[ExternalFileEntry] = []
        for path in entries:
            if not path.is_file() or path.name.startswith("."):
                continue
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            files.append(
                ExternalFileEntry(
                    location=str(path),
                    basename=path.name,
                    extension=path.suffix.lower(),
                    size_bytes=int(stat.st_size),
                    mtime_ns=int(stat.st_mtime_ns),
                )
            )
        return files

    def result_exists(self, *, source_stem: str, file_id: str) -> bool:
        text_path, json_path = local_result_paths(self.outbox, source_stem=source_stem, file_id=file_id)
        return text_path.exists() or json_path.exists()

    def load_audio(self, job: ExternalFileJob) -> tuple[np.ndarray, float]:
        return load_external_audio(Path(job.location))

    def write_success_sidecars(
        self,
        job: ExternalFileJob,
        *,
        transcript: str,
        audio_seconds: float,
        backend: str,
        model_label: str,
        processing_seconds: float,
    ) -> tuple[str, str]:
        payload = _base_payload(job, status="success", audio_seconds=audio_seconds, backend=backend, model_label=model_label)
        payload["processing_seconds"] = round(processing_seconds, 3)
        payload["transcript"] = transcript
        text_path, json_path = local_result_paths(self.outbox, source_stem=Path(job.basename).stem, file_id=job.file_id)
        _write_atomic_text(text_path, transcript)
        _write_atomic_json(json_path, payload)
        return str(text_path), str(json_path)

    def write_error_sidecars(
        self,
        job: ExternalFileJob,
        *,
        error: Exception,
        audio_seconds: float | None,
        backend: str,
        model_label: str,
        processing_seconds: float,
    ) -> tuple[str, str]:
        payload = _error_payload(
            job,
            error=error,
            audio_seconds=audio_seconds,
            backend=backend,
            model_label=model_label,
            processing_seconds=processing_seconds,
        )
        text_path, json_path = local_result_paths(self.outbox, source_stem=Path(job.basename).stem, file_id=job.file_id)
        _write_atomic_text(text_path, "")
        _write_atomic_json(json_path, payload)
        return str(text_path), str(json_path)


class SmbExternalStorage:
    scheme = "smb"

    def __init__(self, *, inbox: SmbLocation, outbox: SmbLocation, credentials: SmbCredentials, smbclient_module=None):
        self.inbox = inbox
        self.outbox = outbox
        self.credentials = credentials
        self._smbclient = smbclient_module
        self._ready = False

    def safe_description(self) -> str:
        return f"smb://{self.inbox.host}/{self.inbox.share}/..."

    def ensure_ready(self) -> None:
        if self._ready:
            return
        smbclient = self._client()
        username = (
            f"{self.credentials.domain}\\{self.credentials.username}"
            if self.credentials.domain
            else self.credentials.username
        )
        smbclient.register_session(
            self.inbox.host,
            username=username,
            password=self.credentials.password,
        )
        smbclient.makedirs(self.inbox.unc(), exist_ok=True)
        smbclient.makedirs(self.outbox.unc(), exist_ok=True)
        self._ready = True

    def list_files(self) -> list[ExternalFileEntry]:
        smbclient = self._client()
        smbclient_path = _smbclient_path(smbclient)
        try:
            names = smbclient.listdir(self.inbox.unc())
        except FileNotFoundError:
            smbclient.makedirs(self.inbox.unc(), exist_ok=True)
            names = []

        files: list[ExternalFileEntry] = []
        for name in names:
            if name.startswith("."):
                continue
            location = self.inbox.child(name)
            unc = location.unc()
            try:
                if not smbclient_path.isfile(unc):
                    continue
                stat = smbclient.stat(unc)
            except FileNotFoundError:
                continue
            files.append(
                ExternalFileEntry(
                    location=location.raw_url,
                    basename=name,
                    extension=Path(name).suffix.lower(),
                    size_bytes=int(stat.st_size),
                    mtime_ns=_mtime_ns(stat.st_mtime),
                )
            )
        return files

    def result_exists(self, *, source_stem: str, file_id: str) -> bool:
        smbclient_path = _smbclient_path(self._client())
        text_location, json_location = self._result_locations(source_stem=source_stem, file_id=file_id)
        return smbclient_path.exists(text_location.unc()) or smbclient_path.exists(json_location.unc())

    def load_audio(self, job: ExternalFileJob) -> tuple[np.ndarray, float]:
        smbclient = self._client()
        location = parse_smb_url(job.location)
        suffix = Path(job.basename).suffix or ".audio"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            with smbclient.open_file(location.unc(), mode="rb") as remote:
                while True:
                    chunk = remote.read(1024 * 1024)
                    if not chunk:
                        break
                    tmp.write(chunk)
            tmp.flush()
            return load_external_audio(Path(tmp.name))

    def write_success_sidecars(
        self,
        job: ExternalFileJob,
        *,
        transcript: str,
        audio_seconds: float,
        backend: str,
        model_label: str,
        processing_seconds: float,
    ) -> tuple[str, str]:
        payload = _base_payload(job, status="success", audio_seconds=audio_seconds, backend=backend, model_label=model_label)
        payload["processing_seconds"] = round(processing_seconds, 3)
        payload["transcript"] = transcript
        text_location, json_location = self._result_locations(source_stem=Path(job.basename).stem, file_id=job.file_id)
        self._write_atomic_text(text_location, transcript)
        self._write_atomic_json(json_location, payload)
        return text_location.raw_url, json_location.raw_url

    def write_error_sidecars(
        self,
        job: ExternalFileJob,
        *,
        error: Exception,
        audio_seconds: float | None,
        backend: str,
        model_label: str,
        processing_seconds: float,
    ) -> tuple[str, str]:
        payload = _error_payload(
            job,
            error=error,
            audio_seconds=audio_seconds,
            backend=backend,
            model_label=model_label,
            processing_seconds=processing_seconds,
        )
        text_location, json_location = self._result_locations(source_stem=Path(job.basename).stem, file_id=job.file_id)
        self._write_atomic_text(text_location, "")
        self._write_atomic_json(json_location, payload)
        return text_location.raw_url, json_location.raw_url

    def _client(self):
        if self._smbclient is None:
            try:
                import smbclient
            except ImportError as e:
                raise RuntimeError("SMB external intake requires the 'smbprotocol' package") from e
            self._smbclient = smbclient
        return self._smbclient

    def _result_locations(self, *, source_stem: str, file_id: str) -> tuple[SmbLocation, SmbLocation]:
        safe_stem = sanitize_stem(source_stem)
        base = f"{safe_stem}-{file_id}"
        return self.outbox.child(f"{base}.txt"), self.outbox.child(f"{base}.json")

    def _write_atomic_text(self, location: SmbLocation, text: str) -> None:
        data = text
        if data and not data.endswith("\n"):
            data += "\n"
        self._write_atomic_bytes(location, data.encode("utf-8"))

    def _write_atomic_json(self, location: SmbLocation, payload: dict) -> None:
        data = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        self._write_atomic_bytes(location, data)

    def _write_atomic_bytes(self, location: SmbLocation, data: bytes) -> None:
        smbclient = self._client()
        tmp_location = location.sibling(f".{location.basename}.{int(time.time() * 1000)}.tmp")
        smbclient.makedirs(location.parent.unc(), exist_ok=True)
        with smbclient.open_file(tmp_location.unc(), mode="wb") as remote:
            remote.write(data)
        smbclient.replace(tmp_location.unc(), location.unc())


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
        target_id: str = DEFAULT_EXTERNAL_TARGET_ID,
        telemetry=None,
    ):
        self.config = config
        self.external_queue = external_queue
        self.target_id = target_id
        self.telemetry = telemetry
        self._observed: dict[str, _ObservedFile] = {}
        self._queued_keys: set[tuple[str, int, int]] = set()

    def scan_once(self, *, now: float | None = None) -> list[ExternalFileJob]:
        now = time.monotonic() if now is None else now
        self.config.storage.ensure_ready()
        queued: list[ExternalFileJob] = []
        entries = self.config.storage.list_files()
        current_locations: set[str] = set()

        for entry in entries:
            current_locations.add(entry.location)
            if entry.extension not in self.config.extensions:
                continue
            key = (entry.basename, entry.size_bytes, entry.mtime_ns)
            file_id = external_file_id(entry.basename, entry.size_bytes, entry.mtime_ns)
            if self.config.storage.result_exists(source_stem=entry.stem, file_id=file_id):
                self._queued_keys.discard(key)
                self._observed.pop(entry.location, None)
                continue

            observed = self._observed.get(entry.location)
            if observed is None or observed.size_bytes != entry.size_bytes or observed.mtime_ns != entry.mtime_ns:
                observed = _ObservedFile(
                    size_bytes=entry.size_bytes,
                    mtime_ns=entry.mtime_ns,
                    changed_at=now,
                )
                self._observed[entry.location] = observed

            if not observed.seen_emitted:
                observed.seen_emitted = True
                if self.telemetry:
                    self.telemetry.emit(
                        "external.file_seen",
                        file_id=file_id,
                        storage_scheme=self.config.storage.scheme,
                        extension=entry.extension,
                        size_bytes=entry.size_bytes,
                    )

            if key in self._queued_keys:
                continue
            if now - observed.changed_at < self.config.stable_seconds:
                continue

            job = ExternalFileJob(
                location=entry.location,
                basename=entry.basename,
                extension=entry.extension,
                size_bytes=entry.size_bytes,
                mtime_ns=entry.mtime_ns,
                file_id=file_id,
                queued_at=time.time(),
                target_id=self.target_id,
            )
            self.external_queue.put(job)
            self._queued_keys.add(key)
            queued.append(job)
            if self.telemetry:
                self.telemetry.emit(
                    "external.file_queued",
                    file_id=file_id,
                    storage_scheme=self.config.storage.scheme,
                    extension=entry.extension,
                    size_bytes=job.size_bytes,
                    queue_depth=self.external_queue.pending_depth(),
                )

        for location in list(self._observed):
            if location not in current_locations:
                self._observed.pop(location, None)
        return queued


def watch_external_inbox(
    watcher: ExternalAudioWatcher,
    *,
    stop_event,
) -> None:
    if watcher.telemetry:
        watcher.telemetry.emit(
            "external.watcher_started",
            storage_scheme=watcher.config.storage.scheme,
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


def build_external_storage(
    *,
    inbox: str | Path,
    outbox: str | Path | None,
    smb_credentials: SmbCredentials | None,
    smbclient_module=None,
) -> ExternalStorage:
    inbox_value = str(inbox)
    if is_smb_url(inbox_value):
        inbox_location = parse_smb_url(inbox_value)
        outbox_location = parse_smb_url(str(outbox)) if outbox is not None else default_smb_outbox(inbox_location)
        if outbox_location.host != inbox_location.host or outbox_location.share != inbox_location.share:
            raise ExternalConfigError("SMB inbox and outbox must be on the same server and share")
        if smb_credentials is None:
            raise ExternalConfigError("SMB external intake requires WHISCODE_EXTERNAL_SMB_USERNAME and WHISCODE_EXTERNAL_SMB_PASSWORD")
        return SmbExternalStorage(
            inbox=inbox_location,
            outbox=outbox_location,
            credentials=smb_credentials,
            smbclient_module=smbclient_module,
        )

    inbox_path = Path(inbox_value).expanduser()
    outbox_path = Path(str(outbox)).expanduser() if outbox is not None else default_external_outbox(inbox_path)
    return LocalExternalStorage(inbox=inbox_path, outbox=outbox_path)


def discover_ccab_short_transcription_targets(
    root: str | Path,
    *,
    extensions: tuple[str, ...] = DEFAULT_EXTERNAL_EXTENSIONS,
    poll_seconds: float = DEFAULT_EXTERNAL_POLL_SECONDS,
    stable_seconds: float = DEFAULT_EXTERNAL_STABLE_SECONDS,
) -> list[ExternalTranscriptionTarget]:
    root_path = Path(str(root)).expanduser()
    if not root_path.exists():
        raise ExternalConfigError(f"CCAB external root does not exist: {root_path}")
    if not root_path.is_dir():
        raise ExternalConfigError(f"CCAB external root is not a directory: {root_path}")

    targets: list[ExternalTranscriptionTarget] = []
    for user_root in sorted((path for path in root_path.iterdir() if path.is_dir()), key=lambda path: path.name):
        if user_root.name.startswith("."):
            continue
        workspace = user_root / "workspace"
        if not workspace.is_dir():
            continue
        short_root = workspace / "transcription" / "short"
        targets.append(
            ExternalTranscriptionTarget(
                target_id=f"ccab-short-{len(targets) + 1}",
                config=ExternalTranscriptionConfig(
                    storage=LocalExternalStorage(
                        inbox=short_root / "inbox",
                        outbox=short_root / "outbox",
                    ),
                    extensions=extensions,
                    poll_seconds=poll_seconds,
                    stable_seconds=stable_seconds,
                ),
            )
        )

    if not targets:
        raise ExternalConfigError(f"CCAB external root contains no user workspace directories: {root_path}")
    return targets


def is_smb_url(value: str) -> bool:
    return urlparse(value).scheme.lower() == "smb"


def parse_smb_url(value: str) -> SmbLocation:
    parsed = urlparse(value)
    if parsed.scheme.lower() != "smb":
        raise ExternalConfigError(f"expected smb:// URL, got: {value}")
    if parsed.username or parsed.password:
        raise ExternalConfigError("SMB credentials must be provided with environment variables, not embedded in the URL")
    if not parsed.hostname:
        raise ExternalConfigError("SMB URL must include a host")
    raw_parts = [unquote(part) for part in parsed.path.split("/") if part]
    if not raw_parts:
        raise ExternalConfigError("SMB URL must include a share name")
    share, *parts = raw_parts
    return SmbLocation(
        raw_url=_smb_url(parsed.hostname, share, tuple(parts)),
        host=parsed.hostname,
        share=share,
        parts=tuple(parts),
    )


def default_smb_outbox(inbox: SmbLocation) -> SmbLocation:
    return inbox.sibling("outbox")


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
    audio_loader=None,
) -> ExternalJobResult:
    started = time.monotonic()
    audio_seconds = None
    try:
        audio, audio_seconds = audio_loader(job.location) if audio_loader is not None else config.storage.load_audio(job)
        transcript = transcribe_audio(audio)
        text_location, json_location = config.storage.write_success_sidecars(
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
            text_location=text_location,
            json_location=json_location,
            error_type=None,
        )
    except Exception as e:
        text_location, json_location = config.storage.write_error_sidecars(
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
            text_location=text_location,
            json_location=json_location,
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
    text_path, json_path = local_result_paths(outbox, source_stem=Path(job.basename).stem, file_id=job.file_id)
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
    payload = _error_payload(
        job,
        error=error,
        audio_seconds=audio_seconds,
        backend=backend,
        model_label=model_label,
        processing_seconds=processing_seconds,
    )
    text_path, json_path = local_result_paths(outbox, source_stem=Path(job.basename).stem, file_id=job.file_id)
    _write_atomic_text(text_path, "")
    _write_atomic_json(json_path, payload)
    return text_path, json_path


def result_exists(outbox: Path, *, source_stem: str, file_id: str) -> bool:
    text_path, json_path = local_result_paths(outbox, source_stem=source_stem, file_id=file_id)
    return text_path.exists() or json_path.exists()


def result_paths(outbox: Path, *, source_stem: str, file_id: str) -> tuple[Path, Path]:
    return local_result_paths(outbox, source_stem=source_stem, file_id=file_id)


def local_result_paths(outbox: Path, *, source_stem: str, file_id: str) -> tuple[Path, Path]:
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


def _error_payload(
    job: ExternalFileJob,
    *,
    error: Exception,
    audio_seconds: float | None,
    backend: str,
    model_label: str,
    processing_seconds: float,
) -> dict:
    payload = _base_payload(job, status="failed", audio_seconds=audio_seconds, backend=backend, model_label=model_label)
    payload["processing_seconds"] = round(processing_seconds, 3)
    payload["error"] = {
        "type": type(error).__name__,
        "message": str(error)[:_MAX_ERROR_MESSAGE_CHARS],
    }
    return payload


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


def _smb_url(host: str, share: str, parts: tuple[str, ...]) -> str:
    suffix = "/".join(parts)
    return f"smb://{host}/{share}/{suffix}" if suffix else f"smb://{host}/{share}"


def _mtime_ns(mtime: float) -> int:
    return int(float(mtime) * 1_000_000_000)


def _smbclient_path(smbclient_module):
    path_module = getattr(smbclient_module, "path", None)
    if path_module is None:
        try:
            import smbclient.path as path_module
        except ImportError as e:
            raise RuntimeError("SMB external intake requires smbclient.path from 'smbprotocol'") from e
    return path_module
