import subprocess
import time

from pynput.keyboard import Controller, Key

_keyboard = Controller()


def type_text(text: str):
    # Save current clipboard
    try:
        original = subprocess.run(
            ["pbpaste"], capture_output=True, timeout=2
        ).stdout
    except Exception:
        original = None

    # Copy transcribed text to clipboard
    subprocess.run(
        ["pbcopy"], input=text.encode("utf-8"), timeout=2
    )

    # Paste via Cmd+V
    time.sleep(0.05)
    with _keyboard.pressed(Key.cmd):
        _keyboard.tap("v")
    time.sleep(0.05)

    # Restore original clipboard (best-effort)
    if original is not None:
        try:
            subprocess.run(
                ["pbcopy"], input=original, timeout=2
            )
        except Exception:
            pass
