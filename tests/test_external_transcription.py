import json
import io
import sys
import types
from pathlib import Path

import numpy as np
import pytest

from whiscode.external_transcription import (
    DEFAULT_EXTERNAL_EXTENSIONS,
    ExternalAudioWatcher,
    ExternalConfigError,
    ExternalFileJob,
    ExternalFileQueue,
    ExternalTranscriptionConfig,
    LocalExternalStorage,
    SmbCredentials,
    SmbExternalStorage,
    build_external_storage,
    default_external_outbox,
    default_smb_outbox,
    external_file_id,
    load_external_audio,
    normalize_audio,
    parse_external_extensions,
    parse_smb_url,
    process_external_transcription_job,
    result_paths,
)


class FakeTelemetry:
    def __init__(self):
        self.events = []

    def emit(self, event, **properties):
        self.events.append((event, properties))


def make_job(path: Path) -> ExternalFileJob:
    stat = path.stat()
    return ExternalFileJob(
        location=str(path),
        basename=path.name,
        extension=path.suffix.lower(),
        size_bytes=stat.st_size,
        mtime_ns=stat.st_mtime_ns,
        file_id=external_file_id(path.name, stat.st_size, stat.st_mtime_ns),
        queued_at=1.0,
    )


def test_parse_external_extensions_normalizes_and_deduplicates():
    assert parse_external_extensions("wav,.OGG, m4a, wav") == (".wav", ".ogg", ".m4a")
    assert parse_external_extensions("") == DEFAULT_EXTERNAL_EXTENSIONS


def test_parse_smb_url_and_unc_conversion():
    location = parse_smb_url("smb://192.168.4.21/NAS_1/whiscode/inbox")

    assert location.host == "192.168.4.21"
    assert location.share == "NAS_1"
    assert location.parts == ("whiscode", "inbox")
    assert location.unc() == r"\\192.168.4.21\NAS_1\whiscode\inbox"
    assert location.raw_url == "smb://192.168.4.21/NAS_1/whiscode/inbox"
    assert default_smb_outbox(location).raw_url == "smb://192.168.4.21/NAS_1/whiscode/outbox"


def test_parse_smb_url_rejects_credentials_and_missing_share():
    with pytest.raises(ExternalConfigError, match="environment variables"):
        parse_smb_url("smb://user:pass@nas/share/inbox")
    with pytest.raises(ExternalConfigError, match="share"):
        parse_smb_url("smb://nas")


def test_default_external_outbox_is_sibling_outbox():
    assert default_external_outbox(Path("~/nas/inbox")).name == "outbox"
    assert default_external_outbox(Path("~/nas/inbox")).parent == Path.home() / "nas"


def test_build_external_storage_uses_local_paths_and_smb_credentials(tmp_path):
    local = build_external_storage(inbox=tmp_path / "inbox", outbox=None, smb_credentials=None)
    assert isinstance(local, LocalExternalStorage)
    assert local.outbox == tmp_path / "outbox"

    smb = build_external_storage(
        inbox="smb://192.168.4.21/NAS_1/whiscode/inbox",
        outbox=None,
        smb_credentials=SmbCredentials(username="u", password="p"),
    )
    assert isinstance(smb, SmbExternalStorage)
    assert smb.outbox.raw_url == "smb://192.168.4.21/NAS_1/whiscode/outbox"


def test_build_external_storage_requires_smb_credentials():
    with pytest.raises(ExternalConfigError, match="WHISCODE_EXTERNAL_SMB_USERNAME"):
        build_external_storage(inbox="smb://192.168.4.21/NAS_1/whiscode/inbox", outbox=None, smb_credentials=None)


def test_watcher_waits_for_stability_filters_and_queues(tmp_path):
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    (inbox / ".hidden.wav").write_text("hidden")
    (inbox / "note.txt").write_text("unsupported")
    audio = inbox / "voice.ogg"
    audio.write_text("audio")
    external_queue = ExternalFileQueue()
    telemetry = FakeTelemetry()
    watcher = ExternalAudioWatcher(
        ExternalTranscriptionConfig(storage=LocalExternalStorage(inbox=inbox, outbox=outbox), extensions=(".ogg",), stable_seconds=5.0),
        external_queue,
        telemetry=telemetry,
    )

    assert watcher.scan_once(now=10.0) == []
    assert external_queue.pending_depth() == 0

    queued = watcher.scan_once(now=16.0)

    assert len(queued) == 1
    assert queued[0].basename == "voice.ogg"
    assert external_queue.pending_depth() == 1
    assert [event for event, _ in telemetry.events] == ["external.file_seen", "external.file_queued"]
    assert telemetry.events[0][1]["storage_scheme"] == "file"


def test_watcher_skips_file_when_matching_result_exists(tmp_path):
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    outbox.mkdir()
    audio = inbox / "voice.wav"
    audio.write_text("audio")
    stat = audio.stat()
    file_id = external_file_id(audio.name, stat.st_size, stat.st_mtime_ns)
    text_path, _ = result_paths(outbox, source_stem=audio.stem, file_id=file_id)
    text_path.write_text("done")
    external_queue = ExternalFileQueue()
    watcher = ExternalAudioWatcher(
        ExternalTranscriptionConfig(storage=LocalExternalStorage(inbox=inbox, outbox=outbox), extensions=(".wav",), stable_seconds=0.0),
        external_queue,
    )

    assert watcher.scan_once(now=1.0) == []
    assert external_queue.pending_depth() == 0


def test_normalize_audio_converts_stereo_and_resamples():
    stereo = np.column_stack([np.linspace(0, 1, 8000), np.linspace(1, 0, 8000)]).astype(np.float32)

    audio = normalize_audio(stereo, 8000)

    assert audio.dtype == np.float32
    assert audio.shape == (16000,)
    assert np.allclose(audio, 0.5, atol=0.01)


def test_load_external_audio_uses_mlx_audio_io_read(monkeypatch, tmp_path):
    audio_path = tmp_path / "telegram.ogg"
    audio_path.write_text("not real audio")
    fake_audio_io = types.ModuleType("mlx_audio.audio_io")
    fake_audio_io.read = lambda path: (np.array([[0.0, 0.5], [1.0, -0.5]], dtype=np.float32), 16000)
    fake_mlx_audio = types.ModuleType("mlx_audio")
    monkeypatch.setitem(sys.modules, "mlx_audio", fake_mlx_audio)
    monkeypatch.setitem(sys.modules, "mlx_audio.audio_io", fake_audio_io)

    audio, seconds = load_external_audio(audio_path)

    assert audio.tolist() == [0.25, 0.25]
    assert seconds == 2 / 16000


def test_external_job_writes_success_sidecars_without_postprocessing(tmp_path):
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    source = inbox / "voice.m4a"
    source.write_text("audio")
    job = make_job(source)
    config = ExternalTranscriptionConfig(storage=LocalExternalStorage(inbox=inbox, outbox=outbox))
    calls = []

    result = process_external_transcription_job(
        config,
        job,
        transcribe_audio=lambda audio: calls.append(audio.copy()) or "raw lower transcript",
        backend="mlx-vibevoice",
        model_label="VibeVoice-ASR-8bit",
        audio_loader=lambda path: (np.array([0.1, 0.2], dtype=np.float32), 0.25),
    )

    assert result.status == "success"
    assert np.allclose(calls[0], [0.1, 0.2])
    assert Path(result.text_location).read_text() == "raw lower transcript\n"
    payload = json.loads(Path(result.json_location).read_text())
    assert payload["status"] == "success"
    assert payload["source_basename"] == "voice.m4a"
    assert payload["backend"] == "mlx-vibevoice"
    assert payload["model_label"] == "VibeVoice-ASR-8bit"
    assert payload["transcript"] == "raw lower transcript"


def test_external_job_writes_error_sidecars(tmp_path):
    inbox = tmp_path / "inbox"
    outbox = tmp_path / "outbox"
    inbox.mkdir()
    source = inbox / "voice.wav"
    source.write_text("audio")
    job = make_job(source)
    config = ExternalTranscriptionConfig(storage=LocalExternalStorage(inbox=inbox, outbox=outbox))

    result = process_external_transcription_job(
        config,
        job,
        transcribe_audio=lambda audio: (_ for _ in ()).throw(RuntimeError("boom")),
        backend="mlx-vibevoice",
        model_label="VibeVoice-ASR-8bit",
        audio_loader=lambda path: (np.array([0.1], dtype=np.float32), 0.1),
    )

    assert result.status == "failed"
    assert result.error_type == "RuntimeError"
    assert Path(result.text_location).read_text() == ""
    payload = json.loads(Path(result.json_location).read_text())
    assert payload["status"] == "failed"
    assert payload["error"]["type"] == "RuntimeError"
    assert payload["audio_seconds"] == 0.1


class FakeSmbPath:
    def __init__(self, client):
        self.client = client

    def isfile(self, unc):
        return unc in self.client.files

    def exists(self, unc):
        return unc in self.client.files


class FakeSmbFile:
    def __init__(self, client, path, mode):
        self.client = client
        self.path = path
        self.mode = mode
        self.buffer = io.BytesIO(client.files.get(path, b"") if "r" in mode else b"")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if "w" in self.mode or "a" in self.mode:
            self.client.files[self.path] = self.buffer.getvalue()
        return False

    def read(self, size=-1):
        return self.buffer.read(size)

    def write(self, data):
        return self.buffer.write(data)


class FakeStat:
    def __init__(self, size, mtime):
        self.st_size = size
        self.st_mtime = mtime


class FakeSmbClient:
    def __init__(self):
        self.path = FakeSmbPath(self)
        self.files = {
            r"\\192.168.4.21\NAS_1\whiscode\inbox\voice.ogg": b"audio",
        }
        self.sessions = []
        self.makedirs_calls = []
        self.replace_calls = []

    def register_session(self, host, **kwargs):
        self.sessions.append((host, kwargs))

    def makedirs(self, unc, exist_ok=False):
        self.makedirs_calls.append((unc, exist_ok))

    def listdir(self, unc):
        assert unc == r"\\192.168.4.21\NAS_1\whiscode\inbox"
        return ["voice.ogg", ".hidden.wav", "folder"]

    def stat(self, unc):
        return FakeStat(size=len(self.files[unc]), mtime=123.456)

    def open_file(self, unc, mode="r", **kwargs):
        return FakeSmbFile(self, unc, mode)

    def replace(self, src, dst):
        self.replace_calls.append((src, dst))
        self.files[dst] = self.files.pop(src)


def test_smb_storage_lists_registers_and_writes_sidecars():
    fake = FakeSmbClient()
    storage = SmbExternalStorage(
        inbox=parse_smb_url("smb://192.168.4.21/NAS_1/whiscode/inbox"),
        outbox=parse_smb_url("smb://192.168.4.21/NAS_1/whiscode/outbox"),
        credentials=SmbCredentials(username="user", password="pass", domain="WORKGROUP"),
        smbclient_module=fake,
    )

    storage.ensure_ready()
    storage.ensure_ready()
    entries = storage.list_files()

    assert fake.sessions == [("192.168.4.21", {"username": r"WORKGROUP\user", "password": "pass"})]
    assert [entry.basename for entry in entries] == ["voice.ogg"]
    assert entries[0].location == "smb://192.168.4.21/NAS_1/whiscode/inbox/voice.ogg"
    assert entries[0].mtime_ns == 123456000000

    job = ExternalFileJob(
        location=entries[0].location,
        basename=entries[0].basename,
        extension=entries[0].extension,
        size_bytes=entries[0].size_bytes,
        mtime_ns=entries[0].mtime_ns,
        file_id=external_file_id(entries[0].basename, entries[0].size_bytes, entries[0].mtime_ns),
        queued_at=1.0,
    )
    text_location, json_location = storage.write_success_sidecars(
        job,
        transcript="hello",
        audio_seconds=0.5,
        backend="mlx-vibevoice",
        model_label="VibeVoice-ASR-8bit",
        processing_seconds=1.25,
    )

    assert text_location.startswith("smb://192.168.4.21/NAS_1/whiscode/outbox/voice-")
    assert json_location.endswith(".json")
    assert len(fake.replace_calls) == 2
    text_unc = parse_smb_url(text_location).unc()
    json_unc = parse_smb_url(json_location).unc()
    assert fake.files[text_unc] == b"hello\n"
    assert json.loads(fake.files[json_unc].decode("utf-8"))["status"] == "success"


def test_smb_storage_loads_remote_audio_through_temp_file(monkeypatch):
    fake = FakeSmbClient()
    storage = SmbExternalStorage(
        inbox=parse_smb_url("smb://192.168.4.21/NAS_1/whiscode/inbox"),
        outbox=parse_smb_url("smb://192.168.4.21/NAS_1/whiscode/outbox"),
        credentials=SmbCredentials(username="user", password="pass"),
        smbclient_module=fake,
    )
    seen = {}

    def fake_read(path):
        seen["suffix"] = Path(path).suffix
        assert Path(path).read_bytes() == b"audio"
        return np.array([0.1, 0.2], dtype=np.float32), 16000

    fake_audio_io = types.ModuleType("mlx_audio.audio_io")
    fake_audio_io.read = fake_read
    fake_mlx_audio = types.ModuleType("mlx_audio")
    monkeypatch.setitem(sys.modules, "mlx_audio", fake_mlx_audio)
    monkeypatch.setitem(sys.modules, "mlx_audio.audio_io", fake_audio_io)

    audio, seconds = storage.load_audio(
        ExternalFileJob(
            location="smb://192.168.4.21/NAS_1/whiscode/inbox/voice.ogg",
            basename="voice.ogg",
            extension=".ogg",
            size_bytes=5,
            mtime_ns=1,
            file_id="abc",
            queued_at=1.0,
        )
    )

    assert seen["suffix"] == ".ogg"
    assert np.allclose(audio, [0.1, 0.2])
    assert seconds == 2 / 16000
