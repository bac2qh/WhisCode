from __future__ import annotations

import configparser
import queue
import sys
import threading
import time
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Any, Callable, Protocol

import numpy as np

from whiscode.recorder import SAMPLE_RATE, _resample, open_input_stream

DEFAULT_WAKE_DIR = Path.home() / ".config" / "whiscode" / "wake" / "wake"
DEFAULT_END_DIR = Path.home() / ".config" / "whiscode" / "wake" / "end"
DEFAULT_COMMAND_DIR = Path.home() / ".config" / "whiscode" / "wake" / "commands"
DEFAULT_COMMAND_CONFIG_PATH = Path.home() / ".config" / "whiscode" / "commands.ini"
DEFAULT_THRESHOLD = 0.055
DEFAULT_WAKE_CONFIRMATIONS = 2
DEFAULT_COMMAND_THRESHOLD = DEFAULT_THRESHOLD
DEFAULT_COMMAND_CONFIRMATIONS = DEFAULT_WAKE_CONFIRMATIONS
DEFAULT_WINDOW_SECONDS = 2.0
DEFAULT_SLIDE_SECONDS = 0.25
DEFAULT_TAIL_SECONDS = 1.0
DEFAULT_MAX_SECONDS = 600.0
DEFAULT_AUDIO_QUEUE_SECONDS = 10.0
DEFAULT_MIN_RMS = 0.006
DEFAULT_MIN_ACTIVE_RATIO = 0.05
DEFAULT_ACTIVE_LEVEL = 0.01
DEFAULT_END_THRESHOLD = 0.055
MIN_REFERENCE_FILES = 3


@dataclass(frozen=True)
class CommandSlot:
    name: str
    label: str
    path: Path


COMMAND_SLOTS = (
    CommandSlot("page-up", "Page Up", DEFAULT_COMMAND_DIR / "page-up"),
    CommandSlot("page-down", "Page Down", DEFAULT_COMMAND_DIR / "page-down"),
    CommandSlot("enter", "Enter", DEFAULT_COMMAND_DIR / "enter"),
    CommandSlot("shift-enter", "Shift+Enter", DEFAULT_COMMAND_DIR / "shift-enter"),
    CommandSlot("shift-tab", "Shift+Tab", DEFAULT_COMMAND_DIR / "shift-tab"),
    CommandSlot("tab", "Tab", DEFAULT_COMMAND_DIR / "tab"),
    CommandSlot("arrow-up", "Arrow Up", DEFAULT_COMMAND_DIR / "arrow-up"),
    CommandSlot("arrow-down", "Arrow Down", DEFAULT_COMMAND_DIR / "arrow-down"),
)


class CommandConfigError(ValueError):
    pass


def command_slots_for_base(
    base_dir: Path = DEFAULT_COMMAND_DIR,
    *,
    slots: tuple[CommandSlot, ...] = COMMAND_SLOTS,
) -> tuple[CommandSlot, ...]:
    base = Path(base_dir)
    return tuple(CommandSlot(slot.name, slot.label, base / slot.name) for slot in slots)


def command_reference_dirs(
    base_dir: Path = DEFAULT_COMMAND_DIR,
    *,
    slots: tuple[CommandSlot, ...] = COMMAND_SLOTS,
) -> dict[str, Path]:
    base = Path(base_dir)
    return {slot.name: base / slot.name for slot in slots}


def active_command_slots(
    config_path: Path | None = DEFAULT_COMMAND_CONFIG_PATH,
    *,
    base_dir: Path = DEFAULT_COMMAND_DIR,
) -> tuple[CommandSlot, ...]:
    configured = load_command_config(config_path)
    if configured is None:
        return command_slots_for_base(base_dir)
    enabled = tuple(slot for slot in COMMAND_SLOTS if configured.get(slot.name, False))
    return command_slots_for_base(base_dir, slots=enabled)


def load_command_config(config_path: Path | None = DEFAULT_COMMAND_CONFIG_PATH) -> dict[str, bool] | None:
    if config_path is None:
        return None
    path = Path(config_path)
    if not path.exists():
        return None

    parser = configparser.ConfigParser()
    try:
        with path.open() as f:
            parser.read_file(f)
    except configparser.Error as e:
        raise CommandConfigError(f"Invalid command config {path}: {e}") from e

    if not parser.has_section("commands"):
        raise CommandConfigError(f"Command config {path} is missing a [commands] section.")

    valid_names = {slot.name for slot in COMMAND_SLOTS}
    configured_names = set(parser.options("commands"))
    unknown = sorted(configured_names - valid_names)
    if unknown:
        valid = ", ".join(slot.name for slot in COMMAND_SLOTS)
        raise CommandConfigError(
            f"Unknown command name(s) in {path}: {', '.join(unknown)}. Valid commands: {valid}"
        )

    enabled: dict[str, bool] = {}
    for slot in COMMAND_SLOTS:
        if parser.has_option("commands", slot.name):
            try:
                enabled[slot.name] = parser.getboolean("commands", slot.name)
            except ValueError as e:
                raise CommandConfigError(
                    f"Invalid boolean for command {slot.name} in {path}: {parser.get('commands', slot.name)!r}"
                ) from e
        else:
            enabled[slot.name] = False
    return enabled


def command_label(name: str) -> str:
    for slot in COMMAND_SLOTS:
        if slot.name == name:
            return slot.label
    return name


def reference_sample_count(path: Path) -> int:
    return len(list(Path(path).glob("*.wav"))) if Path(path).exists() else 0


def missing_reference_messages(
    wake_dir: Path,
    end_dir: Path,
    minimum: int = MIN_REFERENCE_FILES,
    *,
    command_dirs: dict[str, Path] | None = None,
) -> list[str]:
    messages = []
    for label, path in (("wake", wake_dir), ("end", end_dir)):
        count = reference_sample_count(path)
        if count < minimum:
            messages.append(f"{label}: {count}/{minimum} WAV samples in {path}")
    if command_dirs:
        for name, path in command_dirs.items():
            count = reference_sample_count(path)
            if count < minimum:
                messages.append(f"command {name}: {count}/{minimum} WAV samples in {path}")
    return messages


@dataclass(frozen=True)
class Detection:
    name: str
    distance: float
    rms: float | None = None
    active_ratio: float | None = None


@dataclass(frozen=True)
class HandsFreeEvent:
    kind: str
    audio: np.ndarray | None = None
    detection: Detection | None = None
    duration_seconds: float = 0.0
    command: str | None = None


@dataclass(frozen=True)
class AudioChunk:
    audio: np.ndarray
    sample_rate: int


class Detector(Protocol):
    last_distance: float | None

    def detect(self, audio: np.ndarray) -> Detection | None:
        ...


class LocalWakeDetector:
    def __init__(self, support_dir: Path, threshold: float, method: str = "embedding"):
        self.support_dir = Path(support_dir)
        self.threshold = threshold
        self.method = method
        self.last_distance: float | None = None

        if not self.support_dir.exists():
            raise ValueError(f"Reference folder does not exist: {self.support_dir}")

        wavs = sorted(self.support_dir.glob("*.wav"))
        if len(wavs) < MIN_REFERENCE_FILES:
            raise ValueError(
                f"Reference folder {self.support_dir} needs at least "
                f"{MIN_REFERENCE_FILES} WAV samples; found {len(wavs)}."
            )

        from lwake.listen import load_support_set

        self.support_set = load_support_set(str(self.support_dir), method=method)
        if len(self.support_set) < MIN_REFERENCE_FILES:
            raise ValueError(
                f"Reference folder {self.support_dir} needs at least "
                f"{MIN_REFERENCE_FILES} valid WAV samples; loaded {len(self.support_set)}."
            )

    def detect(self, audio: np.ndarray) -> Detection | None:
        from lwake.features import (
            dtw_cosine_normalized_distance,
            extract_embedding_features,
            extract_mfcc_features,
        )

        if self.method == "mfcc":
            features = extract_mfcc_features(y=audio, sample_rate=SAMPLE_RATE)
        else:
            features = extract_embedding_features(y=audio, sample_rate=SAMPLE_RATE)

        best: Detection | None = None
        for filename, ref_features in self.support_set:
            distance = float(dtw_cosine_normalized_distance(features, ref_features))
            if best is None or distance < best.distance:
                best = Detection(filename, distance)

        self.last_distance = best.distance if best else None
        if best and best.distance < self.threshold:
            return best
        return None


class HandsFreeSession:
    def __init__(
        self,
        wake_detector: Detector,
        end_detector: Detector,
        *,
        sample_rate: int = SAMPLE_RATE,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        slide_seconds: float = DEFAULT_SLIDE_SECONDS,
        max_seconds: float = DEFAULT_MAX_SECONDS,
        tail_seconds: float | None = None,
        debug: bool = False,
        telemetry: Any | None = None,
        distance_summary_seconds: float = 5.0,
        min_rms: float = DEFAULT_MIN_RMS,
        min_active_ratio: float = DEFAULT_MIN_ACTIVE_RATIO,
        active_level: float = DEFAULT_ACTIVE_LEVEL,
        wake_confirmations: int = DEFAULT_WAKE_CONFIRMATIONS,
        command_detectors: dict[str, Detector] | None = None,
        command_confirmations: int = DEFAULT_COMMAND_CONFIRMATIONS,
        level_callback: Any | None = None,
    ):
        self.wake_detector = wake_detector
        self.end_detector = end_detector
        self.command_detectors = dict(command_detectors or {})
        self.sample_rate = sample_rate
        self.window_samples = max(1, int(window_seconds * sample_rate))
        self.slide_samples = max(1, int(slide_seconds * sample_rate))
        self.max_samples = int(max_seconds * sample_rate) if max_seconds > 0 else 0
        self.tail_samples = max(1, int((tail_seconds or DEFAULT_TAIL_SECONDS) * sample_rate))
        self.debug = debug
        self.telemetry = telemetry
        self.distance_summary_seconds = distance_summary_seconds
        self.min_rms = min_rms
        self.min_active_ratio = min_active_ratio
        self.active_level = active_level
        self.wake_confirmations = max(1, int(wake_confirmations))
        self.command_confirmations = max(1, int(command_confirmations))
        self.level_callback = level_callback

        self.state = "idle"
        self.suspended = False
        self._wake_buffer = np.zeros(self.window_samples, dtype=np.float32)
        self._end_buffer = np.zeros(self.window_samples, dtype=np.float32)
        self._pending_tail = np.array([], dtype=np.float32)
        self._captured: list[np.ndarray] = []
        self._recorded_samples = 0
        self._wake_filled_samples = 0
        self._end_filled_samples = 0
        self._wake_confirmation_count = 0
        self._end_confirmation_count = 0
        self._command_confirmation_counts = {name: 0 for name in self.command_detectors}
        self._distance_stats: dict[str, dict[str, float]] = {}
        self._gate_stats: dict[str, dict[str, float | str]] = {}
        self._last_distance_summary = time.monotonic()
        self._last_gate_summary = time.monotonic()

    def suspend(self) -> None:
        self.suspended = True
        self.reset_idle()
        self._emit("handsfree.session_suspended")

    def resume(self) -> None:
        self.suspended = False
        self.reset_idle()
        self._emit("handsfree.session_resumed")

    def reset_idle(self) -> None:
        self.state = "idle"
        self._wake_buffer = np.zeros(self.window_samples, dtype=np.float32)
        self._end_buffer = np.zeros(self.window_samples, dtype=np.float32)
        self._pending_tail = np.array([], dtype=np.float32)
        self._captured = []
        self._recorded_samples = 0
        self._wake_filled_samples = 0
        self._end_filled_samples = 0
        self._wake_confirmation_count = 0
        self._end_confirmation_count = 0
        self._command_confirmation_counts = {name: 0 for name in self.command_detectors}

    def manual_start(self) -> HandsFreeEvent:
        self._start_recording(source="manual")
        return HandsFreeEvent("manual.started")

    def manual_stop(self) -> HandsFreeEvent:
        return self._finish_recording("manual.stopped", include_pending=True)

    def feed(self, chunk: np.ndarray) -> list[HandsFreeEvent]:
        if self.suspended:
            return []
        chunk = np.asarray(chunk, dtype=np.float32).flatten()
        if len(chunk) == 0:
            return []

        if self.state == "idle":
            self._wake_buffer = _shift_append(self._wake_buffer, chunk)
            self._wake_filled_samples = min(self.window_samples, self._wake_filled_samples + len(chunk))
            detection = self._maybe_detect(self.wake_detector, self._wake_buffer, "wake", self._wake_filled_samples)
            if detection:
                detection = self._confirm_detection(detection, "wake", self.wake_confirmations)
                if detection:
                    self._start_recording(source="wake")
                    return [HandsFreeEvent("wake.detected", detection=detection)]
                return []
            self._confirm_detection(None, "wake", self.wake_confirmations)
            command_event = self._detect_command()
            if command_event:
                return [command_event]
            return []

        self._recorded_samples += len(chunk)
        self._emit_level(chunk)
        self._append_recording_chunk(chunk)
        self._end_buffer = _shift_append(self._end_buffer, chunk)
        self._end_filled_samples = min(self.window_samples, self._end_filled_samples + len(chunk))
        detection = self._maybe_detect(self.end_detector, self._end_buffer, "end", self._end_filled_samples)
        detection = self._confirm_detection(detection, "end", 1)
        if detection:
            event = self._finish_recording("end.detected", include_pending=False)
            return [HandsFreeEvent(event.kind, event.audio, detection, event.duration_seconds)]

        if self.max_samples and self._recorded_samples >= self.max_samples:
            return [self._finish_recording("timeout", include_pending=True)]

        return []

    def _maybe_detect(self, detector: Detector, audio: np.ndarray, label: str, filled_samples: int) -> Detection | None:
        if filled_samples < self.window_samples:
            self._record_gate_skip(label, "partial_window", filled_samples=filled_samples)
            return None

        rms, active_ratio = _audio_metrics(audio, self.active_level)
        if rms < self.min_rms:
            self._record_gate_skip(label, "low_rms", rms=rms, active_ratio=active_ratio, filled_samples=filled_samples)
            return None
        if active_ratio < self.min_active_ratio:
            self._record_gate_skip(label, "low_active_ratio", rms=rms, active_ratio=active_ratio, filled_samples=filled_samples)
            return None

        return self._detect(detector, audio, label, rms=rms, active_ratio=active_ratio)

    def _detect(self, detector: Detector, audio: np.ndarray, label: str, *, rms: float, active_ratio: float) -> Detection | None:
        try:
            detection = detector.detect(audio)
            if self.debug and detector.last_distance is not None:
                print(f"handsfree.{label}.distance={detector.last_distance:.4f}")
            if detector.last_distance is not None:
                self._record_distance(label, detector.last_distance, detected=detection is not None)
            if detection:
                return Detection(detection.name, detection.distance, rms=rms, active_ratio=active_ratio)
            return None
        except Exception as e:
            print(f"handsfree.detector.error detector={label} error={e}", file=sys.stderr)
            self._emit("handsfree.detector_error", detector=label, error_type=type(e).__name__)
            return None

    def _start_recording(self, *, source: str) -> None:
        self.state = "recording"
        self._end_buffer = np.zeros(self.window_samples, dtype=np.float32)
        self._pending_tail = np.array([], dtype=np.float32)
        self._captured = []
        self._recorded_samples = 0
        self._end_filled_samples = 0
        self._wake_confirmation_count = 0
        self._end_confirmation_count = 0
        self._command_confirmation_counts = {name: 0 for name in self.command_detectors}
        self._emit("handsfree.session_started_recording", source=source)

    def _detect_command(self) -> HandsFreeEvent | None:
        matches: list[tuple[str, Detection]] = []
        for name, detector in self.command_detectors.items():
            label = f"command.{name}"
            detection = self._maybe_detect(detector, self._wake_buffer, label, self._wake_filled_samples)
            if detection:
                matches.append((name, detection))
            else:
                self._command_confirmation_counts[name] = 0
        if not matches:
            return None

        name, detection = min(matches, key=lambda item: item[1].distance)
        for other_name in self.command_detectors:
            if other_name != name:
                self._command_confirmation_counts[other_name] = 0
        detection = self._confirm_command_detection(name, detection)
        if detection:
            event = HandsFreeEvent("command.detected", detection=detection, command=name)
            self.reset_idle()
            return event
        return None

    def _append_recording_chunk(self, chunk: np.ndarray) -> None:
        pending = np.concatenate([self._pending_tail, chunk])
        if len(pending) > self.tail_samples:
            split = len(pending) - self.tail_samples
            self._captured.append(pending[:split].copy())
            self._pending_tail = pending[split:].copy()
        else:
            self._pending_tail = pending

    def _finish_recording(self, kind: str, *, include_pending: bool) -> HandsFreeEvent:
        parts = list(self._captured)
        if include_pending and len(self._pending_tail):
            parts.append(self._pending_tail.copy())
        audio = np.concatenate(parts).astype(np.float32) if parts else np.array([], dtype=np.float32)
        duration = len(audio) / self.sample_rate
        self.reset_idle()
        self._emit(
            "handsfree.session_finished_recording",
            reason=kind,
            duration_seconds=round(duration, 3),
            audio_samples=len(audio),
            included_tail=include_pending,
        )
        return HandsFreeEvent(kind, audio=audio, duration_seconds=duration)

    def _record_distance(self, label: str, distance: float, *, detected: bool) -> None:
        stats = self._distance_stats.setdefault(
            label,
            {"count": 0.0, "min": distance, "max": distance, "total": 0.0, "last": distance, "detections": 0.0},
        )
        stats["count"] += 1
        stats["min"] = min(stats["min"], distance)
        stats["max"] = max(stats["max"], distance)
        stats["total"] += distance
        stats["last"] = distance
        if detected:
            stats["detections"] += 1

        now = time.monotonic()
        if now - self._last_distance_summary >= self.distance_summary_seconds:
            self._emit_distance_summary()
            self._last_distance_summary = now

    def _record_gate_skip(
        self,
        label: str,
        reason: str,
        *,
        rms: float | None = None,
        active_ratio: float | None = None,
        filled_samples: int,
    ) -> None:
        key = f"{label}:{reason}"
        stats = self._gate_stats.setdefault(
            key,
            {
                "detector": label,
                "reason": reason,
                "count": 0.0,
                "min_filled_samples": float(filled_samples),
                "max_filled_samples": float(filled_samples),
            },
        )
        stats["count"] = float(stats["count"]) + 1
        stats["min_filled_samples"] = min(float(stats["min_filled_samples"]), float(filled_samples))
        stats["max_filled_samples"] = max(float(stats["max_filled_samples"]), float(filled_samples))
        if rms is not None:
            _update_min_max(stats, "rms", rms)
        if active_ratio is not None:
            _update_min_max(stats, "active_ratio", active_ratio)

        now = time.monotonic()
        if stats["count"] == 1:
            self._emit_gate_summary(reset=False)
        elif now - self._last_gate_summary >= self.distance_summary_seconds:
            self._emit_gate_summary(reset=True)
            self._last_gate_summary = now

    def _emit_gate_summary(self, *, reset: bool) -> None:
        for stats in self._gate_stats.values():
            properties = {
                "detector": stats["detector"],
                "reason": stats["reason"],
                "count": int(float(stats["count"])),
                "min_filled_samples": int(float(stats["min_filled_samples"])),
                "max_filled_samples": int(float(stats["max_filled_samples"])),
                "window_samples": self.window_samples,
                "min_rms_threshold": self.min_rms,
                "min_active_ratio_threshold": self.min_active_ratio,
                "active_level": self.active_level,
            }
            for key in (
                "min_rms",
                "max_rms",
                "last_rms",
                "min_active_ratio",
                "max_active_ratio",
                "last_active_ratio",
            ):
                if key in stats:
                    properties[key] = round(float(stats[key]), 6)
            self._emit("handsfree.detector_gate_summary", **properties)
        if reset:
            self._gate_stats = {}

    def _emit_distance_summary(self) -> None:
        for label, stats in self._distance_stats.items():
            count = int(stats["count"])
            if count == 0:
                continue
            self._emit(
                "handsfree.detector_distance_summary",
                detector=label,
                count=count,
                min_distance=round(stats["min"], 6),
                max_distance=round(stats["max"], 6),
                avg_distance=round(stats["total"] / count, 6),
                last_distance=round(stats["last"], 6),
                detections=int(stats["detections"]),
            )
        self._distance_stats = {}

    def _emit(self, event: str, **properties) -> None:
        if self.telemetry:
            self.telemetry.emit(event, **properties)

    def _confirm_detection(self, detection: Detection | None, label: str, required: int) -> Detection | None:
        count_attr = f"_{_safe_label(label)}_confirmation_count"
        required = max(1, int(required))
        if detection is None:
            setattr(self, count_attr, 0)
            return None

        count = int(getattr(self, count_attr, 0)) + 1
        setattr(self, count_attr, count)
        if count < required:
            self._emit(
                "handsfree.detector_confirmation_pending",
                detector=label,
                count=count,
                required=required,
                distance=round(detection.distance, 6),
                rms=round(detection.rms, 6) if detection.rms is not None else None,
                active_ratio=round(detection.active_ratio, 6) if detection.active_ratio is not None else None,
            )
            return None

        setattr(self, count_attr, 0)
        if required > 1:
            self._emit(
                "handsfree.detector_confirmation_completed",
                detector=label,
                required=required,
                distance=round(detection.distance, 6),
                rms=round(detection.rms, 6) if detection.rms is not None else None,
                active_ratio=round(detection.active_ratio, 6) if detection.active_ratio is not None else None,
            )
        return detection

    def _confirm_command_detection(self, name: str, detection: Detection | None) -> Detection | None:
        required = self.command_confirmations
        detector_label = f"command.{name}"
        if detection is None:
            self._command_confirmation_counts[name] = 0
            return None

        count = int(self._command_confirmation_counts.get(name, 0)) + 1
        self._command_confirmation_counts[name] = count
        if count < required:
            self._emit(
                "handsfree.detector_confirmation_pending",
                detector=detector_label,
                command=name,
                count=count,
                required=required,
                distance=round(detection.distance, 6),
                rms=round(detection.rms, 6) if detection.rms is not None else None,
                active_ratio=round(detection.active_ratio, 6) if detection.active_ratio is not None else None,
            )
            return None

        self._command_confirmation_counts = {slot_name: 0 for slot_name in self.command_detectors}
        if required > 1:
            self._emit(
                "handsfree.detector_confirmation_completed",
                detector=detector_label,
                command=name,
                required=required,
                distance=round(detection.distance, 6),
                rms=round(detection.rms, 6) if detection.rms is not None else None,
                active_ratio=round(detection.active_ratio, 6) if detection.active_ratio is not None else None,
            )
        return detection

    def _emit_level(self, chunk: np.ndarray) -> None:
        if self.level_callback:
            self.level_callback(_level_from_audio(chunk))


class HandsFreeAudioLoop:
    def __init__(
        self,
        session: HandsFreeSession,
        event_queue: queue.Queue,
        *,
        stop_event: threading.Event,
        telemetry: Any | None = None,
        audio_queue_seconds: float = DEFAULT_AUDIO_QUEUE_SECONDS,
        stream_factory: Callable[[], tuple[Any, int]] = open_input_stream,
    ):
        self.session = session
        self.event_queue = event_queue
        self.stop_event = stop_event
        self.telemetry = telemetry
        self.audio_queue_seconds = max(0.0, float(audio_queue_seconds))
        max_chunks = max(1, ceil(self.audio_queue_seconds / (self.session.slide_samples / SAMPLE_RATE)))
        self._audio_queue: queue.Queue[AudioChunk] = queue.Queue(maxsize=max_chunks)
        self._stream_factory = stream_factory
        self._capture_thread: threading.Thread | None = None
        self._detector_thread: threading.Thread | None = None
        self._overflow_count = 0
        self._dropped_count = 0
        self._processed_count = 0
        self._processing_total_seconds = 0.0
        self._processing_max_seconds = 0.0
        self._last_queue_summary = time.monotonic()
        self._last_processing_summary = time.monotonic()
        self._stats_lock = threading.Lock()

    def start(self) -> None:
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._detector_thread = threading.Thread(target=self._detector_loop, daemon=True)
        self._detector_thread.start()
        self._capture_thread.start()

    def join(self, timeout: float | None = None) -> None:
        deadline = time.monotonic() + timeout if timeout is not None else None
        for thread in (self._capture_thread, self._detector_thread):
            if not thread:
                continue
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            thread.join(timeout=remaining)

    def _capture_loop(self) -> None:
        try:
            stream, actual_rate = self._stream_factory()
            slide_samples = max(1, int(self.session.slide_samples * actual_rate / SAMPLE_RATE))
            with stream:
                print(f"handsfree.started sample_rate={actual_rate}")
                self._emit(
                    "handsfree.audio_loop_started",
                    sample_rate=actual_rate,
                    slide_samples=slide_samples,
                    audio_queue_seconds=self.audio_queue_seconds,
                    audio_queue_max_chunks=self._audio_queue.maxsize,
                )
                while not self.stop_event.is_set():
                    data, overflowed = stream.read(slide_samples)
                    if overflowed:
                        with self._stats_lock:
                            self._overflow_count += 1
                            overflow_count = self._overflow_count
                        print("handsfree.audio.overflow", file=sys.stderr)
                        if overflow_count == 1 or overflow_count % 10 == 0:
                            self._emit("handsfree.audio_overflow", count=overflow_count)
                    chunk = np.asarray(data[:, 0], dtype=np.float32)
                    self._enqueue_audio_chunk(AudioChunk(chunk.copy(), actual_rate))
                    self._maybe_emit_queue_summary()
                self._emit_queue_summary(final=True)
                self._emit(
                    "handsfree.audio_loop_stopped",
                    overflow_count=self._overflow_count,
                    dropped_count=self._dropped_count,
                    queue_size=self._audio_queue.qsize(),
                )
        except Exception as e:
            self.event_queue.put(HandsFreeEvent("detector.error"))
            print(f"handsfree.audio_loop.error error={e}", file=sys.stderr)
            self._emit("handsfree.audio_loop_error", error_type=type(e).__name__)

    def _detector_loop(self) -> None:
        while not self.stop_event.is_set() or not self._audio_queue.empty():
            try:
                audio_chunk = self._audio_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            started = time.monotonic()
            try:
                chunk = audio_chunk.audio
                if audio_chunk.sample_rate != SAMPLE_RATE:
                    chunk = _resample(chunk, audio_chunk.sample_rate, SAMPLE_RATE)
                for event in self.session.feed(chunk):
                    self.event_queue.put(event)
            except Exception as e:
                self.event_queue.put(HandsFreeEvent("detector.error"))
                print(f"handsfree.detector.error error={e}", file=sys.stderr)
                self._emit("handsfree.audio_loop_error", error_type=type(e).__name__)
            finally:
                elapsed = time.monotonic() - started
                with self._stats_lock:
                    self._processed_count += 1
                    self._processing_total_seconds += elapsed
                    self._processing_max_seconds = max(self._processing_max_seconds, elapsed)
                self._audio_queue.task_done()
                self._maybe_emit_processing_summary()
        self._emit_processing_summary(final=True)

    def _enqueue_audio_chunk(self, audio_chunk: AudioChunk) -> None:
        try:
            self._audio_queue.put_nowait(audio_chunk)
            return
        except queue.Full:
            pass

        try:
            self._audio_queue.get_nowait()
            self._audio_queue.task_done()
        except queue.Empty:
            pass
        with self._stats_lock:
            self._dropped_count += 1
            dropped_count = self._dropped_count
        if dropped_count == 1 or dropped_count % 10 == 0:
            self._emit(
                "handsfree.audio_queue_dropped",
                count=dropped_count,
                queue_size=self._audio_queue.qsize(),
                queue_max_chunks=self._audio_queue.maxsize,
                audio_queue_seconds=self.audio_queue_seconds,
            )
        self._audio_queue.put_nowait(audio_chunk)

    def _maybe_emit_queue_summary(self) -> None:
        now = time.monotonic()
        if now - self._last_queue_summary < 5.0:
            return
        self._last_queue_summary = now
        self._emit_queue_summary(final=False)

    def _emit_queue_summary(self, *, final: bool) -> None:
        with self._stats_lock:
            overflow_count = self._overflow_count
            dropped_count = self._dropped_count
        self._emit(
            "handsfree.audio_queue_summary",
            final=final,
            queue_size=self._audio_queue.qsize(),
            queue_max_chunks=self._audio_queue.maxsize,
            audio_queue_seconds=self.audio_queue_seconds,
            overflow_count=overflow_count,
            dropped_count=dropped_count,
            session_state=self.session.state,
        )

    def _maybe_emit_processing_summary(self) -> None:
        now = time.monotonic()
        if now - self._last_processing_summary < 5.0:
            return
        self._last_processing_summary = now
        self._emit_processing_summary(final=False)

    def _emit_processing_summary(self, *, final: bool) -> None:
        with self._stats_lock:
            processed_count = self._processed_count
            total_seconds = self._processing_total_seconds
            max_seconds = self._processing_max_seconds
            self._processed_count = 0
            self._processing_total_seconds = 0.0
            self._processing_max_seconds = 0.0
        if processed_count == 0 and not final:
            return
        avg_seconds = total_seconds / processed_count if processed_count else 0.0
        self._emit(
            "handsfree.detector_processing_summary",
            final=final,
            chunks=processed_count,
            avg_seconds=round(avg_seconds, 6),
            max_seconds=round(max_seconds, 6),
            queue_size=self._audio_queue.qsize(),
            queue_max_chunks=self._audio_queue.maxsize,
            session_state=self.session.state,
        )

    def _emit(self, event: str, **properties) -> None:
        if self.telemetry:
            self.telemetry.emit(event, **properties)


def _shift_append(buffer: np.ndarray, chunk: np.ndarray) -> np.ndarray:
    if len(chunk) >= len(buffer):
        return chunk[-len(buffer):].astype(np.float32).copy()
    shifted = np.roll(buffer, -len(chunk))
    shifted[-len(chunk):] = chunk
    return shifted


def _audio_metrics(audio: np.ndarray, active_level: float) -> tuple[float, float]:
    if len(audio) == 0:
        return 0.0, 0.0
    rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float32))))
    active_ratio = float(np.mean(np.abs(audio) >= active_level))
    return rms, active_ratio


def _level_from_audio(audio: np.ndarray) -> float:
    rms, _ = _audio_metrics(audio, DEFAULT_ACTIVE_LEVEL)
    return min(1.0, rms / 0.08)


def _update_min_max(stats: dict[str, float | str], name: str, value: float) -> None:
    min_key = f"min_{name}"
    max_key = f"max_{name}"
    last_key = f"last_{name}"
    stats[min_key] = min(float(stats.get(min_key, value)), value)
    stats[max_key] = max(float(stats.get(max_key, value)), value)
    stats[last_key] = value


def _safe_label(label: str) -> str:
    return label.replace("-", "_").replace(".", "_")


def process_hands_free_events(
    event_queue: queue.Queue,
    session: HandsFreeSession,
    stop_event: threading.Event,
) -> HandsFreeEvent | None:
    while not stop_event.is_set():
        try:
            return event_queue.get(timeout=0.05)
        except queue.Empty:
            continue
    return None
