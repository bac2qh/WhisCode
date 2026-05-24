from __future__ import annotations

import base64
import http.client
import io
import json
import subprocess
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_LLAMA_HOST = "127.0.0.1"
DEFAULT_LLAMA_PORT = 8091
DEFAULT_LLAMA_CONTEXT = 4096
DEFAULT_LLAMA_GPU_LAYERS = 99
DEFAULT_LLAMA_ALIAS = "whiscode-qwen3-asr"
DEFAULT_LLAMA_STARTUP_TIMEOUT_SECONDS = 120.0
DEFAULT_LLAMA_REQUEST_TIMEOUT_SECONDS = 300.0
SAMPLE_RATE = 16000


class LlamaCppAsrError(RuntimeError):
    pass


@dataclass
class LlamaCppServerConfig:
    server_bin: Path
    model: Path
    mmproj: Path
    host: str = DEFAULT_LLAMA_HOST
    port: int = DEFAULT_LLAMA_PORT
    ctx: int = DEFAULT_LLAMA_CONTEXT
    ngl: int = DEFAULT_LLAMA_GPU_LAYERS
    autostart: bool = True
    alias: str = DEFAULT_LLAMA_ALIAS
    startup_timeout_seconds: float = DEFAULT_LLAMA_STARTUP_TIMEOUT_SECONDS
    request_timeout_seconds: float = DEFAULT_LLAMA_REQUEST_TIMEOUT_SECONDS


def default_llama_server_bin() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "llama.cpp" / "build" / "bin" / "llama-server"
        if candidate.exists():
            return candidate
    return Path.home() / "Documents/repos/llama.cpp/build/bin/llama-server"


def default_llama_model_path() -> Path:
    return (
        Path.home()
        / ".lmstudio/models/ggml-org/Qwen3-ASR-1.7B-GGUF/Qwen3-ASR-1.7B-Q8_0.gguf"
    )


def default_llama_mmproj_path() -> Path:
    return (
        Path.home()
        / ".lmstudio/models/ggml-org/Qwen3-ASR-1.7B-GGUF/mmproj-Qwen3-ASR-1.7B-bf16.gguf"
    )


class LlamaCppAsrBackend:
    def __init__(self, config: LlamaCppServerConfig, *, telemetry=None):
        self.config = config
        self.telemetry = telemetry
        self._process: subprocess.Popen | None = None
        self._owns_process = False

    def start(self) -> None:
        health = self.health_check(timeout=1.0)
        if health.ok:
            self._emit(
                "llama.server_health",
                outcome="reachable",
                status_class=health.status_class,
                latency_ms=health.latency_ms,
                port=self.config.port,
            )
            return

        self._emit(
            "llama.server_health",
            outcome="unreachable",
            status_class=health.status_class,
            latency_ms=health.latency_ms,
            port=self.config.port,
            error_type=health.error_type,
        )

        if not self.config.autostart:
            raise LlamaCppAsrError(
                f"llama.cpp server is not reachable at {self.base_url}; start it or remove --no-llama-autostart."
            )

        self._validate_start_inputs()
        started = time.monotonic()
        command = self._server_command()
        try:
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self._owns_process = True
        except Exception as e:
            self._emit("llama.server_start_failed", stage="spawn", error_type=type(e).__name__, port=self.config.port)
            raise LlamaCppAsrError(f"failed to start llama-server: {e}") from e

        try:
            self._wait_until_ready(started)
        except Exception:
            self.close()
            raise

        self._emit(
            "llama.server_started",
            pid=self._process.pid if self._process else None,
            port=self.config.port,
            binary=self.config.server_bin.name,
            model=self.config.model.name,
            duration_seconds=round(time.monotonic() - started, 3),
        )

    def close(self) -> None:
        if not self._owns_process or self._process is None:
            return
        process = self._process
        self._process = None
        self._owns_process = False
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def transcribe(
        self,
        audio: np.ndarray,
        *,
        language: str = "auto",
        extra_prompt: str | None = None,
        hotwords: list[str] | None = None,
        progress_callback=None,
    ) -> str:
        if len(audio) == 0:
            return ""

        del progress_callback
        started = time.monotonic()
        forced_language = qwen_language_for_whiscode(language)
        payload = build_chat_payload(
            audio,
            model=self.config.alias,
            forced_language=forced_language,
            extra_prompt=extra_prompt,
            hotwords=hotwords,
        )
        self._emit(
            "llama.transcription_started",
            audio_samples=len(audio),
            audio_seconds=round(len(audio) / SAMPLE_RATE, 3),
        )
        try:
            response = self._post_json("/v1/chat/completions", payload, timeout=self.config.request_timeout_seconds)
            raw_text = extract_chat_content(response)
            text = parse_qwen_asr_output(raw_text, forced_language=forced_language)
        except _HttpStatusError as e:
            self._emit(
                "llama.transcription_failed",
                duration_seconds=round(time.monotonic() - started, 3),
                http_status_class=(e.status // 100) * 100,
                error_type=type(e).__name__,
            )
            raise LlamaCppAsrError(f"llama.cpp returned HTTP {e.status}") from e
        except LlamaCppAsrError as e:
            self._emit(
                "llama.transcription_failed",
                duration_seconds=round(time.monotonic() - started, 3),
                error_type=type(e).__name__,
            )
            raise
        except Exception as e:
            self._emit(
                "llama.transcription_failed",
                duration_seconds=round(time.monotonic() - started, 3),
                error_type=type(e).__name__,
            )
            raise LlamaCppAsrError(f"llama.cpp transcription failed: {e}") from e

        self._emit(
            "llama.transcription_completed",
            duration_seconds=round(time.monotonic() - started, 3),
            output_chars=len(text),
            outcome="text" if text else "empty",
        )
        return text

    @property
    def base_url(self) -> str:
        return f"http://{self.config.host}:{self.config.port}"

    def health_check(self, *, timeout: float) -> "HealthResult":
        started = time.monotonic()
        try:
            self._request_json("GET", "/v1/models", timeout=timeout)
            return HealthResult(ok=True, status_class=200, latency_ms=round((time.monotonic() - started) * 1000, 1))
        except _HttpStatusError as e:
            return HealthResult(
                ok=False,
                status_class=(e.status // 100) * 100,
                latency_ms=round((time.monotonic() - started) * 1000, 1),
                error_type=type(e).__name__,
            )
        except Exception as e:
            return HealthResult(
                ok=False,
                status_class=None,
                latency_ms=round((time.monotonic() - started) * 1000, 1),
                error_type=type(e).__name__,
            )

    def _wait_until_ready(self, started: float) -> None:
        deadline = started + self.config.startup_timeout_seconds
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                self._emit(
                    "llama.server_start_failed",
                    stage="process_exit",
                    error_type="ProcessExited",
                    port=self.config.port,
                )
                raise LlamaCppAsrError("llama-server exited before becoming ready")
            health = self.health_check(timeout=1.0)
            if health.ok:
                return
            time.sleep(0.5)
        self._emit("llama.server_start_failed", stage="health_timeout", error_type="TimeoutError", port=self.config.port)
        raise LlamaCppAsrError("llama-server did not become ready before timeout")

    def _validate_start_inputs(self) -> None:
        missing = []
        if not self.config.server_bin.is_file():
            missing.append(f"llama-server binary: {self.config.server_bin}")
        if not self.config.server_bin.exists() or not self.config.server_bin.stat().st_mode & 0o111:
            missing.append(f"executable llama-server binary: {self.config.server_bin}")
        if not self.config.model.is_file():
            missing.append(f"llama.cpp model: {self.config.model}")
        if not self.config.mmproj.is_file():
            missing.append(f"llama.cpp mmproj: {self.config.mmproj}")
        if missing:
            self._emit("llama.server_start_failed", stage="validate", error_type="FileNotFoundError", port=self.config.port)
            raise LlamaCppAsrError("Missing " + "; ".join(missing))

    def _server_command(self) -> list[str]:
        return [
            str(self.config.server_bin),
            "-m",
            str(self.config.model),
            "--mmproj",
            str(self.config.mmproj),
            "--host",
            self.config.host,
            "--port",
            str(self.config.port),
            "-ngl",
            str(self.config.ngl),
            "-c",
            str(self.config.ctx),
            "--alias",
            self.config.alias,
            "-fa",
            "on",
            "--jinja",
            "--log-disable",
        ]

    def _post_json(self, path: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
        return self._request_json("POST", path, payload=payload, timeout=timeout)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        timeout: float,
    ) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {"Content-Type": "application/json"} if body is not None else {}
        conn = http.client.HTTPConnection(self.config.host, self.config.port, timeout=timeout)
        try:
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            data = response.read()
        finally:
            conn.close()
        if response.status < 200 or response.status >= 300:
            raise _HttpStatusError(response.status)
        if not data:
            return {}
        try:
            return json.loads(data.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise LlamaCppAsrError("llama.cpp returned invalid JSON") from e

    def _emit(self, event: str, **properties: Any) -> None:
        if self.telemetry is not None:
            self.telemetry.emit(event, **properties)


@dataclass
class HealthResult:
    ok: bool
    status_class: int | None
    latency_ms: float
    error_type: str | None = None


class _HttpStatusError(RuntimeError):
    def __init__(self, status: int):
        super().__init__(f"HTTP {status}")
        self.status = status


def build_chat_payload(
    audio: np.ndarray,
    *,
    model: str,
    forced_language: str | None = None,
    extra_prompt: str | None = None,
    hotwords: list[str] | None = None,
) -> dict[str, Any]:
    context = build_context(extra_prompt=extra_prompt, hotwords=hotwords)
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": context},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": base64.b64encode(audio_to_wav_bytes(audio)).decode("ascii"),
                            "format": "wav",
                        },
                    }
                ],
            },
        ],
        "temperature": 0.0,
        "top_p": 1.0,
        "max_tokens": 1024,
        "stream": False,
    }
    if forced_language:
        payload["generation_prompt"] = f"language {forced_language}<asr_text>"
    return payload


def build_context(*, extra_prompt: str | None, hotwords: list[str] | None) -> str:
    parts = []
    if extra_prompt:
        parts.append(extra_prompt.strip())
    if hotwords:
        parts.append("Hotwords: " + ", ".join(word for word in hotwords if word))
    return " ".join(part for part in parts if part)


def audio_to_wav_bytes(audio: np.ndarray, *, sample_rate: int = SAMPLE_RATE) -> bytes:
    mono = np.asarray(audio, dtype=np.float32).flatten()
    clipped = np.clip(mono, -1.0, 1.0)
    pcm = (clipped * 32767.0).astype("<i2")
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    return output.getvalue()


def extract_chat_content(response: dict[str, Any]) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LlamaCppAsrError("llama.cpp response did not include chat content") from e
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return str(content)


def parse_qwen_asr_output(raw: str, *, forced_language: str | None = None) -> str:
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""

    if "<asr_text>" in text:
        meta, text_part = text.split("<asr_text>", 1)
        if "language none" in meta.lower() and not text_part.strip():
            return ""
        return text_part.strip()

    if forced_language:
        prefix = f"language {forced_language}"
        if text.lower().startswith(prefix.lower()):
            return text[len(prefix):].strip()
    return text


def qwen_language_for_whiscode(language: str | None) -> str | None:
    if not language or language == "auto":
        return None
    normalized = language.strip()
    mapping = {
        "zh": "Chinese",
        "cn": "Chinese",
        "chinese": "Chinese",
        "en": "English",
        "english": "English",
        "yue": "Cantonese",
        "cantonese": "Cantonese",
        "ja": "Japanese",
        "japanese": "Japanese",
        "ko": "Korean",
        "korean": "Korean",
    }
    mapped = mapping.get(normalized.lower())
    if mapped:
        return mapped
    return normalized[:1].upper() + normalized[1:].lower()
