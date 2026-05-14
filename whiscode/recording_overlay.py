from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import threading
import time
from collections import deque
from typing import Any

import numpy as np


class RecordingOverlayClient:
    def __init__(self, *, enabled: bool = True, update_interval: float = 0.08):
        self.enabled = enabled
        self.update_interval = update_interval
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._latest_level = 0.0
        self._visible = False
        self._stop_event = threading.Event()
        self._sender_thread: threading.Thread | None = None

    def show(self) -> None:
        if not self.enabled:
            return
        if not self._ensure_process():
            return
        self._visible = True
        self._send({"command": "show"})
        self._ensure_sender_thread()

    def hide(self) -> None:
        if not self.enabled:
            return
        self._visible = False
        self._send({"command": "hide"})

    def update_level(self, audio_or_level: Any) -> None:
        if not self.enabled:
            return
        if isinstance(audio_or_level, (int, float)):
            level = float(audio_or_level)
        else:
            audio = np.asarray(audio_or_level, dtype=np.float32).flatten()
            level = _audio_level(audio)
        with self._lock:
            self._latest_level = max(0.0, min(1.0, level))

    def stop(self) -> None:
        self._visible = False
        self._stop_event.set()
        self._send({"command": "stop"})
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except OSError:
                pass
        self._process = None

    def _ensure_process(self) -> bool:
        if self._process and self._process.poll() is None:
            return True
        try:
            self._process = subprocess.Popen(
                [sys.executable, "-m", "whiscode.recording_overlay", "--helper"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            return True
        except OSError:
            self.enabled = False
            return False

    def _ensure_sender_thread(self) -> None:
        if self._sender_thread and self._sender_thread.is_alive():
            return
        self._stop_event.clear()
        self._sender_thread = threading.Thread(target=self._send_levels, daemon=True)
        self._sender_thread.start()

    def _send_levels(self) -> None:
        while not self._stop_event.is_set():
            if self._visible:
                with self._lock:
                    level = self._latest_level
                self._send({"command": "level", "level": level})
            time.sleep(self.update_interval)

    def _send(self, command: dict[str, Any]) -> None:
        if not self._process or not self._process.stdin or self._process.poll() is not None:
            return
        try:
            self._process.stdin.write(json.dumps(command, separators=(",", ":")) + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError):
            self.enabled = False


def _audio_level(audio: np.ndarray) -> float:
    if len(audio) == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float32))))
    return min(1.0, rms / 0.08)


def _run_helper() -> None:
    from AppKit import (
        NSApp,
        NSApplication,
        NSApplicationActivationPolicyAccessory,
        NSBackingStoreBuffered,
        NSBezierPath,
        NSColor,
        NSFont,
        NSFontAttributeName,
        NSMakeRect,
        NSPanel,
        NSForegroundColorAttributeName,
        NSView,
        NSWindowCollectionBehaviorCanJoinAllSpaces,
        NSWindowCollectionBehaviorFullScreenAuxiliary,
        NSWindowStyleMaskBorderless,
        NSWindowStyleMaskNonactivatingPanel,
        NSFloatingWindowLevel,
        NSScreen,
    )
    from Foundation import NSMakePoint
    from PyObjCTools import AppHelper
    import objc

    class OverlayView(NSView):
        def initWithFrame_(self, frame):
            self = objc.super(OverlayView, self).initWithFrame_(frame)
            if self is None:
                return None
            self.started_at = None
            self.levels = deque([0.0] * 28, maxlen=28)
            self.setWantsLayer_(True)
            return self

        def showRecording(self):
            self.started_at = time.monotonic()
            self.levels.clear()
            self.levels.extend([0.0] * 28)
            self.setNeedsDisplay_(True)

        def hideRecording(self):
            self.started_at = None
            self.setNeedsDisplay_(True)

        def setLevel_(self, level):
            self.levels.append(float(max(0.0, min(1.0, level))))
            self.setNeedsDisplay_(True)

        def drawRect_(self, rect):
            bounds = self.bounds()
            NSColor.colorWithCalibratedWhite_alpha_(0.08, 0.88).setFill()
            path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bounds, 18, 18)
            path.fill()

            NSColor.colorWithCalibratedRed_green_blue_alpha_(1.0, 0.22, 0.18, 1.0).setFill()
            NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(16, 18, 10, 10)).fill()

            elapsed = 0 if self.started_at is None else max(0, int(time.monotonic() - self.started_at))
            minutes, seconds = divmod(elapsed, 60)
            text = f"{minutes:02d}:{seconds:02d}"
            attrs = {
                NSFontAttributeName: NSFont.monospacedDigitSystemFontOfSize_weight_(16, 0.3),
                NSForegroundColorAttributeName: NSColor.whiteColor(),
            }
            text.drawAtPoint_withAttributes_(NSMakePoint(36, 13), attrs)

            bar_x = 92
            bar_width = 4
            gap = 3
            center_y = 23
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.45, 0.85, 1.0, 0.95).setFill()
            for index, level in enumerate(self.levels):
                height = max(4, min(28, 4 + int(level * 28)))
                x = bar_x + index * (bar_width + gap)
                y = center_y - height / 2
                NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                    NSMakeRect(x, y, bar_width, height),
                    2,
                    2,
                ).fill()

    class OverlayController:
        def __init__(self):
            screen = NSScreen.mainScreen().visibleFrame()
            width = 310
            height = 46
            x = screen.origin.x + (screen.size.width - width) / 2
            y = screen.origin.y + screen.size.height - height - 24
            frame = NSMakeRect(x, y, width, height)
            self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
                frame,
                NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
                NSBackingStoreBuffered,
                False,
            )
            self.panel.setLevel_(NSFloatingWindowLevel)
            self.panel.setOpaque_(False)
            self.panel.setBackgroundColor_(NSColor.clearColor())
            self.panel.setIgnoresMouseEvents_(True)
            self.panel.setCollectionBehavior_(
                NSWindowCollectionBehaviorCanJoinAllSpaces
                | NSWindowCollectionBehaviorFullScreenAuxiliary
            )
            self.view = OverlayView.alloc().initWithFrame_(NSMakeRect(0, 0, width, height))
            self.panel.setContentView_(self.view)

        def handle(self, command):
            name = command.get("command")
            if name == "show":
                self.view.showRecording()
                self.panel.orderFrontRegardless()
            elif name == "hide":
                self.view.hideRecording()
                self.panel.orderOut_(None)
            elif name == "level":
                self.view.setLevel_(float(command.get("level", 0.0)))
            elif name == "stop":
                self.panel.orderOut_(None)
                NSApp.terminate_(None)

    def read_commands(controller):
        for line in sys.stdin:
            try:
                command = json.loads(line)
            except json.JSONDecodeError:
                continue
            AppHelper.callAfter(controller.handle, command)

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    controller = OverlayController()
    threading.Thread(target=read_commands, args=(controller,), daemon=True).start()
    AppHelper.runEventLoop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--helper", action="store_true")
    args = parser.parse_args(argv)
    if args.helper:
        _run_helper()
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
