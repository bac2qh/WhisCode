import time

from pynput.keyboard import Controller

_keyboard = Controller()


def type_text(text: str, delay: float = 0.01):
    for char in text:
        _keyboard.type(char)
        if delay > 0:
            time.sleep(delay)
