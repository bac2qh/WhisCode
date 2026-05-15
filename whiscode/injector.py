import subprocess
import time

from pynput.keyboard import Controller, Key

_keyboard = Controller()

KEY_COMMANDS = {
    "page-up": Key.page_up,
    "page-down": Key.page_down,
    "enter": Key.enter,
}


def type_text(text: str):
    # Copy transcribed text to clipboard
    subprocess.run(
        ["pbcopy"], input=text.encode("utf-8"), timeout=2
    )

    # Paste via Cmd+V
    time.sleep(0.05)
    with _keyboard.pressed(Key.cmd):
        _keyboard.tap("v")


def press_key_command(command: str) -> None:
    try:
        key = KEY_COMMANDS[command]
    except KeyError as e:
        raise ValueError(f"Unknown key command: {command}") from e
    _keyboard.tap(key)
