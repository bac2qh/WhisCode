from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from whiscode.crispasr_asr import CrispAsrError, extract_crispasr_text
from whiscode.recorder import SAMPLE_RATE

DEFAULT_MLX_VIBEVOICE_MODEL = Path.home() / "Documents/models/mlx-community/VibeVoice-ASR-8bit"
DEFAULT_MLX_VIBEVOICE_MAX_TOKENS = 8192
DEFAULT_MLX_VIBEVOICE_TEMPERATURE = 0.0
DEFAULT_MLX_VIBEVOICE_PREFILL_STEP_SIZE = 2048
TECHNICAL_DICTATION_CONTEXT = (
    "Technical dictation may include programming terms, CLI commands, repository names, "
    "APIs, model names, and mixed English/Chinese."
)


class MlxVibeVoiceError(RuntimeError):
    pass


def default_mlx_vibevoice_model() -> str:
    configured = os.environ.get("WHISCODE_MLX_VIBEVOICE_MODEL")
    if configured:
        return str(Path(configured).expanduser()) if _looks_like_path(configured) else configured
    return str(DEFAULT_MLX_VIBEVOICE_MODEL)


@dataclass
class MlxVibeVoiceConfig:
    model: str = field(default_factory=default_mlx_vibevoice_model)
    max_tokens: int = DEFAULT_MLX_VIBEVOICE_MAX_TOKENS
    temperature: float = DEFAULT_MLX_VIBEVOICE_TEMPERATURE
    prefill_step_size: int = DEFAULT_MLX_VIBEVOICE_PREFILL_STEP_SIZE


class MlxVibeVoiceBackend:
    def __init__(
        self,
        config: MlxVibeVoiceConfig,
        *,
        telemetry=None,
        model_loader: Callable[[str], Any] | None = None,
    ):
        self.config = config
        self.telemetry = telemetry
        self.model_loader = model_loader
        self.model = None

    @property
    def model_location(self) -> str:
        return _resolve_model_location(self.config.model)

    @property
    def model_label(self) -> str:
        return _model_label(self.config.model)

    def start(self) -> None:
        if self.model is not None:
            return
        started = time.monotonic()
        if self.telemetry:
            self.telemetry.emit("mlx_vibevoice.model_load_started", model=self.model_label)
        try:
            loader = self.model_loader
            if loader is None:
                from mlx_audio.stt import load

                loader = load
            self.model = loader(self.model_location)
        except Exception as e:
            if self.telemetry:
                self.telemetry.emit(
                    "mlx_vibevoice.model_load_failed",
                    model=self.model_label,
                    error_type=type(e).__name__,
                )
            raise MlxVibeVoiceError(f"failed to load MLX VibeVoice model '{self.config.model}': {e}") from e
        if self.telemetry:
            self.telemetry.emit(
                "mlx_vibevoice.model_load_completed",
                model=self.model_label,
                duration_seconds=round(time.monotonic() - started, 3),
            )

    def transcribe(
        self,
        audio: np.ndarray,
        *,
        language: str = "auto",
        extra_prompt: str | None = None,
        hotwords: list[str] | None = None,
        progress_callback=None,
    ) -> str:
        del language, progress_callback
        if len(audio) == 0:
            return ""
        if self.model is None:
            raise MlxVibeVoiceError("MLX VibeVoice model is not loaded")

        context = build_mlx_vibevoice_context(extra_prompt=extra_prompt, hotwords=hotwords)
        audio_seconds = len(audio) / SAMPLE_RATE if len(audio) else 0.0
        started = time.monotonic()
        if self.telemetry:
            self.telemetry.emit(
                "mlx_vibevoice.transcription_started",
                model=self.model_label,
                audio_seconds=round(audio_seconds, 3),
                hotword_count=len([word for word in hotwords or [] if word and word.strip()]),
                has_extra_prompt=bool(extra_prompt and extra_prompt.strip()),
                context_chars=len(context or ""),
            )
        try:
            result = self.model.generate(
                audio,
                sampling_rate=SAMPLE_RATE,
                context=context,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                prefill_step_size=self.config.prefill_step_size,
                verbose=False,
            )
            text = extract_mlx_vibevoice_text(result)
        except Exception as e:
            if self.telemetry:
                self.telemetry.emit(
                    "mlx_vibevoice.transcription_failed",
                    model=self.model_label,
                    error_type=type(e).__name__,
                    duration_seconds=round(time.monotonic() - started, 3),
                )
            if isinstance(e, MlxVibeVoiceError):
                raise
            raise MlxVibeVoiceError(f"MLX VibeVoice transcription failed: {e}") from e

        if self.telemetry:
            self.telemetry.emit(
                "mlx_vibevoice.transcription_completed",
                model=self.model_label,
                duration_seconds=round(time.monotonic() - started, 3),
                output_chars=len(text),
            )
        return text

    def close(self) -> None:
        self.model = None


def build_mlx_vibevoice_context(*, extra_prompt: str | None, hotwords: list[str] | None) -> str:
    parts: list[str] = []
    filtered_hotwords = [word.strip() for word in hotwords or [] if word and word.strip()]
    if filtered_hotwords:
        parts.append("Hotwords: " + ", ".join(filtered_hotwords))
    if extra_prompt and extra_prompt.strip():
        parts.append(extra_prompt.strip())
    parts.append(TECHNICAL_DICTATION_CONTEXT)
    return "\n".join(parts)


def extract_mlx_vibevoice_text(result: Any) -> str:
    segments = getattr(result, "segments", None)
    if segments:
        text = _join_segments(segments)
        if text:
            return text

    raw_text = str(getattr(result, "text", "") or "").strip()
    if not raw_text:
        return ""
    try:
        return extract_crispasr_text({"text": raw_text})
    except CrispAsrError as e:
        raise MlxVibeVoiceError("MLX VibeVoice chunks were malformed") from e


def _join_segments(segments: Any) -> str:
    if not isinstance(segments, list):
        return ""
    contents: list[str] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        content = segment.get("text", segment.get("Content"))
        if isinstance(content, str) and content.strip():
            contents.append(content.strip())
    return " ".join(contents)


def _resolve_model_location(model: str) -> str:
    return str(Path(model).expanduser()) if _looks_like_path(model) else model


def _model_label(model: str) -> str:
    if _looks_like_path(model):
        return Path(model).expanduser().name
    return model.rsplit("/", 1)[-1]


def _looks_like_path(value: str) -> bool:
    return value.startswith(("~", "/", ".")) or Path(value).expanduser().exists()
