import json
import sys
import types
from pathlib import Path

import numpy as np

from whiscode.external_transcription import (
    DEFAULT_EXTERNAL_EXTENSIONS,
    ExternalAudioWatcher,
    ExternalFileJob,
    ExternalFileQueue,
    ExternalTranscriptionConfig,
    default_external_outbox,
    external_file_id,
    load_external_audio,
    normalize_audio,
    parse_external_extensions,
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
        path=path,
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


def test_default_external_outbox_is_sibling_outbox():
    assert default_external_outbox(Path("~/nas/inbox")).name == "outbox"
    assert default_external_outbox(Path("~/nas/inbox")).parent == Path.home() / "nas"


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
        ExternalTranscriptionConfig(inbox=inbox, outbox=outbox, extensions=(".ogg",), stable_seconds=5.0),
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
        ExternalTranscriptionConfig(inbox=inbox, outbox=outbox, extensions=(".wav",), stable_seconds=0.0),
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
    config = ExternalTranscriptionConfig(inbox=inbox, outbox=outbox)
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
    assert result.text_path.read_text() == "raw lower transcript\n"
    payload = json.loads(result.json_path.read_text())
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
    config = ExternalTranscriptionConfig(inbox=inbox, outbox=outbox)

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
    assert result.text_path.read_text() == ""
    payload = json.loads(result.json_path.read_text())
    assert payload["status"] == "failed"
    assert payload["error"]["type"] == "RuntimeError"
    assert payload["audio_seconds"] == 0.1
