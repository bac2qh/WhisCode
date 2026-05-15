import pytest
from pynput.keyboard import Key

from whiscode import injector


class FakeKeyboard:
    def __init__(self):
        self.tapped = []
        self.events = []

    def tap(self, key):
        self.tapped.append(key)
        self.events.append(("tap", key))

    def pressed(self, key):
        keyboard = self

        class Pressed:
            def __enter__(self):
                keyboard.events.append(("press", key))

            def __exit__(self, exc_type, exc, tb):
                keyboard.events.append(("release", key))
                return False

        return Pressed()


def test_press_key_command_maps_slots_to_physical_keys(monkeypatch):
    keyboard = FakeKeyboard()
    monkeypatch.setattr(injector, "_keyboard", keyboard)

    injector.press_key_command("page-up")
    injector.press_key_command("page-down")
    injector.press_key_command("enter")
    injector.press_key_command("shift-enter")
    injector.press_key_command("shift-tab")

    assert keyboard.tapped == [Key.page_up, Key.page_down, Key.enter, Key.enter, Key.tab]
    assert keyboard.events == [
        ("tap", Key.page_up),
        ("tap", Key.page_down),
        ("tap", Key.enter),
        ("press", Key.shift),
        ("tap", Key.enter),
        ("release", Key.shift),
        ("press", Key.shift),
        ("tap", Key.tab),
        ("release", Key.shift),
    ]


def test_press_key_command_rejects_unknown_slot(monkeypatch):
    monkeypatch.setattr(injector, "_keyboard", FakeKeyboard())

    with pytest.raises(ValueError, match="Unknown key command"):
        injector.press_key_command("escape")
