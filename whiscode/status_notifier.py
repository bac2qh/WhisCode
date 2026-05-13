import subprocess
import sys


def _quote_applescript(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def notify_status(message: str, title: str = "WhisCode") -> None:
    script = f"display notification {_quote_applescript(message)} with title {_quote_applescript(title)}"
    try:
        subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as e:
        print(f"  Warning: could not show status notification: {e}", file=sys.stderr)


def notify_recording_now() -> None:
    notify_status("Recording now")


def notify_recording_completed() -> None:
    notify_status("Recording completed")
