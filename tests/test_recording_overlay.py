import io
import json
from unittest.mock import Mock, patch

import numpy as np

from whiscode.recording_overlay import RecordingOverlayClient


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


def test_overlay_client_update_level_clamps_audio_level():
    client = RecordingOverlayClient()

    client.update_level(np.array([0.0, 1.0], dtype=np.float32))

    assert client._latest_level == 1.0


def test_overlay_client_disables_when_helper_fails_to_start():
    with patch("subprocess.Popen", side_effect=OSError("missing appkit")):
        client = RecordingOverlayClient()
        client.show()

    assert client.enabled is False
