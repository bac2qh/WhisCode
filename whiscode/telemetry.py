from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_TELEMETRY_PATH = Path.home() / ".config" / "whiscode" / "telemetry" / "events.jsonl"


class Telemetry:
    def __init__(
        self,
        *,
        enabled: bool,
        path: Path | None = None,
        session_id: str | None = None,
    ):
        self.enabled = enabled
        self.path = Path(path).expanduser() if path else DEFAULT_TELEMETRY_PATH
        self.session_id = session_id or uuid.uuid4().hex
        self._warned = False

    def emit(self, event: str, **properties: Any) -> None:
        if not self.enabled:
            return

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "session_id": self.session_id,
            "pid": os.getpid(),
            **_safe_properties(properties),
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        except OSError as e:
            if not self._warned:
                print(f"  Warning: could not write telemetry: {e}", file=sys.stderr)
                self._warned = True


def telemetry_from_args(args, *, default_enabled: bool) -> Telemetry:
    path = getattr(args, "telemetry_path", None)
    enabled = default_enabled and not getattr(args, "no_telemetry", False)
    return Telemetry(enabled=enabled, path=path)


def _safe_properties(properties: dict[str, Any]) -> dict[str, Any]:
    return {key: _safe_value(value) for key, value in properties.items()}


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    return str(value)
