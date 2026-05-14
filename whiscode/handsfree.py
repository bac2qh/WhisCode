from __future__ import annotations

import queue
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from whiscode.recorder import SAMPLE_RATE, _resample, open_input_stream

DEFAULT_WAKE_DIR = Path.home() / ".config" / "whiscode" / "wake" / "wake"
DEFAULT_END_DIR = Path.home() / ".config" / "whiscode" / "wake" / "end"
DEFAULT_THRESHOLD = 0.1
DEFAULT_WINDOW_SECONDS = 2.0
DEFAULT_SLIDE_SECONDS = 0.25
DEFAULT_TAIL_SECONDS = 1.0
DEFAULT_MAX_SECONDS = 180.0
MIN_REFERENCE_FILES = 3


def reference_sample_count(path: Path) -> int:
    return len(list(Path(path).glob("*.wav"))) if Path(path).exists() else 0


def missing_reference_messages(wake_dir: Path, end_dir: Path, minimum: int = MIN_REFERENCE_FILES) -> list[str]:
    messages = []
    for label, path in (("wake", wake_dir), ("end", end_dir)):
        count = reference_sample_count(path)
        if count < minimum:
            messages.append(f"{label}: {count}/{minimum} WAV samples in {path}")
    return messages


@dataclass(frozen=True)
class Detection:
    name: str
    distance: float


@dataclass(frozen=True)
class HandsFreeEvent:
    kind: str
    audio: np.ndarray | None = None
    detection: Detection | None = None
    duration_seconds: float = 0.0


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
    ):
        self.wake_detector = wake_detector
        self.end_detector = end_detector
        self.sample_rate = sample_rate
        self.window_samples = max(1, int(window_seconds * sample_rate))
        self.slide_samples = max(1, int(slide_seconds * sample_rate))
        self.max_samples = int(max_seconds * sample_rate) if max_seconds > 0 else 0
        self.tail_samples = max(1, int((tail_seconds or DEFAULT_TAIL_SECONDS) * sample_rate))
        self.debug = debug
        self.telemetry = telemetry
        self.distance_summary_seconds = distance_summary_seconds

        self.state = "idle"
        self.suspended = False
        self._wake_buffer = np.zeros(self.window_samples, dtype=np.float32)
        self._end_buffer = np.zeros(self.window_samples, dtype=np.float32)
        self._pending_tail = np.array([], dtype=np.float32)
        self._captured: list[np.ndarray] = []
        self._recorded_samples = 0
        self._distance_stats: dict[str, dict[str, float]] = {}
        self._last_distance_summary = time.monotonic()

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
            detection = self._detect(self.wake_detector, self._wake_buffer, "wake")
            if detection:
                self._start_recording(source="wake")
                return [HandsFreeEvent("wake.detected", detection=detection)]
            return []

        self._recorded_samples += len(chunk)
        self._append_recording_chunk(chunk)
        self._end_buffer = _shift_append(self._end_buffer, chunk)
        detection = self._detect(self.end_detector, self._end_buffer, "end")
        if detection:
            event = self._finish_recording("end.detected", include_pending=False)
            return [HandsFreeEvent(event.kind, event.audio, detection, event.duration_seconds)]

        if self.max_samples and self._recorded_samples >= self.max_samples:
            return [self._finish_recording("timeout", include_pending=True)]

        return []

    def _detect(self, detector: Detector, audio: np.ndarray, label: str) -> Detection | None:
        try:
            detection = detector.detect(audio)
            if self.debug and detector.last_distance is not None:
                print(f"handsfree.{label}.distance={detector.last_distance:.4f}")
            if detector.last_distance is not None:
                self._record_distance(label, detector.last_distance, detected=detection is not None)
            return detection
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
        self._emit("handsfree.session_started_recording", source=source)

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


class HandsFreeAudioLoop:
    def __init__(
        self,
        session: HandsFreeSession,
        event_queue: queue.Queue,
        *,
        stop_event: threading.Event,
        telemetry: Any | None = None,
    ):
        self.session = session
        self.event_queue = event_queue
        self.stop_event = stop_event
        self._thread: threading.Thread | None = None
        self.telemetry = telemetry

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def join(self, timeout: float | None = None) -> None:
        if self._thread:
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        try:
            stream, actual_rate = open_input_stream()
            slide_samples = max(1, int(self.session.slide_samples * actual_rate / SAMPLE_RATE))
            overflow_count = 0
            with stream:
                print(f"handsfree.started sample_rate={actual_rate}")
                self._emit("handsfree.audio_loop_started", sample_rate=actual_rate, slide_samples=slide_samples)
                while not self.stop_event.is_set():
                    data, overflowed = stream.read(slide_samples)
                    if overflowed:
                        overflow_count += 1
                        print("handsfree.audio.overflow", file=sys.stderr)
                        if overflow_count == 1 or overflow_count % 10 == 0:
                            self._emit("handsfree.audio_overflow", count=overflow_count)
                    chunk = np.asarray(data[:, 0], dtype=np.float32)
                    if actual_rate != SAMPLE_RATE:
                        chunk = _resample(chunk, actual_rate, SAMPLE_RATE)
                    for event in self.session.feed(chunk):
                        self.event_queue.put(event)
                self._emit("handsfree.audio_loop_stopped", overflow_count=overflow_count)
        except Exception as e:
            self.event_queue.put(HandsFreeEvent("detector.error"))
            print(f"handsfree.detector.error error={e}", file=sys.stderr)
            self._emit("handsfree.audio_loop_error", error_type=type(e).__name__)

    def _emit(self, event: str, **properties) -> None:
        if self.telemetry:
            self.telemetry.emit(event, **properties)


def _shift_append(buffer: np.ndarray, chunk: np.ndarray) -> np.ndarray:
    if len(chunk) >= len(buffer):
        return chunk[-len(buffer):].astype(np.float32).copy()
    shifted = np.roll(buffer, -len(chunk))
    shifted[-len(chunk):] = chunk
    return shifted


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
