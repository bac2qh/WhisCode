import subprocess
import time

from pynput.keyboard import Controller, Key

_keyboard = Controller()


def type_text(text: str):
    # Copy transcribed text to clipboard
    subprocess.run(
        ["pbcopy"], input=text.encode("utf-8"), timeout=2
    )

    # Paste via Cmd+V
    time.sleep(0.05)
    with _keyboard.pressed(Key.cmd):
        _keyboard.tap("v")
