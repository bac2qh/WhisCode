import pytest
from pynput.keyboard import Key

from whiscode import injector


class FakeKeyboard:
    def __init__(self):
        self.tapped = []

    def tap(self, key):
        self.tapped.append(key)


def test_press_key_command_maps_slots_to_physical_keys(monkeypatch):
    keyboard = FakeKeyboard()
    monkeypatch.setattr(injector, "_keyboard", keyboard)

    injector.press_key_command("page-up")
    injector.press_key_command("page-down")
    injector.press_key_command("enter")

    assert keyboard.tapped == [Key.page_up, Key.page_down, Key.enter]


def test_press_key_command_rejects_unknown_slot(monkeypatch):
    monkeypatch.setattr(injector, "_keyboard", FakeKeyboard())

    with pytest.raises(ValueError, match="Unknown key command"):
        injector.press_key_command("escape")
