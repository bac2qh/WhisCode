from __future__ import annotations

import argparse
import json
import math
import os
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

import numpy as np

LEGACY_OVERLAY_ITEM_ID = "legacy"


@dataclass(frozen=True)
class OverlayHelperProcess:
    pid: int
    ppid: int
    command: str


@dataclass(frozen=True)
class OverlayCleanupResult:
    found_count: int
    terminated_count: int
    failed_count: int


class RecordingOverlayClient:
    def __init__(
        self,
        *,
        enabled: bool = True,
        update_interval: float = 0.08,
        stop_timeout: float = 1.0,
        telemetry: Any | None = None,
    ):
        self.enabled = enabled
        self.update_interval = update_interval
        self.stop_timeout = stop_timeout
        self.telemetry = telemetry
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._cleanup_ran = False
        self._latest_level = 0.0
        self._visible = False
        self._mode: str | None = None
        self._active_recording_item_id: str | None = None
        self._stop_event = threading.Event()
        self._sender_thread: threading.Thread | None = None

    def show(self) -> None:
        self.show_recording_item(LEGACY_OVERLAY_ITEM_ID)

    def show_recording_item(self, item_id: str) -> None:
        if not self.enabled:
            return
        if not self._ensure_process():
            return
        with self._lock:
            self._visible = True
            self._mode = "recording"
            self._active_recording_item_id = item_id
        if self._send({"command": "show_recording", "item_id": item_id}):
            self._ensure_sender_thread()

    def hide(self) -> None:
        self.remove_item(LEGACY_OVERLAY_ITEM_ID)

    def remove_item(self, item_id: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            if self._active_recording_item_id == item_id:
                self._active_recording_item_id = None
            if item_id == LEGACY_OVERLAY_ITEM_ID:
                self._visible = False
                self._mode = None
        self._send({"command": "remove_item", "item_id": item_id})

    def show_queued_item(self, item_id: str, *, audio_seconds: float | None = None) -> None:
        if not self.enabled:
            return
        if not self._ensure_process():
            return
        with self._lock:
            if self._active_recording_item_id == item_id:
                self._active_recording_item_id = None
            self._visible = True
        command: dict[str, Any] = {"command": "show_queued", "item_id": item_id}
        if audio_seconds is not None:
            command["audio_seconds"] = _nonnegative_float(audio_seconds)
        self._send(command)

    def show_transcribing(self, *, total_frames: int | None = None) -> None:
        self.show_transcribing_item(LEGACY_OVERLAY_ITEM_ID, total_frames=total_frames)

    def show_transcribing_item(
        self,
        item_id: str,
        *,
        total_frames: int | None = None,
        audio_seconds: float | None = None,
    ) -> None:
        if not self.enabled:
            return
        if not self._ensure_process():
            return
        with self._lock:
            self._visible = True
            self._mode = "transcribing"
            if self._active_recording_item_id == item_id:
                self._active_recording_item_id = None
        command: dict[str, Any] = {"command": "show_transcribing", "item_id": item_id}
        if total_frames is not None:
            command["total_frames"] = _nonnegative_int(total_frames)
        if audio_seconds is not None:
            command["audio_seconds"] = _nonnegative_float(audio_seconds)
        self._send(command)

    def update_transcription_progress(
        self,
        *,
        item_id: str | None = None,
        current_frames: int | None = None,
        total_frames: int | None = None,
        rate: float | None = None,
    ) -> None:
        if not self.enabled:
            return
        command: dict[str, Any] = {"command": "transcription_progress"}
        if item_id is not None:
            command["item_id"] = item_id
        if current_frames is not None:
            command["current_frames"] = _nonnegative_int(current_frames)
        if total_frames is not None:
            command["total_frames"] = _nonnegative_int(total_frames)
        if rate is not None:
            try:
                numeric_rate = float(rate)
            except (TypeError, ValueError):
                numeric_rate = None
            if numeric_rate is not None and math.isfinite(numeric_rate):
                command["rate"] = max(0.0, numeric_rate)
        self._send(command)

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
        with self._lock:
            self._visible = False
            self._mode = None
        self._stop_event.set()
        self._send({"command": "stop"})
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except OSError:
                pass
            else:
                try:
                    self._process.wait(timeout=self.stop_timeout)
                except subprocess.TimeoutExpired:
                    try:
                        self._process.kill()
                    except OSError:
                        pass
                    else:
                        try:
                            self._process.wait(timeout=self.stop_timeout)
                        except subprocess.TimeoutExpired:
                            pass
        self._process = None

    def _ensure_process(self) -> bool:
        if self._process and self._process.poll() is None:
            return True
        self._cleanup_orphan_helpers()
        try:
            self._process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "whiscode.recording_overlay",
                    "--helper",
                    "--parent-pid",
                    str(os.getpid()),
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            return True
        except OSError as e:
            self._disable("launch_failed", stage="start", error_type=type(e).__name__)
            return False

    def _cleanup_orphan_helpers(self) -> None:
        if self._cleanup_ran:
            return
        self._cleanup_ran = True
        result = cleanup_orphan_helpers()
        if result.found_count and self.telemetry:
            self.telemetry.emit(
                "recording_overlay.orphan_cleanup",
                found_count=result.found_count,
                terminated_count=result.terminated_count,
                failed_count=result.failed_count,
            )

    def _ensure_sender_thread(self) -> None:
        if self._sender_thread and self._sender_thread.is_alive():
            return
        self._stop_event.clear()
        self._sender_thread = threading.Thread(target=self._send_levels, daemon=True)
        self._sender_thread.start()

    def _send_levels(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                visible = self._visible
                mode = self._mode
                level = self._latest_level
                item_id = self._active_recording_item_id
            if visible and mode == "recording" and item_id is not None:
                self._send({"command": "level", "item_id": item_id, "level": level})
            time.sleep(self.update_interval)

    def _send(self, command: dict[str, Any]) -> bool:
        if not self._process or not self._process.stdin:
            return False
        returncode = self._process.poll()
        if returncode is not None:
            self._disable("helper_exited", stage=str(command.get("command", "unknown")), returncode=returncode)
            return False
        try:
            with self._send_lock:
                self._process.stdin.write(json.dumps(command, separators=(",", ":")) + "\n")
                self._process.stdin.flush()
            return True
        except (BrokenPipeError, OSError):
            self._disable("pipe_failed", stage=str(command.get("command", "unknown")))
            return False

    def _disable(
        self,
        reason: str,
        *,
        stage: str,
        returncode: int | None = None,
        error_type: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        self.enabled = False
        with self._lock:
            self._visible = False
            self._mode = None
        self._stop_event.set()
        properties = {"reason": reason, "stage": stage}
        if returncode is not None:
            properties["returncode"] = returncode
        if error_type is not None:
            properties["error_type"] = error_type
        if self.telemetry:
            self.telemetry.emit("recording_overlay.disabled", **properties)
        details = " ".join(f"{key}={value}" for key, value in properties.items())
        print(f"recording overlay disabled: {details}", file=sys.stderr)


def _audio_level(audio: np.ndarray) -> float:
    if len(audio) == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float32))))
    return min(1.0, rms / 0.08)


def _nonnegative_int(value: Any) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, numeric)


def _nonnegative_float(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(numeric):
        return 0.0
    return max(0.0, numeric)


def _draw_attributed_text(text: str, point: Any, attrs: dict[Any, Any], *, attributed_string_class=None) -> Any:
    if attributed_string_class is None:
        from AppKit import NSAttributedString

        attributed_string_class = NSAttributedString
    attributed = attributed_string_class.alloc().initWithString_attributes_(text, attrs)
    attributed.drawAtPoint_(point)
    return attributed


def _read_helper_commands(input_stream: Any, controller: Any, call_after: Any) -> None:
    for line in input_stream:
        try:
            command = json.loads(line)
        except json.JSONDecodeError:
            continue
        call_after(controller.handle, command)
    call_after(controller.handle, {"command": "stop"})


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _watch_parent(
    parent_pid: int,
    controller: Any,
    call_after: Any,
    *,
    interval: float = 0.5,
    process_exists=_process_exists,
    sleep=time.sleep,
) -> None:
    while True:
        if not process_exists(parent_pid):
            call_after(controller.handle, {"command": "stop"})
            return
        sleep(interval)


def _start_parent_watchdog(parent_pid: int | None, controller: Any, call_after: Any) -> threading.Thread | None:
    if parent_pid is None or parent_pid <= 0:
        return None
    thread = threading.Thread(
        target=_watch_parent,
        args=(parent_pid, controller, call_after),
        daemon=True,
    )
    thread.start()
    return thread


def _is_overlay_helper_command(command: str) -> bool:
    return (
        "whiscode.recording_overlay" in command
        and "--helper" in command
        and "--cleanup-orphans" not in command
    )


def _parse_overlay_helper_processes(ps_output: str) -> list[OverlayHelperProcess]:
    processes = []
    for line in ps_output.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(None, 2)
        if len(parts) != 3:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        command = parts[2]
        if _is_overlay_helper_command(command):
            processes.append(OverlayHelperProcess(pid, ppid, command))
    return processes


def overlay_helper_processes(*, ps_output: str | bytes | None = None) -> list[OverlayHelperProcess]:
    if ps_output is None:
        ps_output = subprocess.check_output(
            ["ps", "-axo", "pid=,ppid=,command="],
            stderr=subprocess.DEVNULL,
        )
    if isinstance(ps_output, bytes):
        ps_output = ps_output.decode("utf-8", errors="replace")
    return _parse_overlay_helper_processes(ps_output)


def cleanup_orphan_helpers(
    *,
    processes: list[OverlayHelperProcess] | None = None,
    terminate_timeout: float = 0.5,
    kill_timeout: float = 0.5,
) -> OverlayCleanupResult:
    if processes is None:
        try:
            processes = overlay_helper_processes()
        except (OSError, subprocess.SubprocessError):
            return OverlayCleanupResult(found_count=0, terminated_count=0, failed_count=1)

    orphans = [process for process in processes if process.ppid == 1 and process.pid != os.getpid()]
    terminated = 0
    failed = 0
    for process in orphans:
        try:
            os.kill(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            terminated += 1
            continue
        except PermissionError:
            failed += 1
            continue

        deadline = time.monotonic() + terminate_timeout
        while time.monotonic() < deadline:
            if not _process_exists(process.pid):
                terminated += 1
                break
            time.sleep(0.05)
        else:
            try:
                os.kill(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                terminated += 1
                continue
            except PermissionError:
                failed += 1
                continue
            kill_deadline = time.monotonic() + kill_timeout
            while time.monotonic() < kill_deadline:
                if not _process_exists(process.pid):
                    terminated += 1
                    break
                time.sleep(0.05)
            else:
                failed += 1
    return OverlayCleanupResult(
        found_count=len(orphans),
        terminated_count=terminated,
        failed_count=failed,
    )


def _run_helper(parent_pid: int | None = None) -> None:
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
            self.items = []
            self.setWantsLayer_(True)
            return self

        def showRecordingItem_(self, item_id):
            item = self._upsertItem_mode_(item_id, "recording")
            item["started_at"] = time.monotonic()
            item["levels"] = deque([0.0] * 28, maxlen=28)
            self.setNeedsDisplay_(True)

        def showQueuedItem_audioSeconds_(self, item_id, audio_seconds):
            item = self._upsertItem_mode_(item_id, "queued")
            item["audio_seconds"] = max(0.0, float(audio_seconds or 0.0))
            self.setNeedsDisplay_(True)

        def showTranscribingItem_total_audioSeconds_(self, item_id, total_frames, audio_seconds):
            item = self._upsertItem_mode_(item_id, "transcribing")
            item["started_at"] = time.monotonic()
            item["current_frames"] = 0
            item["total_frames"] = max(0, int(total_frames or 0))
            item["rate"] = 0.0
            item["audio_seconds"] = max(0.0, float(audio_seconds or 0.0))
            self.setNeedsDisplay_(True)

        def removeItem_(self, item_id):
            self.items = [item for item in self.items if item["id"] != item_id]
            self.setNeedsDisplay_(True)

        def setLevel_item_(self, level, item_id):
            item = self._findItem_(item_id)
            if item is None or item["mode"] != "recording":
                return
            item["levels"].append(float(max(0.0, min(1.0, level))))
            self.setNeedsDisplay_(True)

        def setTranscriptionProgress_total_rate_item_(self, current_frames, total_frames, rate, item_id):
            item = self._findItem_(item_id)
            if item is None or item["mode"] != "transcribing":
                return
            item["current_frames"] = max(0, int(current_frames or 0))
            if total_frames is not None:
                item["total_frames"] = max(0, int(total_frames or 0))
            item["rate"] = max(0.0, float(rate or 0.0))
            self.setNeedsDisplay_(True)

        def itemCount(self):
            return len(self.items)

        def _findItem_(self, item_id):
            for item in self.items:
                if item["id"] == item_id:
                    return item
            return None

        def _upsertItem_mode_(self, item_id, mode):
            item = self._findItem_(item_id)
            if item is None:
                item = {
                    "id": item_id,
                    "mode": mode,
                    "started_at": time.monotonic(),
                    "levels": deque([0.0] * 28, maxlen=28),
                    "current_frames": 0,
                    "total_frames": 0,
                    "rate": 0.0,
                    "audio_seconds": 0.0,
                }
                self.items.insert(0, item)
            else:
                item["mode"] = mode
            return item

        def drawRect_(self, rect):
            bounds = self.bounds()
            card_height = 46
            gap = 8
            top = bounds.size.height
            for index, item in enumerate(self.items):
                y = top - card_height - index * (card_height + gap)
                card = NSMakeRect(0, y, bounds.size.width, card_height)
                NSColor.colorWithCalibratedWhite_alpha_(0.08, 0.88).setFill()
                path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(card, 18, 18)
                path.fill()
                if item["mode"] == "transcribing":
                    self._drawTranscribingInRect_item_(card, item)
                elif item["mode"] == "queued":
                    self._drawQueuedInRect_item_(card, item)
                else:
                    self._drawRecordingInRect_item_(card, item)

        def _drawRecordingInRect_item_(self, card, item):
            NSColor.colorWithCalibratedRed_green_blue_alpha_(1.0, 0.22, 0.18, 1.0).setFill()
            NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(card.origin.x + 16, card.origin.y + 18, 10, 10)).fill()

            elapsed = max(0, int(time.monotonic() - item["started_at"]))
            minutes, seconds = divmod(elapsed, 60)
            text = f"{minutes:02d}:{seconds:02d}"
            attrs = {
                NSFontAttributeName: NSFont.monospacedDigitSystemFontOfSize_weight_(16, 0.3),
                NSForegroundColorAttributeName: NSColor.whiteColor(),
            }
            _draw_attributed_text(text, NSMakePoint(card.origin.x + 36, card.origin.y + 13), attrs)

            bar_x = card.origin.x + 92
            bar_width = 4
            gap = 3
            center_y = card.origin.y + 23
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.45, 0.85, 1.0, 0.95).setFill()
            for index, level in enumerate(item["levels"]):
                height = max(4, min(28, 4 + int(level * 28)))
                x = bar_x + index * (bar_width + gap)
                y = center_y - height / 2
                NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                    NSMakeRect(x, y, bar_width, height),
                    2,
                    2,
                ).fill()

        def _drawQueuedInRect_item_(self, card, item):
            NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.55).setFill()
            NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(card.origin.x + 16, card.origin.y + 18, 10, 10)).fill()

            audio_seconds = max(0.0, float(item.get("audio_seconds") or 0.0))
            text = f"Queued  {audio_seconds:.1f}s"
            attrs = {
                NSFontAttributeName: NSFont.monospacedDigitSystemFontOfSize_weight_(13, 0.3),
                NSForegroundColorAttributeName: NSColor.whiteColor(),
            }
            _draw_attributed_text(text, NSMakePoint(card.origin.x + 36, card.origin.y + 16), attrs)

        def _drawTranscribingInRect_item_(self, card, item):
            total = max(0, int(item["total_frames"] or 0))
            current = max(0, int(item["current_frames"] or 0))
            if total > 0:
                current = min(current, total)
                progress = min(1.0, current / total)
            else:
                elapsed = time.monotonic() - item["started_at"]
                progress = (math.sin(elapsed * 4.0) + 1.0) / 2.0

            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.45, 0.85, 1.0, 0.95).setFill()
            NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(card.origin.x + 16, card.origin.y + 18, 10, 10)).fill()

            percent = int(round(progress * 100)) if total > 0 else 0
            rate = int(round(float(item["rate"] or 0.0)))
            if total > 0 and rate > 0:
                text = f"Transcribing {percent:3d}%  {current}/{total}  {rate} fps"
            elif total > 0:
                text = f"Transcribing {percent:3d}%  {current}/{total}"
            else:
                text = "Transcribing"
            attrs = {
                NSFontAttributeName: NSFont.monospacedDigitSystemFontOfSize_weight_(12, 0.3),
                NSForegroundColorAttributeName: NSColor.whiteColor(),
            }
            _draw_attributed_text(text, NSMakePoint(card.origin.x + 36, card.origin.y + 24), attrs)

            track = NSMakeRect(card.origin.x + 36, card.origin.y + 11, 288, 7)
            NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.22).setFill()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(track, 3.5, 3.5).fill()

            fill_width = 288 * progress if total > 0 else 56
            fill_x = card.origin.x + 36 if total > 0 else card.origin.x + 36 + (288 - fill_width) * progress
            NSColor.colorWithCalibratedRed_green_blue_alpha_(0.45, 0.85, 1.0, 1.0).setFill()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(fill_x, card.origin.y + 11, fill_width, 7),
                3.5,
                3.5,
            ).fill()

    class OverlayController:
        def __init__(self):
            screen = NSScreen.mainScreen().visibleFrame()
            width = 360
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

        def _syncPanelFrame(self):
            count = max(1, int(self.view.itemCount()))
            width = 360
            card_height = 46
            gap = 8
            height = card_height * count + gap * max(0, count - 1)
            screen = NSScreen.mainScreen().visibleFrame()
            x = screen.origin.x + (screen.size.width - width) / 2
            y = screen.origin.y + screen.size.height - height - 24
            self.panel.setFrame_display_(NSMakeRect(x, y, width, height), True)
            self.view.setFrame_(NSMakeRect(0, 0, width, height))

        def handle(self, command):
            name = command.get("command")
            item_id = str(command.get("item_id") or LEGACY_OVERLAY_ITEM_ID)
            if name in {"show", "show_recording"}:
                self.view.showRecordingItem_(item_id)
                self._syncPanelFrame()
                self.panel.orderFrontRegardless()
            elif name == "show_queued":
                self.view.showQueuedItem_audioSeconds_(item_id, command.get("audio_seconds", 0.0))
                self._syncPanelFrame()
                self.panel.orderFrontRegardless()
            elif name == "show_transcribing":
                self.view.showTranscribingItem_total_audioSeconds_(
                    item_id,
                    command.get("total_frames", 0),
                    command.get("audio_seconds", 0.0),
                )
                self._syncPanelFrame()
                self.panel.orderFrontRegardless()
            elif name == "hide":
                self.view.removeItem_(item_id)
                if self.view.itemCount():
                    self._syncPanelFrame()
                else:
                    self.panel.orderOut_(None)
            elif name == "remove_item":
                self.view.removeItem_(item_id)
                if self.view.itemCount():
                    self._syncPanelFrame()
                else:
                    self.panel.orderOut_(None)
            elif name == "level":
                self.view.setLevel_item_(float(command.get("level", 0.0)), item_id)
            elif name == "transcription_progress":
                self.view.setTranscriptionProgress_total_rate_item_(
                    command.get("current_frames", 0),
                    command.get("total_frames"),
                    command.get("rate", 0.0),
                    item_id,
                )
            elif name == "stop":
                self.panel.orderOut_(None)
                NSApp.terminate_(None)

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    controller = OverlayController()
    _start_parent_watchdog(parent_pid, controller, AppHelper.callAfter)
    threading.Thread(
        target=_read_helper_commands,
        args=(sys.stdin, controller, AppHelper.callAfter),
        daemon=True,
    ).start()
    AppHelper.runEventLoop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--helper", action="store_true")
    parser.add_argument("--parent-pid", type=int, default=None)
    parser.add_argument("--cleanup-orphans", action="store_true")
    args = parser.parse_args(argv)
    if args.cleanup_orphans:
        result = cleanup_orphan_helpers()
        print(
            json.dumps(
                {
                    "found_count": result.found_count,
                    "terminated_count": result.terminated_count,
                    "failed_count": result.failed_count,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0 if result.failed_count == 0 else 1
    if args.helper:
        _run_helper(parent_pid=args.parent_pid)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
