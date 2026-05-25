from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from whiscode.mlx_vibevoice_asr import (
    DEFAULT_MLX_VIBEVOICE_MODEL,
    MlxVibeVoiceBackend,
    MlxVibeVoiceConfig,
    MlxVibeVoiceError,
    build_mlx_vibevoice_context,
    default_mlx_vibevoice_model,
    extract_mlx_vibevoice_text,
)


class FakeTelemetry:
    def __init__(self):
        self.events = []

    def emit(self, event, **properties):
        self.events.append((event, properties))


class FakeModel:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def generate(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result


def test_default_mlx_vibevoice_model_uses_downloaded_8bit_path(monkeypatch):
    monkeypatch.delenv("WHISCODE_MLX_VIBEVOICE_MODEL", raising=False)

    assert default_mlx_vibevoice_model() == str(DEFAULT_MLX_VIBEVOICE_MODEL)


def test_default_mlx_vibevoice_model_honors_env_path(monkeypatch):
    monkeypatch.setenv("WHISCODE_MLX_VIBEVOICE_MODEL", "~/models/VibeVoice-ASR-bf16")

    assert default_mlx_vibevoice_model() == str(Path.home() / "models/VibeVoice-ASR-bf16")


def test_default_mlx_vibevoice_model_allows_hugging_face_repo(monkeypatch):
    monkeypatch.setenv("WHISCODE_MLX_VIBEVOICE_MODEL", "mlx-community/VibeVoice-ASR-bf16")

    assert default_mlx_vibevoice_model() == "mlx-community/VibeVoice-ASR-bf16"


def test_build_context_puts_hotwords_first_and_keeps_mixed_language():
    context = build_mlx_vibevoice_context(
        extra_prompt="Prefer repo jargon.",
        hotwords=["LLM", "打开 repo", "pytest"],
    )

    assert context.startswith("Hotwords: LLM, 打开 repo, pytest")
    assert "Prefer repo jargon." in context
    assert "Technical dictation" in context


def test_build_context_filters_empty_hotwords():
    context = build_mlx_vibevoice_context(extra_prompt=None, hotwords=["", "  ", "MLX"])

    assert "Hotwords: MLX" in context
    assert "Technical dictation" in context


def test_extract_text_joins_mlx_segments():
    result = SimpleNamespace(
        text='[{"Content":"fallback"}]',
        segments=[
            {"start_time": 0.0, "end_time": 0.5, "speaker_id": 0, "text": "open repo"},
            {"start_time": 0.5, "end_time": 0.9, "speaker_id": 0, "text": "run pytest"},
        ],
    )

    assert extract_mlx_vibevoice_text(result) == "open repo run pytest"


def test_extract_text_falls_back_to_raw_vibevoice_chunks():
    result = SimpleNamespace(
        text='assistant\n[{"Start":0,"End":1,"Speaker":0,"Content":"打开 repo"}]',
        segments=[],
    )

    assert extract_mlx_vibevoice_text(result) == "打开 repo"


def test_extract_text_rejects_malformed_raw_chunks():
    result = SimpleNamespace(text='[{"Content":]', segments=[])

    with pytest.raises(MlxVibeVoiceError, match="chunks"):
        extract_mlx_vibevoice_text(result)


def test_backend_loads_model_and_transcribes_with_context():
    fake_model = FakeModel(
        SimpleNamespace(
            text="",
            segments=[
                {"text": "hello LLM"},
            ],
        )
    )
    telemetry = FakeTelemetry()
    backend = MlxVibeVoiceBackend(
        MlxVibeVoiceConfig(
            model="~/Documents/models/mlx-community/VibeVoice-ASR-8bit",
            max_tokens=123,
            temperature=0.2,
            prefill_step_size=456,
        ),
        telemetry=telemetry,
        model_loader=lambda model: fake_model,
    )

    backend.start()
    text = backend.transcribe(
        np.zeros(1600, dtype=np.float32),
        extra_prompt="Prefer WhisCode.",
        hotwords=["LLM", "WhisCode"],
    )

    assert text == "hello LLM"
    args, kwargs = fake_model.calls[0]
    assert args[0].shape == (1600,)
    assert kwargs["sampling_rate"] == 16000
    assert kwargs["max_tokens"] == 123
    assert kwargs["temperature"] == 0.2
    assert kwargs["prefill_step_size"] == 456
    assert "Hotwords: LLM, WhisCode" in kwargs["context"]
    assert "Prefer WhisCode." in kwargs["context"]
    assert [event for event, properties in telemetry.events] == [
        "mlx_vibevoice.model_load_started",
        "mlx_vibevoice.model_load_completed",
        "mlx_vibevoice.transcription_started",
        "mlx_vibevoice.transcription_completed",
    ]


def test_backend_telemetry_does_not_include_content():
    fake_model = FakeModel(SimpleNamespace(text="", segments=[{"text": "secret transcript"}]))
    telemetry = FakeTelemetry()
    backend = MlxVibeVoiceBackend(
        MlxVibeVoiceConfig(model="/tmp/VibeVoice-ASR-8bit"),
        telemetry=telemetry,
        model_loader=lambda model: fake_model,
    )

    backend.start()
    backend.transcribe(
        np.zeros(1600, dtype=np.float32),
        extra_prompt="secret prompt",
        hotwords=["secret hotword"],
    )

    serialized = repr(telemetry.events)
    assert "secret transcript" not in serialized
    assert "secret prompt" not in serialized
    assert "secret hotword" not in serialized
    assert "/tmp/VibeVoice-ASR-8bit" not in serialized
    assert "VibeVoice-ASR-8bit" in serialized
