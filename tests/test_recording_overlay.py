import io
import json
import os
import signal
import subprocess
from unittest.mock import Mock, patch

import numpy as np

from whiscode.recording_overlay import (
    OverlayCleanupResult,
    OverlayHelperProcess,
    RecordingOverlayClient,
    _draw_attributed_text,
    _parse_overlay_helper_processes,
    _read_helper_commands,
    _watch_parent,
    cleanup_orphan_helpers,
    main,
)


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
        patch(
            "whiscode.recording_overlay.cleanup_orphan_helpers",
            return_value=OverlayCleanupResult(0, 0, 0),
        ),
        patch.object(RecordingOverlayClient, "_ensure_sender_thread"),
    ):
        client = RecordingOverlayClient(update_interval=999)
        client.show()
        client.hide()
        client.stop()

    assert popen.call_args.args[0][1:] == [
        "-m",
        "whiscode.recording_overlay",
        "--helper",
        "--parent-pid",
        str(os.getpid()),
    ]
    assert sent_commands(process) == [
        {"command": "show_recording", "item_id": "legacy"},
        {"command": "remove_item", "item_id": "legacy"},
        {"command": "stop"},
    ]
    process.terminate.assert_called_once()
    process.wait.assert_called_once()


def test_overlay_client_sends_transcription_commands():
    process = make_process()

    with (
        patch("subprocess.Popen", return_value=process),
        patch(
            "whiscode.recording_overlay.cleanup_orphan_helpers",
            return_value=OverlayCleanupResult(0, 0, 0),
        ),
    ):
        client = RecordingOverlayClient(update_interval=999)
        client.show_transcribing(total_frames=10)
        client.update_transcription_progress(current_frames=5, total_frames=10, rate=123.4)
        client.hide()

    assert sent_commands(process) == [
        {"command": "show_transcribing", "item_id": "legacy", "total_frames": 10},
        {"command": "transcription_progress", "current_frames": 5, "total_frames": 10, "rate": 123.4},
        {"command": "remove_item", "item_id": "legacy"},
    ]
    assert client._visible is False
    assert client._mode is None


def test_overlay_client_clamps_transcription_progress():
    process = make_process()

    with (
        patch("subprocess.Popen", return_value=process),
        patch(
            "whiscode.recording_overlay.cleanup_orphan_helpers",
            return_value=OverlayCleanupResult(0, 0, 0),
        ),
    ):
        client = RecordingOverlayClient(update_interval=999)
        client.show_transcribing(total_frames=-10)
        client.update_transcription_progress(current_frames=-5, total_frames=-10, rate=-3.0)

    assert sent_commands(process) == [
        {"command": "show_transcribing", "item_id": "legacy", "total_frames": 0},
        {"command": "transcription_progress", "current_frames": 0, "total_frames": 0, "rate": 0.0},
    ]


def test_overlay_client_sends_stacked_item_commands():
    process = make_process()

    with (
        patch("subprocess.Popen", return_value=process),
        patch(
            "whiscode.recording_overlay.cleanup_orphan_helpers",
            return_value=OverlayCleanupResult(0, 0, 0),
        ),
        patch.object(RecordingOverlayClient, "_ensure_sender_thread"),
    ):
        client = RecordingOverlayClient(update_interval=999)
        client.show_recording_item("job-2")
        client.show_queued_item("job-2", audio_seconds=3.25)
        client.show_transcribing_item("job-1", audio_seconds=1.5)
        client.update_transcription_progress(item_id="job-1", current_frames=4, total_frames=8)
        client.remove_item("job-1")

    assert sent_commands(process) == [
        {"command": "show_recording", "item_id": "job-2"},
        {"command": "show_queued", "item_id": "job-2", "audio_seconds": 3.25},
        {"command": "show_transcribing", "item_id": "job-1", "audio_seconds": 1.5},
        {"command": "transcription_progress", "item_id": "job-1", "current_frames": 4, "total_frames": 8},
        {"command": "remove_item", "item_id": "job-1"},
    ]


def test_overlay_client_stop_kills_helper_when_terminate_times_out():
    process = make_process()
    process.wait.side_effect = [subprocess.TimeoutExpired("overlay", 0.01), None]

    with (
        patch("subprocess.Popen", return_value=process),
        patch(
            "whiscode.recording_overlay.cleanup_orphan_helpers",
            return_value=OverlayCleanupResult(0, 0, 0),
        ),
    ):
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
    with (
        patch("subprocess.Popen", side_effect=OSError("missing appkit")),
        patch(
            "whiscode.recording_overlay.cleanup_orphan_helpers",
            return_value=OverlayCleanupResult(0, 0, 0),
        ),
    ):
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

    with (
        patch("subprocess.Popen", return_value=process),
        patch(
            "whiscode.recording_overlay.cleanup_orphan_helpers",
            return_value=OverlayCleanupResult(0, 0, 0),
        ),
    ):
        client = RecordingOverlayClient(telemetry=telemetry)
        client.show()

    assert client.enabled is False
    assert client._visible is False
    assert sent_commands(process) == []
    assert ("recording_overlay.disabled", {"reason": "helper_exited", "stage": "show_recording", "returncode": -5}) in telemetry.events
    assert "recording overlay disabled: reason=helper_exited stage=show_recording returncode=-5" in capsys.readouterr().err


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


def test_overlay_client_launch_cleans_orphans_once():
    process = make_process()
    telemetry = FakeTelemetry()

    with (
        patch("subprocess.Popen", return_value=process),
        patch(
            "whiscode.recording_overlay.cleanup_orphan_helpers",
            return_value=OverlayCleanupResult(found_count=2, terminated_count=2, failed_count=0),
        ) as cleanup,
    ):
        client = RecordingOverlayClient(telemetry=telemetry)
        client.show()
        client.hide()
        client.show()

    cleanup.assert_called_once()
    assert (
        "recording_overlay.orphan_cleanup",
        {"found_count": 2, "terminated_count": 2, "failed_count": 0},
    ) in telemetry.events


def test_watch_parent_schedules_stop_when_parent_disappears():
    controller = Mock()
    calls = []

    _watch_parent(
        123,
        controller,
        lambda fn, command: calls.append((fn, command)),
        process_exists=lambda pid: False,
        sleep=lambda interval: (_ for _ in ()).throw(AssertionError("slept")),
    )

    assert calls == [(controller.handle, {"command": "stop"})]


def test_parse_overlay_helper_processes_finds_helper_commands():
    output = """
      111     1 /usr/bin/python -m whiscode.recording_overlay --helper --parent-pid 10
      222    10 /usr/bin/python -m whiscode.recording_overlay --helper --parent-pid 10
      333     1 /usr/bin/python -m whiscode.recording_overlay --cleanup-orphans
      444     1 /usr/bin/python other.py
    """

    processes = _parse_overlay_helper_processes(output)

    assert processes == [
        OverlayHelperProcess(
            111,
            1,
            "/usr/bin/python -m whiscode.recording_overlay --helper --parent-pid 10",
        ),
        OverlayHelperProcess(
            222,
            10,
            "/usr/bin/python -m whiscode.recording_overlay --helper --parent-pid 10",
        ),
    ]


def test_cleanup_orphan_helpers_skips_active_helpers():
    processes = [
        OverlayHelperProcess(111, 1, "python -m whiscode.recording_overlay --helper"),
        OverlayHelperProcess(222, 123, "python -m whiscode.recording_overlay --helper"),
    ]

    with patch("whiscode.recording_overlay.os.kill") as kill:
        kill.side_effect = [None, ProcessLookupError()]
        result = cleanup_orphan_helpers(processes=processes)

    assert result == OverlayCleanupResult(found_count=1, terminated_count=1, failed_count=0)
    assert kill.call_args_list == [
        ((111, signal.SIGTERM),),
        ((111, 0),),
    ]


def test_cleanup_orphan_helpers_counts_permission_failures():
    processes = [OverlayHelperProcess(111, 1, "python -m whiscode.recording_overlay --helper")]

    with patch("whiscode.recording_overlay.os.kill", side_effect=PermissionError):
        result = cleanup_orphan_helpers(processes=processes)

    assert result == OverlayCleanupResult(found_count=1, terminated_count=0, failed_count=1)


def test_cleanup_orphan_helpers_reports_process_listing_failure():
    with patch("whiscode.recording_overlay.overlay_helper_processes", side_effect=OSError):
        result = cleanup_orphan_helpers()

    assert result == OverlayCleanupResult(found_count=0, terminated_count=0, failed_count=1)


def test_cleanup_orphans_cli_prints_counts(capsys):
    with patch(
        "whiscode.recording_overlay.cleanup_orphan_helpers",
        return_value=OverlayCleanupResult(found_count=1, terminated_count=1, failed_count=0),
    ):
        result = main(["--cleanup-orphans"])

    assert result == 0
    assert json.loads(capsys.readouterr().out) == {
        "found_count": 1,
        "terminated_count": 1,
        "failed_count": 0,
    }
