import io
import wave
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from whiscode.llama_cpp_asr import (
    HealthResult,
    LlamaCppAsrBackend,
    LlamaCppAsrError,
    LlamaCppServerConfig,
    audio_to_wav_bytes,
    build_chat_payload,
    extract_chat_content,
    parse_qwen_asr_output,
    qwen_language_for_whiscode,
)


class FakeTelemetry:
    def __init__(self):
        self.events = []

    def emit(self, event, **properties):
        self.events.append((event, properties))


def make_config(tmp_path: Path, *, autostart: bool = True) -> LlamaCppServerConfig:
    server = tmp_path / "llama-server"
    model = tmp_path / "model.gguf"
    mmproj = tmp_path / "mmproj.gguf"
    server.write_text("#!/bin/sh\n")
    server.chmod(0o755)
    model.write_text("model")
    mmproj.write_text("mmproj")
    return LlamaCppServerConfig(
        server_bin=server,
        model=model,
        mmproj=mmproj,
        host="127.0.0.1",
        port=8091,
        startup_timeout_seconds=0.5,
        autostart=autostart,
    )


def test_audio_to_wav_bytes_writes_16khz_mono_int16():
    data = audio_to_wav_bytes(np.array([-2.0, 0.0, 2.0], dtype=np.float32))

    with wave.open(io.BytesIO(data), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 16000
        assert wav.getsampwidth() == 2
        assert wav.getnframes() == 3


def test_build_chat_payload_uses_base64_input_audio_and_forced_language():
    payload = build_chat_payload(
        np.zeros(8, dtype=np.float32),
        model="whiscode-qwen3-asr",
        forced_language="Chinese",
        extra_prompt="Project terms",
        hotwords=["WhisCode", "Qwen"],
    )

    assert payload["model"] == "whiscode-qwen3-asr"
    assert payload["generation_prompt"] == "language Chinese<asr_text>"
    assert payload["messages"][0] == {
        "role": "system",
        "content": "Project terms Hotwords: WhisCode, Qwen",
    }
    audio_part = payload["messages"][1]["content"][0]
    assert audio_part["type"] == "input_audio"
    assert audio_part["input_audio"]["format"] == "wav"
    assert isinstance(audio_part["input_audio"]["data"], str)


@pytest.mark.parametrize(
    ("raw", "forced_language", "expected"),
    [
        ("language Chinese<asr_text>你好，世界。", None, "你好，世界。"),
        ("language None<asr_text>", None, ""),
        ("plain transcript", None, "plain transcript"),
        ("language Chinese 你好", "Chinese", "你好"),
    ],
)
def test_parse_qwen_asr_output(raw, forced_language, expected):
    assert parse_qwen_asr_output(raw, forced_language=forced_language) == expected


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("auto", None),
        ("zh", "Chinese"),
        ("en", "English"),
        ("yue", "Cantonese"),
        ("Japanese", "Japanese"),
    ],
)
def test_qwen_language_for_whiscode(language, expected):
    assert qwen_language_for_whiscode(language) == expected


def test_extract_chat_content_reads_openai_shape():
    response = {"choices": [{"message": {"content": "language English<asr_text>Hello"}}]}

    assert extract_chat_content(response) == "language English<asr_text>Hello"


def test_extract_chat_content_rejects_missing_content():
    with pytest.raises(LlamaCppAsrError, match="chat content"):
        extract_chat_content({"choices": []})


def test_start_reuses_existing_server(tmp_path):
    telemetry = FakeTelemetry()
    backend = LlamaCppAsrBackend(make_config(tmp_path), telemetry=telemetry)
    backend.health_check = lambda timeout: HealthResult(ok=True, status_class=200, latency_ms=2.0)

    backend.start()

    assert backend._process is None
    assert (
        "llama.server_health",
        {"outcome": "reachable", "status_class": 200, "latency_ms": 2.0, "port": 8091},
    ) in telemetry.events


def test_start_requires_server_when_autostart_disabled(tmp_path):
    backend = LlamaCppAsrBackend(make_config(tmp_path, autostart=False), telemetry=FakeTelemetry())
    backend.health_check = lambda timeout: HealthResult(
        ok=False,
        status_class=None,
        latency_ms=1.0,
        error_type="ConnectionRefusedError",
    )

    with pytest.raises(LlamaCppAsrError, match="not reachable"):
        backend.start()


def test_start_autostarts_and_close_terminates_owned_process(tmp_path):
    telemetry = FakeTelemetry()
    backend = LlamaCppAsrBackend(make_config(tmp_path), telemetry=telemetry)
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

    assert popen.called
    assert backend._process is fake_process
    assert "llama.server_started" in [event for event, properties in telemetry.events]

    backend.close()
    assert fake_process.terminated is True


def test_close_does_not_terminate_external_process(tmp_path):
    backend = LlamaCppAsrBackend(make_config(tmp_path), telemetry=FakeTelemetry())

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


def test_transcribe_posts_audio_and_parses_response(tmp_path):
    telemetry = FakeTelemetry()
    backend = LlamaCppAsrBackend(make_config(tmp_path), telemetry=telemetry)
    requests = []

    def post_json(path, payload, timeout):
        requests.append((path, payload, timeout))
        return {"choices": [{"message": {"content": "language Chinese<asr_text>你好，世界。"}}]}

    backend._post_json = post_json

    text = backend.transcribe(
        np.zeros(16000, dtype=np.float32),
        language="auto",
        extra_prompt="Context",
        hotwords=["WhisCode"],
    )

    assert text == "你好，世界。"
    path, payload, timeout = requests[0]
    assert path == "/v1/chat/completions"
    assert payload["messages"][0]["content"] == "Context Hotwords: WhisCode"
    assert timeout == backend.config.request_timeout_seconds
    assert [event for event, properties in telemetry.events] == [
        "llama.transcription_started",
        "llama.transcription_completed",
    ]
