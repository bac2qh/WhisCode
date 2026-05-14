import json

from whiscode.telemetry import Telemetry


def test_telemetry_writes_jsonl(tmp_path):
    path = tmp_path / "events.jsonl"
    telemetry = Telemetry(enabled=True, path=path, session_id="test-session")

    telemetry.emit("test.event", count=2, path=tmp_path / "samples")

    payload = json.loads(path.read_text().strip())
    assert payload["event"] == "test.event"
    assert payload["session_id"] == "test-session"
    assert payload["count"] == 2
    assert payload["path"] == str(tmp_path / "samples")
    assert "timestamp" in payload
    assert "pid" in payload


def test_telemetry_disabled_does_not_create_file(tmp_path):
    path = tmp_path / "events.jsonl"
    telemetry = Telemetry(enabled=False, path=path)

    telemetry.emit("test.event")

    assert not path.exists()
