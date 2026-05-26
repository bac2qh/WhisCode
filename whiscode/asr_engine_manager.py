from __future__ import annotations

import threading
import time
from typing import Callable, Protocol

import numpy as np


class AsrEngine(Protocol):
    backend_name: str
    model_label: str

    def transcribe(
        self,
        audio: np.ndarray,
        *,
        language: str = "auto",
        extra_prompt: str | None = None,
        hotwords: list[str] | None = None,
        progress_callback=None,
    ) -> str:
        ...

    def close(self) -> None:
        ...


class AsrEngineManager:
    def __init__(
        self,
        *,
        primary_engine: AsrEngine,
        engine_factory: Callable[[], AsrEngine],
        telemetry=None,
    ):
        self._primary_engine = primary_engine
        self._engine_factory = engine_factory
        self._telemetry = telemetry
        self._lock = threading.Lock()
        self._external_active = False
        self._external_engine: AsrEngine | None = None
        self._rescue_engine: AsrEngine | None = None

    @property
    def backend_name(self) -> str:
        return self._primary_engine.backend_name

    @property
    def model_label(self) -> str:
        return self._primary_engine.model_label

    def transcribe_manual(
        self,
        audio: np.ndarray,
        *,
        language: str = "auto",
        extra_prompt: str | None = None,
        hotwords: list[str] | None = None,
        progress_callback=None,
    ) -> str:
        engine = self._engine_for_manual()
        return engine.transcribe(
            audio,
            language=language,
            extra_prompt=extra_prompt,
            hotwords=hotwords,
            progress_callback=progress_callback,
        )

    def transcribe_external(
        self,
        audio: np.ndarray,
        *,
        language: str = "auto",
    ) -> str:
        with self._lock:
            self._external_active = True
            self._external_engine = self._primary_engine
            engine = self._external_engine
        try:
            return engine.transcribe(
                audio,
                language=language,
                extra_prompt=None,
                hotwords=None,
                progress_callback=None,
            )
        finally:
            self._finish_external()

    def close(self) -> None:
        with self._lock:
            engines = [self._primary_engine]
            if self._rescue_engine is not None and self._rescue_engine is not self._primary_engine:
                engines.append(self._rescue_engine)
            if self._external_engine is not None and self._external_engine not in engines:
                engines.append(self._external_engine)
            self._external_active = False
            self._external_engine = None
            self._rescue_engine = None
        for engine in engines:
            engine.close()

    def _engine_for_manual(self) -> AsrEngine:
        with self._lock:
            if not self._external_active:
                return self._primary_engine
            if self._rescue_engine is not None:
                return self._rescue_engine
            started = time.monotonic()
            if self._telemetry:
                self._telemetry.emit(
                    "asr.engine_rescue_started",
                    backend=self._primary_engine.backend_name,
                    model=self._primary_engine.model_label,
                )
            rescue = self._engine_factory()
            self._rescue_engine = rescue
            if self._telemetry:
                self._telemetry.emit(
                    "asr.engine_rescue_completed",
                    backend=rescue.backend_name,
                    model=rescue.model_label,
                    duration_seconds=round(time.monotonic() - started, 3),
                )
            return rescue

    def _finish_external(self) -> None:
        old_external = None
        promoted = None
        with self._lock:
            old_external = self._external_engine
            if self._rescue_engine is not None:
                promoted = self._rescue_engine
                self._primary_engine = promoted
                self._rescue_engine = None
            self._external_active = False
            self._external_engine = None

        if promoted is not None:
            if self._telemetry:
                self._telemetry.emit(
                    "asr.engine_promoted",
                    backend=promoted.backend_name,
                    model=promoted.model_label,
                )
            if old_external is not None and old_external is not promoted:
                old_external.close()
                if self._telemetry:
                    self._telemetry.emit(
                        "asr.engine_retired",
                        backend=old_external.backend_name,
                        model=old_external.model_label,
                    )
