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


class FakeTelemetry:
    def __init__(self):
        self.events = []

    def emit(self, event, **properties):
        self.events.append((event, properties))


class FakeQuartz:
    kCGScrollEventUnitPixel = "pixel"
    kCGHIDEventTap = "hid"

    def __init__(self, *, height=1200, fail_post=False, event_prefix="event"):
        self.height = height
        self.fail_post = fail_post
        self.event_prefix = event_prefix
        self.created = []
        self.posted = []

    def CGMainDisplayID(self):
        return "main"

    def CGDisplayBounds(self, display_id):
        assert display_id == "main"
        return ((0, 0), (800, self.height))

    def CGEventCreateScrollWheelEvent(self, source, unit, wheel_count, wheel_1):
        event = f"{self.event_prefix}-{len(self.created) + 1}"
        self.created.append((source, unit, wheel_count, wheel_1, event))
        return event

    def CGEventPost(self, tap, event):
        if self.fail_post:
            raise RuntimeError("post failed")
        self.posted.append((tap, event))


def test_press_key_command_maps_slots_to_physical_keys(monkeypatch):
    keyboard = FakeKeyboard()
    monkeypatch.setattr(injector, "_keyboard", keyboard)

    injector.press_key_command("page-up")
    injector.press_key_command("page-down")
    injector.press_key_command("enter")
    injector.press_key_command("shift-enter")
    injector.press_key_command("shift-tab")
    injector.press_key_command("tab")
    injector.press_key_command("arrow-up")
    injector.press_key_command("arrow-down")

    assert keyboard.tapped == [
        Key.page_up,
        Key.page_down,
        Key.enter,
        Key.enter,
        Key.tab,
        Key.tab,
        Key.up,
        Key.down,
    ]
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
        ("tap", Key.tab),
        ("tap", Key.up),
        ("tap", Key.down),
    ]


def test_press_key_command_rejects_unknown_slot(monkeypatch):
    monkeypatch.setattr(injector, "_keyboard", FakeKeyboard())

    with pytest.raises(ValueError, match="Unknown key command"):
        injector.press_key_command("escape")


def test_press_key_command_scrolls_half_display_with_quartz(monkeypatch):
    fake_quartz = FakeQuartz(height=1000)
    telemetry = FakeTelemetry()
    monkeypatch.setattr(injector, "_load_quartz", lambda: fake_quartz)

    up = injector.press_key_command("scroll-up", telemetry=telemetry)
    down = injector.press_key_command("scroll-down", telemetry=telemetry)

    assert up.action == "scroll"
    assert up.direction == "older"
    assert up.pixel_amount == 500
    assert down.action == "scroll"
    assert down.direction == "newer"
    assert down.pixel_amount == 500
    assert fake_quartz.created == [
        (None, "pixel", 1, 500, "event-1"),
        (None, "pixel", 1, -500, "event-2"),
    ]
    assert fake_quartz.posted == [("hid", "event-1"), ("hid", "event-2")]
    assert telemetry.events == [
        (
            "scroll_command.injected",
            {"command": "scroll-up", "direction": "older", "pixel_amount": 500, "outcome": "scrolled"},
        ),
        (
            "scroll_command.injected",
            {"command": "scroll-down", "direction": "newer", "pixel_amount": 500, "outcome": "scrolled"},
        ),
    ]


def test_press_key_command_scroll_failure_emits_bounded_telemetry(monkeypatch):
    fake_quartz = FakeQuartz(height=800, fail_post=True)
    telemetry = FakeTelemetry()
    monkeypatch.setattr(injector, "_load_quartz", lambda: fake_quartz)

    with pytest.raises(RuntimeError, match="post failed"):
        injector.press_key_command("scroll-up", telemetry=telemetry)

    assert telemetry.events == [
        (
            "scroll_command.failed",
            {
                "command": "scroll-up",
                "direction": "older",
                "pixel_amount": 400,
                "outcome": "failed",
                "error_type": "RuntimeError",
            },
        )
    ]
