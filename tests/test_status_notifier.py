from unittest.mock import patch

from whiscode.status_notifier import (
    notify_recording_completed,
    notify_recording_now,
    notify_status,
)


def test_notify_recording_now_launches_osascript():
    with patch("subprocess.Popen") as mock_popen:
        notify_recording_now()

    args = mock_popen.call_args.args[0]
    assert args[0:2] == ["osascript", "-e"]
    assert 'display notification "Recording now" with title "WhisCode"' == args[2]


def test_notify_recording_completed_launches_osascript():
    with patch("subprocess.Popen") as mock_popen:
        notify_recording_completed()

    args = mock_popen.call_args.args[0]
    assert args[0:2] == ["osascript", "-e"]
    assert 'display notification "Recording completed" with title "WhisCode"' == args[2]


def test_notify_status_escapes_applescript_strings():
    with patch("subprocess.Popen") as mock_popen:
        notify_status('Recording "quoted" \\ path', title='WhisCode "local"')

    args = mock_popen.call_args.args[0]
    assert args[2] == (
        'display notification "Recording \\"quoted\\" \\\\ path" '
        'with title "WhisCode \\"local\\""'
    )


def test_notify_status_handles_launch_failure(capsys):
    with patch("subprocess.Popen", side_effect=OSError("missing osascript")):
        notify_status("Recording now")

    captured = capsys.readouterr()
    assert "could not show status notification" in captured.err
    assert "missing osascript" in captured.err
