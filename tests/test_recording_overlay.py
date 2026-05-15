import io
import json
import subprocess
from unittest.mock import Mock, patch

import numpy as np

from whiscode.recording_overlay import RecordingOverlayClient, _draw_attributed_text, _read_helper_commands


def make_process():
    process = Mock()
    process.stdin = io.StringIO()
    process.poll.return_value = None
    return process


def sent_commands(process):
    return [json.loads(line) for line in process.stdin.getvalue().splitlines()]


def test_overlay_client_sends_show_hide_stop_commands():
    process = make_process()

    with (
        patch("subprocess.Popen", return_value=process) as popen,
        patch.object(RecordingOverlayClient, "_ensure_sender_thread"),
    ):
        client = RecordingOverlayClient(update_interval=999)
        client.show()
        client.hide()
        client.stop()

    assert popen.call_args.args[0][1:] == ["-m", "whiscode.recording_overlay", "--helper"]
    assert sent_commands(process) == [
        {"command": "show"},
        {"command": "hide"},
        {"command": "stop"},
    ]
    process.terminate.assert_called_once()
    process.wait.assert_called_once()


def test_overlay_client_stop_kills_helper_when_terminate_times_out():
    process = make_process()
    process.wait.side_effect = [subprocess.TimeoutExpired("overlay", 0.01), None]

    with patch("subprocess.Popen", return_value=process):
        client = RecordingOverlayClient(stop_timeout=0.01)
        client.show()
        client.stop()

    process.terminate.assert_called_once()
    process.kill.assert_called_once()
    assert process.wait.call_count == 2


def test_overlay_client_update_level_clamps_audio_level():
    client = RecordingOverlayClient()

    client.update_level(np.array([0.0, 1.0], dtype=np.float32))

    assert client._latest_level == 1.0


def test_overlay_client_disables_when_helper_fails_to_start():
    with patch("subprocess.Popen", side_effect=OSError("missing appkit")):
        client = RecordingOverlayClient()
        client.show()

    assert client.enabled is False


class FakeTelemetry:
    def __init__(self):
        self.events = []

    def emit(self, event, **properties):
        self.events.append((event, properties))


def test_overlay_client_reports_helper_exit(capsys):
    process = make_process()
    process.poll.return_value = -5
    telemetry = FakeTelemetry()

    with patch("subprocess.Popen", return_value=process):
        client = RecordingOverlayClient(telemetry=telemetry)
        client.show()

    assert client.enabled is False
    assert client._visible is False
    assert sent_commands(process) == []
    assert ("recording_overlay.disabled", {"reason": "helper_exited", "stage": "show", "returncode": -5}) in telemetry.events
    assert "recording overlay disabled: reason=helper_exited stage=show returncode=-5" in capsys.readouterr().err


def test_overlay_client_stop_before_show_is_quiet(capsys):
    telemetry = FakeTelemetry()
    client = RecordingOverlayClient(telemetry=telemetry)

    client.stop()

    assert client.enabled is True
    assert telemetry.events == []
    assert capsys.readouterr().err == ""


class FakeAttributedString:
    last = None

    @classmethod
    def alloc(cls):
        return cls()

    def initWithString_attributes_(self, text, attrs):
        self.text = text
        self.attrs = attrs
        self.point = None
        FakeAttributedString.last = self
        return self

    def drawAtPoint_(self, point):
        self.point = point


def test_draw_attributed_text_uses_attributed_string_draw_path():
    attrs = {"font": "mono", "color": "white"}

    result = _draw_attributed_text(
        "00:03",
        "point",
        attrs,
        attributed_string_class=FakeAttributedString,
    )

    assert result is FakeAttributedString.last
    assert result.text == "00:03"
    assert result.attrs == attrs
    assert result.point == "point"


def test_read_helper_commands_schedules_stop_on_eof():
    controller = Mock()
    calls = []

    _read_helper_commands(
        io.StringIO('{"command":"show"}\n{"command":"hide"}\n'),
        controller,
        lambda fn, command: calls.append((fn, command)),
    )

    assert calls == [
        (controller.handle, {"command": "show"}),
        (controller.handle, {"command": "hide"}),
        (controller.handle, {"command": "stop"}),
    ]


def test_read_helper_commands_ignores_bad_json_but_stops_on_eof():
    controller = Mock()
    calls = []

    _read_helper_commands(
        io.StringIO('not-json\n{"command":"level","level":0.4}\n'),
        controller,
        lambda fn, command: calls.append((fn, command)),
    )

    assert calls == [
        (controller.handle, {"command": "level", "level": 0.4}),
        (controller.handle, {"command": "stop"}),
    ]
