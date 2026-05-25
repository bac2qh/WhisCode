from __future__ import annotations

import http.client
import io
import json
import os
import re
import subprocess
import time
import uuid
import wave
from dataclasses import dataclass
from datetime import datetime, timezone
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
DEFAULT_CRISPASR_RAW_RESPONSE_LOG_PATH = Path.home() / "Library" / "Logs" / "WhisCode" / "crispasr-raw-responses.jsonl"
RAW_RESPONSE_BODY_KEY = "_whiscode_raw_response_body"
SAMPLE_RATE = 16000
_CONTENT_KEY_PATTERN = re.compile(r"""(["'])Content\1\s*:\s*(["'])""")


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
            text = extract_crispasr_text(response, telemetry=self.telemetry)
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
        return self._request_json("POST", path, body=body, headers=headers, timeout=timeout, include_raw_body=True)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float,
        include_raw_body: bool = False,
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
            return {RAW_RESPONSE_BODY_KEY: ""} if include_raw_body else {}
        text = data.decode("utf-8")
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            result: dict[str, Any] = {"text": text}
            if include_raw_body:
                result[RAW_RESPONSE_BODY_KEY] = text
            return result
        if isinstance(parsed, dict):
            result = dict(parsed)
        else:
            result = {"text": parsed}
        if include_raw_body:
            result[RAW_RESPONSE_BODY_KEY] = text
        return result

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


def extract_crispasr_text(response: dict[str, Any], *, telemetry=None) -> str:
    try:
        text = response["text"]
    except (KeyError, TypeError) as e:
        raise CrispAsrError("CrispASR response did not include text") from e
    if isinstance(text, list):
        return _join_vibevoice_chunks(text, telemetry=telemetry, response=response)
    if isinstance(text, str):
        stripped = text.strip()
        chunk_list_text = _vibevoice_chunk_list_string_candidate(stripped)
        if chunk_list_text is not None:
            try:
                parsed = json.loads(chunk_list_text)
            except json.JSONDecodeError as e:
                debug_result = _emit_vibevoice_shape_invalid(
                    telemetry,
                    response=response,
                    stage="json_parse",
                    text_type="str",
                    string_length=len(stripped),
                    prefix_class=_vibevoice_string_prefix_class(stripped),
                )
                recovered = _extract_vibevoice_content_best_effort(chunk_list_text)
                if recovered is not None:
                    text, content_count = recovered
                    _emit_vibevoice_shape_recovered(
                        telemetry,
                        stage="json_parse",
                        method="content_scan",
                        recovered_content_count=content_count,
                        string_length=len(stripped),
                        raw_response_logged=debug_result.logged if debug_result else None,
                        raw_response_log=debug_result.path.name if debug_result else None,
                    )
                    return text
                raise CrispAsrError("CrispASR VibeVoice chunks were malformed") from e
            if isinstance(parsed, list):
                return _join_vibevoice_chunks(parsed, telemetry=telemetry, response=response)
        return stripped
    return str(text or "").strip()


def _vibevoice_chunk_list_string_candidate(text: str) -> str | None:
    if _looks_like_vibevoice_chunk_list_string(text):
        return text
    unwrapped = _strip_vibevoice_raw_output_wrappers(text)
    if unwrapped != text and _looks_like_vibevoice_chunk_list_string(unwrapped):
        return unwrapped
    return None


def _strip_vibevoice_raw_output_wrappers(text: str) -> str:
    stripped = text.strip()
    for prefix in ("<|im_start|>assistant", "assistant"):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix) :].strip()
            break
    changed = True
    while changed:
        changed = False
        for suffix in ("<|endoftext|>", "<|im_end|>"):
            if stripped.endswith(suffix):
                stripped = stripped[: -len(suffix)].strip()
                changed = True
    return stripped


def _looks_like_vibevoice_chunk_list_string(text: str) -> bool:
    if not text.startswith("["):
        return False
    remainder = text[1:].lstrip()
    return not remainder or remainder.startswith("{") or remainder.startswith("]")


def _join_vibevoice_chunks(chunks: list[Any], *, telemetry=None, response: dict[str, Any] | None = None) -> str:
    if not chunks:
        _emit_vibevoice_shape_invalid(telemetry, response=response, stage="chunk_list", text_type="list", list_length=0)
        raise CrispAsrError("CrispASR VibeVoice chunks were empty")

    contents = []
    missing_content_count = 0
    non_string_content_count = 0
    for chunk in chunks:
        if not isinstance(chunk, dict):
            _emit_vibevoice_shape_invalid(
                telemetry,
                response=response,
                stage="chunk_item",
                text_type="list",
                list_length=len(chunks),
                item_type=type(chunk).__name__,
            )
            raise CrispAsrError("CrispASR VibeVoice chunks were malformed")
        if "Content" not in chunk:
            missing_content_count += 1
            continue
        content = chunk["Content"]
        if not isinstance(content, str):
            non_string_content_count += 1
            continue
        stripped = content.strip()
        if stripped:
            contents.append(stripped)

    if missing_content_count or non_string_content_count:
        _emit_vibevoice_shape_invalid(
            telemetry,
            response=response,
            stage="chunk_content",
            text_type="list",
            list_length=len(chunks),
            missing_content_count=missing_content_count,
            non_string_content_count=non_string_content_count,
        )
        raise CrispAsrError("CrispASR VibeVoice chunks were malformed")

    if not contents:
        _emit_vibevoice_shape_invalid(
            telemetry,
            response=response,
            stage="chunk_content",
            text_type="list",
            list_length=len(chunks),
            empty_content_count=len(chunks),
        )
        raise CrispAsrError("CrispASR VibeVoice chunks were empty")
    return " ".join(contents)


def _extract_vibevoice_content_best_effort(text: str) -> tuple[str, int] | None:
    contents = []
    for match in _CONTENT_KEY_PATTERN.finditer(text):
        value_quote = match.group(2)
        value = _scan_jsonish_string_value(text, match.end(), value_quote)
        if value is None:
            continue
        stripped = value.strip()
        if stripped:
            contents.append(stripped)
    if not contents:
        return None
    return " ".join(contents), len(contents)


def _scan_jsonish_string_value(text: str, start: int, quote: str) -> str | None:
    value = []
    i = start
    while i < len(text):
        char = text[i]
        if char == "\\" and i + 1 < len(text):
            value.append(_decode_jsonish_escape(text[i + 1]))
            i += 2
            continue
        if char == quote and _looks_like_jsonish_value_end(text, i + 1):
            return "".join(value)
        value.append(char)
        i += 1
    return None


def _decode_jsonish_escape(char: str) -> str:
    escapes = {
        '"': '"',
        "'": "'",
        "\\": "\\",
        "/": "/",
        "b": "\b",
        "f": "\f",
        "n": "\n",
        "r": "\r",
        "t": "\t",
    }
    return escapes.get(char, char)


def _looks_like_jsonish_value_end(text: str, index: int) -> bool:
    while index < len(text) and text[index].isspace():
        index += 1
    return index >= len(text) or text[index] in ",}]"


def _vibevoice_string_prefix_class(text: str) -> str:
    if text.startswith("[{"):
        return "list_object"
    if text.startswith("[]"):
        return "empty_list"
    if text.startswith("["):
        return "list_other"
    if text.startswith("<|im_start|>assistant"):
        return "assistant_special_token"
    if text.startswith("assistant"):
        return "assistant"
    return "other"


@dataclass(frozen=True)
class _RawResponseDebugResult:
    logged: bool
    path: Path
    error_type: str | None = None


def _emit_vibevoice_shape_invalid(
    telemetry,
    *,
    response: dict[str, Any] | None = None,
    **properties: Any,
) -> _RawResponseDebugResult | None:
    debug_result = _write_crispasr_raw_response_debug(response, telemetry, stage=str(properties.get("stage", "unknown")))
    if debug_result is not None:
        properties = {
            **properties,
            "raw_response_logged": debug_result.logged,
            "raw_response_log": debug_result.path.name,
        }
        if debug_result.error_type:
            properties["raw_response_log_error_type"] = debug_result.error_type
    if telemetry is not None:
        telemetry.emit("crispasr.response_shape_invalid", **properties)
    return debug_result


def _emit_vibevoice_shape_recovered(telemetry, **properties: Any) -> None:
    if telemetry is not None:
        telemetry.emit(
            "crispasr.response_shape_recovered",
            **{key: value for key, value in properties.items() if value is not None},
        )


def _write_crispasr_raw_response_debug(
    response: dict[str, Any] | None,
    telemetry,
    *,
    stage: str,
) -> _RawResponseDebugResult | None:
    if telemetry is None or getattr(telemetry, "enabled", True) is False:
        return None
    if not isinstance(response, dict) or RAW_RESPONSE_BODY_KEY not in response:
        return None
    raw_body = response[RAW_RESPONSE_BODY_KEY]
    if not isinstance(raw_body, str):
        raw_body = json.dumps(raw_body, ensure_ascii=False, sort_keys=True)

    path = _crispasr_raw_response_log_path(telemetry)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_id": getattr(telemetry, "session_id", None),
        "pid": os.getpid(),
        "stage": stage,
        "raw_response_body": raw_body,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    except OSError as e:
        return _RawResponseDebugResult(logged=False, path=path, error_type=type(e).__name__)
    return _RawResponseDebugResult(logged=True, path=path)


def _crispasr_raw_response_log_path(telemetry) -> Path:
    telemetry_path = getattr(telemetry, "path", None)
    if telemetry_path:
        return Path(telemetry_path).expanduser().with_name("crispasr-raw-responses.jsonl")
    return DEFAULT_CRISPASR_RAW_RESPONSE_LOG_PATH
