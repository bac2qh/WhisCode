import io
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from whiscode.crispasr_asr import (
    CrispAsrBackend,
    CrispAsrError,
    CrispAsrServerConfig,
    HealthResult,
    audio_to_wav_bytes,
    build_crispasr_prompt,
    build_multipart_form,
    default_crispasr_bin,
    default_crispasr_model_path,
    extract_crispasr_text,
)


class FakeTelemetry:
    def __init__(self):
        self.events = []

    def emit(self, event, **properties):
        self.events.append((event, properties))


def make_config(tmp_path: Path, *, autostart: bool = True) -> CrispAsrServerConfig:
    server = tmp_path / "crispasr"
    model = tmp_path / "vibevoice-asr-f16.gguf"
    server.write_text("#!/bin/sh\n")
    server.chmod(0o755)
    model.write_text("model")
    return CrispAsrServerConfig(
        server_bin=server,
        model=model,
        backend="vibevoice",
        host="127.0.0.1",
        port=8092,
        startup_timeout_seconds=0.5,
        autostart=autostart,
    )


def test_default_paths_honor_env(monkeypatch):
    monkeypatch.setenv("WHISCODE_CRISPASR_BIN", "~/bin/crispasr")
    monkeypatch.setenv("WHISCODE_CRISPASR_MODEL", "~/models/vibevoice.gguf")

    assert default_crispasr_bin() == Path.home() / "bin/crispasr"
    assert default_crispasr_model_path() == Path.home() / "models/vibevoice.gguf"


def test_audio_to_wav_bytes_writes_16khz_mono_int16():
    data = audio_to_wav_bytes(np.array([-2.0, 0.0, 2.0], dtype=np.float32))

    with wave.open(io.BytesIO(data), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 16000
        assert wav.getsampwidth() == 2
        assert wav.getnframes() == 3


def test_build_crispasr_prompt_includes_code_prompt_extra_prompt_and_hotwords():
    prompt = build_crispasr_prompt(
        extra_prompt="Prefer repository jargon.",
        hotwords=["repo", "pytest"],
    )

    assert "Programming terms:" in prompt
    assert "uv" in prompt
    assert "Prefer repository jargon." in prompt
    assert "Hotwords: repo, pytest" in prompt


def test_build_multipart_form_includes_fields_and_audio_file():
    body, content_type = build_multipart_form(
        fields={"response_format": "json", "prompt": "repo"},
        file_field="file",
        filename="audio.wav",
        file_bytes=b"RIFFdata",
        boundary="boundary",
    )

    assert content_type == "multipart/form-data; boundary=boundary"
    assert b'name="response_format"' in body
    assert b"json" in body
    assert b'name="prompt"' in body
    assert b"repo" in body
    assert b'name="file"; filename="audio.wav"' in body
    assert b"Content-Type: audio/wav" in body
    assert b"RIFFdata" in body


def test_extract_crispasr_text_reads_text_field():
    assert extract_crispasr_text({"text": " hello "}) == "hello"


def test_extract_crispasr_text_rejects_missing_text():
    with pytest.raises(CrispAsrError, match="include text"):
        extract_crispasr_text({"segments": []})


def test_start_reuses_existing_server(tmp_path):
    telemetry = FakeTelemetry()
    backend = CrispAsrBackend(make_config(tmp_path), telemetry=telemetry)
    backend.health_check = lambda timeout: HealthResult(ok=True, status_class=200, latency_ms=2.0)

    backend.start()

    assert backend._process is None
    assert (
        "crispasr.server_health",
        {
            "outcome": "reachable",
            "status_class": 200,
            "latency_ms": 2.0,
            "port": 8092,
            "backend": "vibevoice",
        },
    ) in telemetry.events


def test_start_requires_server_when_autostart_disabled(tmp_path):
    backend = CrispAsrBackend(make_config(tmp_path, autostart=False), telemetry=FakeTelemetry())
    backend.health_check = lambda timeout: HealthResult(
        ok=False,
        status_class=None,
        latency_ms=1.0,
        error_type="ConnectionRefusedError",
    )

    with pytest.raises(CrispAsrError, match="not reachable"):
        backend.start()


def test_start_autostarts_and_close_terminates_owned_process(tmp_path):
    telemetry = FakeTelemetry()
    backend = CrispAsrBackend(make_config(tmp_path), telemetry=telemetry)
    health_results = [
        HealthResult(ok=False, status_class=None, latency_ms=1.0, error_type="ConnectionRefusedError"),
        HealthResult(ok=True, status_class=200, latency_ms=1.5),
    ]
    backend.health_check = lambda timeout: health_results.pop(0)

    class FakeProcess:
        pid = 1234
        terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

    fake_process = FakeProcess()
    with patch("subprocess.Popen", return_value=fake_process) as popen:
        backend.start()

    assert popen.call_args.args[0] == [
        str(backend.config.server_bin),
        "--server",
        "--backend",
        "vibevoice",
        "-m",
        str(backend.config.model),
        "--host",
        "127.0.0.1",
        "--port",
        "8092",
    ]
    assert backend.owns_process is True
    assert "crispasr.server_started" in [event for event, properties in telemetry.events]

    backend.close()
    assert fake_process.terminated is True


def test_close_does_not_terminate_external_process(tmp_path):
    backend = CrispAsrBackend(make_config(tmp_path), telemetry=FakeTelemetry())

    class FakeProcess:
        terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

    fake_process = FakeProcess()
    backend._process = fake_process
    backend._owns_process = False

    backend.close()

    assert fake_process.terminated is False


def test_transcribe_posts_multipart_audio_and_parses_response(tmp_path):
    telemetry = FakeTelemetry()
    backend = CrispAsrBackend(make_config(tmp_path), telemetry=telemetry)
    requests = []

    def post_multipart(path, *, fields, file_field, filename, file_bytes, timeout):
        requests.append((path, fields, file_field, filename, file_bytes, timeout))
        return {"text": "open the repo"}

    backend._post_multipart = post_multipart

    text = backend.transcribe(
        np.zeros(16000, dtype=np.float32),
        language="en",
        extra_prompt="Prefer coding jargon.",
        hotwords=["repo"],
    )

    assert text == "open the repo"
    path, fields, file_field, filename, file_bytes, timeout = requests[0]
    assert path == "/v1/audio/transcriptions"
    assert fields["response_format"] == "json"
    assert fields["language"] == "en"
    assert fields["temperature"] == "0.0"
    assert fields["max_tokens"] == "2048"
    assert "Programming terms:" in fields["prompt"]
    assert "Prefer coding jargon." in fields["prompt"]
    assert "Hotwords: repo" in fields["prompt"]
    assert file_field == "file"
    assert filename == "audio.wav"
    assert file_bytes.startswith(b"RIFF")
    assert timeout == backend.config.request_timeout_seconds
    assert [event for event, properties in telemetry.events] == [
        "crispasr.transcription_started",
        "crispasr.transcription_completed",
    ]


def test_transcribe_omits_auto_language(tmp_path):
    backend = CrispAsrBackend(make_config(tmp_path), telemetry=FakeTelemetry())
    requests = []

    def post_multipart(path, *, fields, file_field, filename, file_bytes, timeout):
        requests.append(fields)
        return {"text": ""}

    backend._post_multipart = post_multipart

    backend.transcribe(np.zeros(8, dtype=np.float32), language="auto")

    assert "language" not in requests[0]
