import subprocess
import time
from dataclasses import dataclass
from typing import Any

from pynput.keyboard import Controller, Key

_keyboard = Controller()

KEY_COMMANDS = {
    "page-up": Key.page_up,
    "page-down": Key.page_down,
    "enter": Key.enter,
    "shift-enter": (Key.shift, Key.enter),
    "shift-tab": (Key.shift, Key.tab),
    "tab": Key.tab,
    "arrow-up": Key.up,
    "arrow-down": Key.down,
}

SCROLL_COMMANDS = {
    "scroll-up": ("older", 1),
    "scroll-down": ("newer", -1),
}


@dataclass(frozen=True)
class CommandInjection:
    command: str
    action: str
    direction: str | None = None
    pixel_amount: int | None = None


def type_text(text: str):
    # Copy transcribed text to clipboard
    subprocess.run(
        ["pbcopy"], input=text.encode("utf-8"), timeout=2
    )

    # Paste via Cmd+V
    time.sleep(0.05)
    with _keyboard.pressed(Key.cmd):
        _keyboard.tap("v")


def is_scroll_command(command: str) -> bool:
    return command in SCROLL_COMMANDS


def press_key_command(command: str, *, telemetry: Any | None = None) -> CommandInjection:
    if command in SCROLL_COMMANDS:
        return _scroll_command(command, telemetry=telemetry)

    try:
        key = KEY_COMMANDS[command]
    except KeyError as e:
        raise ValueError(f"Unknown key command: {command}") from e
    if isinstance(key, tuple):
        modifier, target = key
        with _keyboard.pressed(modifier):
            _keyboard.tap(target)
        return CommandInjection(command=command, action="key")
    _keyboard.tap(key)
    return CommandInjection(command=command, action="key")


def _scroll_command(command: str, *, telemetry: Any | None) -> CommandInjection:
    direction, multiplier = SCROLL_COMMANDS[command]
    pixel_amount = 0
    try:
        quartz = _load_quartz()
        pixel_amount = _main_display_half_height_pixels(quartz)
        event = quartz.CGEventCreateScrollWheelEvent(
            None,
            quartz.kCGScrollEventUnitPixel,
            1,
            multiplier * pixel_amount,
        )
        if event is None:
            raise RuntimeError("CGEventCreateScrollWheelEvent returned None")
        quartz.CGEventPost(quartz.kCGHIDEventTap, event)
    except Exception as e:
        _emit_scroll_telemetry(
            telemetry,
            "scroll_command.failed",
            command=command,
            direction=direction,
            pixel_amount=pixel_amount,
            outcome="failed",
            error_type=type(e).__name__,
        )
        raise

    _emit_scroll_telemetry(
        telemetry,
        "scroll_command.injected",
        command=command,
        direction=direction,
        pixel_amount=pixel_amount,
        outcome="scrolled",
    )
    return CommandInjection(command=command, action="scroll", direction=direction, pixel_amount=pixel_amount)


def _load_quartz():
    import Quartz

    return Quartz


def _main_display_half_height_pixels(quartz) -> int:
    display_id = quartz.CGMainDisplayID()
    bounds = quartz.CGDisplayBounds(display_id)
    height = _bounds_height(bounds)
    if height <= 0:
        raise RuntimeError(f"Invalid main display height: {height!r}")
    return max(1, int(round(height / 2)))


def _bounds_height(bounds) -> float:
    size = getattr(bounds, "size", None)
    if size is not None and hasattr(size, "height"):
        return float(size.height)

    try:
        if len(bounds) == 2:
            return float(bounds[1][1])
        if len(bounds) == 4:
            return float(bounds[3])
    except (TypeError, IndexError, ValueError):
        pass

    raise RuntimeError(f"Could not read main display height from bounds: {bounds!r}")


def _emit_scroll_telemetry(telemetry: Any | None, event: str, **properties) -> None:
    if telemetry:
        telemetry.emit(event, **properties)
