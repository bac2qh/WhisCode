from __future__ import annotations

import http.client
import io
import json
import os
import subprocess
import time
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from whiscode.transcriber import CODE_PROMPT

DEFAULT_CRISPASR_HOST = "127.0.0.1"
DEFAULT_CRISPASR_PORT = 8092
DEFAULT_CRISPASR_BACKEND = "vibevoice"
DEFAULT_CRISPASR_MAX_TOKENS = 2048
DEFAULT_CRISPASR_TEMPERATURE = 0.0
DEFAULT_CRISPASR_STARTUP_TIMEOUT_SECONDS = 180.0
DEFAULT_CRISPASR_REQUEST_TIMEOUT_SECONDS = 300.0
SAMPLE_RATE = 16000


class CrispAsrError(RuntimeError):
    pass


@dataclass
class CrispAsrServerConfig:
    server_bin: Path
    model: Path
    backend: str = DEFAULT_CRISPASR_BACKEND
    host: str = DEFAULT_CRISPASR_HOST
    port: int = DEFAULT_CRISPASR_PORT
    autostart: bool = True
    max_tokens: int = DEFAULT_CRISPASR_MAX_TOKENS
    temperature: float = DEFAULT_CRISPASR_TEMPERATURE
    startup_timeout_seconds: float = DEFAULT_CRISPASR_STARTUP_TIMEOUT_SECONDS
    request_timeout_seconds: float = DEFAULT_CRISPASR_REQUEST_TIMEOUT_SECONDS


def default_crispasr_bin() -> Path:
    configured = os.environ.get("WHISCODE_CRISPASR_BIN")
    if configured:
        return Path(configured).expanduser()
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "CrispASR" / "build" / "bin" / "crispasr"
        if candidate.exists():
            return candidate
    return Path.home() / "Documents/repos/CrispASR/build/bin/crispasr"


def default_crispasr_model_path() -> Path:
    configured = os.environ.get("WHISCODE_CRISPASR_MODEL")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "Documents/models/vibevoice-asr-GGUF/vibevoice-asr-f16.gguf"


class CrispAsrBackend:
    def __init__(self, config: CrispAsrServerConfig, *, telemetry=None):
        self.config = config
        self.telemetry = telemetry
        self._process: subprocess.Popen | None = None
        self._owns_process = False

    def start(self) -> None:
        health = self.health_check(timeout=1.0)
        if health.ok:
            self._emit(
                "crispasr.server_health",
                outcome="reachable",
                status_class=health.status_class,
                latency_ms=health.latency_ms,
                port=self.config.port,
                backend=self.config.backend,
            )
            return

        self._emit(
            "crispasr.server_health",
            outcome="unreachable",
            status_class=health.status_class,
            latency_ms=health.latency_ms,
            port=self.config.port,
            backend=self.config.backend,
            error_type=health.error_type,
        )

        if not self.config.autostart:
            raise CrispAsrError(
                f"CrispASR server is not reachable at {self.base_url}; start it or remove --no-crispasr-autostart."
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
            self._emit(
                "crispasr.server_start_failed",
                stage="spawn",
                error_type=type(e).__name__,
                port=self.config.port,
                backend=self.config.backend,
            )
            raise CrispAsrError(f"failed to start CrispASR: {e}") from e

        try:
            self._wait_until_ready(started)
        except Exception:
            self.close()
            raise

        self._emit(
            "crispasr.server_started",
            pid=self._process.pid if self._process else None,
            port=self.config.port,
            backend=self.config.backend,
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

    @property
    def owns_process(self) -> bool:
        return self._owns_process

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
        prompt = build_crispasr_prompt(extra_prompt=extra_prompt, hotwords=hotwords)
        fields: dict[str, str] = {
            "response_format": "json",
            "prompt": prompt,
            "temperature": str(self.config.temperature),
            "max_tokens": str(self.config.max_tokens),
        }
        if language and language != "auto":
            fields["language"] = language

        self._emit(
            "crispasr.transcription_started",
            audio_samples=len(audio),
            audio_seconds=round(len(audio) / SAMPLE_RATE, 3),
            backend=self.config.backend,
        )

        try:
            response = self._post_multipart(
                "/v1/audio/transcriptions",
                fields=fields,
                file_field="file",
                filename="audio.wav",
                file_bytes=audio_to_wav_bytes(audio),
                timeout=self.config.request_timeout_seconds,
            )
            text = extract_crispasr_text(response)
        except _HttpStatusError as e:
            self._emit(
                "crispasr.transcription_failed",
                duration_seconds=round(time.monotonic() - started, 3),
                http_status_class=(e.status // 100) * 100,
                error_type=type(e).__name__,
                backend=self.config.backend,
            )
            raise CrispAsrError(f"CrispASR returned HTTP {e.status}") from e
        except CrispAsrError:
            self._emit(
                "crispasr.transcription_failed",
                duration_seconds=round(time.monotonic() - started, 3),
                error_type="CrispAsrError",
                backend=self.config.backend,
            )
            raise
        except Exception as e:
            self._emit(
                "crispasr.transcription_failed",
                duration_seconds=round(time.monotonic() - started, 3),
                error_type=type(e).__name__,
                backend=self.config.backend,
            )
            raise CrispAsrError(f"CrispASR transcription failed: {e}") from e

        self._emit(
            "crispasr.transcription_completed",
            duration_seconds=round(time.monotonic() - started, 3),
            output_chars=len(text),
            outcome="text" if text else "empty",
            backend=self.config.backend,
        )
        return text

    @property
    def base_url(self) -> str:
        return f"http://{self.config.host}:{self.config.port}"

    def health_check(self, *, timeout: float) -> "HealthResult":
        started = time.monotonic()
        try:
            self._request_json("GET", "/health", timeout=timeout)
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
                    "crispasr.server_start_failed",
                    stage="process_exit",
                    error_type="ProcessExited",
                    port=self.config.port,
                    backend=self.config.backend,
                )
                raise CrispAsrError("CrispASR exited before becoming ready")
            health = self.health_check(timeout=1.0)
            if health.ok:
                return
            time.sleep(0.5)
        self._emit(
            "crispasr.server_start_failed",
            stage="health_timeout",
            error_type="TimeoutError",
            port=self.config.port,
            backend=self.config.backend,
        )
        raise CrispAsrError("CrispASR did not become ready before timeout")

    def _validate_start_inputs(self) -> None:
        missing = []
        if not self.config.server_bin.is_file():
            missing.append(f"CrispASR binary: {self.config.server_bin}")
        if not self.config.server_bin.exists() or not self.config.server_bin.stat().st_mode & 0o111:
            missing.append(f"executable CrispASR binary: {self.config.server_bin}")
        if not self.config.model.is_file():
            missing.append(f"CrispASR model: {self.config.model}")
        if missing:
            self._emit(
                "crispasr.server_start_failed",
                stage="validate",
                error_type="FileNotFoundError",
                port=self.config.port,
                backend=self.config.backend,
            )
            raise CrispAsrError("Missing " + "; ".join(missing))

    def _server_command(self) -> list[str]:
        return [
            str(self.config.server_bin),
            "--server",
            "--backend",
            self.config.backend,
            "-m",
            str(self.config.model),
            "--host",
            self.config.host,
            "--port",
            str(self.config.port),
        ]

    def _post_multipart(
        self,
        path: str,
        *,
        fields: dict[str, str],
        file_field: str,
        filename: str,
        file_bytes: bytes,
        timeout: float,
    ) -> dict[str, Any]:
        body, content_type = build_multipart_form(
            fields=fields,
            file_field=file_field,
            filename=filename,
            file_bytes=file_bytes,
        )
        headers = {"Content-Type": content_type}
        return self._request_json("POST", path, body=body, headers=headers, timeout=timeout)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float,
    ) -> dict[str, Any]:
        conn = http.client.HTTPConnection(self.config.host, self.config.port, timeout=timeout)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            data = response.read()
        finally:
            conn.close()
        if response.status < 200 or response.status >= 300:
            raise _HttpStatusError(response.status)
        if not data:
            return {}
        text = data.decode("utf-8")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"text": text}
        if isinstance(parsed, dict):
            return parsed
        return {"text": str(parsed)}

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


def build_crispasr_prompt(*, extra_prompt: str | None, hotwords: list[str] | None) -> str:
    parts = [CODE_PROMPT]
    if extra_prompt:
        parts.append(extra_prompt.strip())
    filtered_hotwords = [word for word in hotwords or [] if word]
    if filtered_hotwords:
        parts.append("Hotwords: " + ", ".join(filtered_hotwords))
    return " ".join(part for part in parts if part)


def build_multipart_form(
    *,
    fields: dict[str, str],
    file_field: str,
    filename: str,
    file_bytes: bytes,
    boundary: str | None = None,
) -> tuple[bytes, str]:
    boundary = boundary or f"----whiscode-{uuid.uuid4().hex}"
    output = io.BytesIO()
    for name, value in fields.items():
        output.write(f"--{boundary}\r\n".encode("utf-8"))
        output.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        output.write(str(value).encode("utf-8"))
        output.write(b"\r\n")
    output.write(f"--{boundary}\r\n".encode("utf-8"))
    output.write(
        (
            f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
            "Content-Type: audio/wav\r\n\r\n"
        ).encode("utf-8")
    )
    output.write(file_bytes)
    output.write(b"\r\n")
    output.write(f"--{boundary}--\r\n".encode("utf-8"))
    return output.getvalue(), f"multipart/form-data; boundary={boundary}"


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


def extract_crispasr_text(response: dict[str, Any]) -> str:
    try:
        text = response["text"]
    except (KeyError, TypeError) as e:
        raise CrispAsrError("CrispASR response did not include text") from e
    return str(text or "").strip()
