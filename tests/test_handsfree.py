import queue
import threading

import numpy as np

from whiscode.handsfree import AudioChunk, Detection, HandsFreeAudioLoop, HandsFreeEvent, HandsFreeSession


class FakeDetector:
    def __init__(self, detections):
        self.detections = list(detections)
        self.last_distance = None
        self.calls = 0

    def detect(self, audio):
        self.calls += 1
        if not self.detections:
            self.last_distance = 1.0
            return None
        detection = self.detections.pop(0)
        self.last_distance = detection.distance if detection else 1.0
        return detection


class ThresholdDetector:
    def __init__(self, distance, threshold):
        self.distance = distance
        self.threshold = threshold
        self.last_distance = None
        self.calls = 0

    def detect(self, audio):
        self.calls += 1
        self.last_distance = self.distance
        if self.distance < self.threshold:
            return Detection("match.wav", self.distance)
        return None


def chunk(value):
    return np.array([value], dtype=np.float32)


def test_wake_detection_starts_recording_without_capturing_wake_audio():
    wake_detector = FakeDetector([Detection("wake-01.wav", 0.05), Detection("wake-02.wav", 0.04)])
    session = HandsFreeSession(
        wake_detector,
        FakeDetector([]),
        sample_rate=10,
        window_seconds=0.2,
        slide_seconds=0.1,
        tail_seconds=0.2,
    )

    assert session.feed(chunk(9)) == []
    assert session.feed(chunk(9)) == []
    events = session.feed(chunk(9))

    assert [event.kind for event in events] == ["wake.detected"]
    assert wake_detector.calls == 2
    assert session.state == "recording"
    assert session.manual_stop().audio.size == 0


def test_single_wake_detection_waits_for_confirmation():
    telemetry = FakeTelemetry()
    wake_detector = FakeDetector([Detection("wake-01.wav", 0.05), None])
    session = HandsFreeSession(
        wake_detector,
        FakeDetector([]),
        sample_rate=10,
        window_seconds=0.2,
        slide_seconds=0.1,
        tail_seconds=0.2,
        telemetry=telemetry,
    )

    assert session.feed(chunk(9)) == []
    assert session.feed(chunk(9)) == []
    assert session.feed(chunk(9)) == []

    assert wake_detector.calls == 2
    assert session.state == "idle"
    assert ("handsfree.detector_confirmation_pending", {
        "detector": "wake",
        "count": 1,
        "required": 2,
        "distance": 0.05,
        "rms": 9.0,
        "active_ratio": 1.0,
    }) in telemetry.events


def test_end_detection_stops_recording_and_excludes_pending_tail():
    session = HandsFreeSession(
        FakeDetector([Detection("wake-01.wav", 0.05)]),
        FakeDetector([None, None, Detection("end-01.wav", 0.04)]),
        sample_rate=10,
        window_seconds=0.2,
        slide_seconds=0.1,
        tail_seconds=0.2,
        wake_confirmations=1,
    )
    assert session.feed(chunk(1)) == []
    session.feed(chunk(1))

    session.feed(chunk(1))
    session.feed(chunk(2))
    session.feed(chunk(3))
    events = session.feed(chunk(4))

    assert [event.kind for event in events] == ["end.detected"]
    np.testing.assert_array_equal(events[0].audio, np.array([1, 2], dtype=np.float32))
    assert events[0].duration_seconds == 0.2
    assert session.state == "idle"


def test_manual_stop_includes_pending_tail():
    session = HandsFreeSession(
        FakeDetector([]),
        FakeDetector([]),
        sample_rate=10,
        window_seconds=0.2,
        slide_seconds=0.1,
        tail_seconds=0.2,
    )

    assert session.manual_start().kind == "manual.started"
    session.feed(chunk(1))
    session.feed(chunk(2))
    event = session.manual_stop()

    assert event.kind == "manual.stopped"
    np.testing.assert_array_equal(event.audio, np.array([1, 2], dtype=np.float32))
    assert event.duration_seconds == 0.2
    assert session.state == "idle"


def test_timeout_stops_recording_and_includes_pending_tail():
    session = HandsFreeSession(
        FakeDetector([]),
        FakeDetector([None, None, None]),
        sample_rate=10,
        window_seconds=0.2,
        slide_seconds=0.1,
        max_seconds=0.3,
        tail_seconds=0.2,
    )
    session.manual_start()

    assert session.feed(chunk(1)) == []
    assert session.feed(chunk(2)) == []
    events = session.feed(chunk(3))

    assert [event.kind for event in events] == ["timeout"]
    np.testing.assert_array_equal(events[0].audio, np.array([1, 2, 3], dtype=np.float32))
    assert session.state == "idle"


def test_partial_wake_window_does_not_call_detector():
    wake_detector = FakeDetector([Detection("wake-01.wav", 0.05)])
    session = HandsFreeSession(
        wake_detector,
        FakeDetector([]),
        sample_rate=10,
        window_seconds=0.2,
    )

    assert session.feed(chunk(1)) == []

    assert wake_detector.calls == 0
    assert session.state == "idle"


def test_silent_full_wake_window_does_not_call_detector():
    wake_detector = FakeDetector([Detection("wake-01.wav", 0.05)])
    session = HandsFreeSession(
        wake_detector,
        FakeDetector([]),
        sample_rate=10,
        window_seconds=0.2,
    )

    assert session.feed(chunk(0)) == []
    assert session.feed(chunk(0)) == []

    assert wake_detector.calls == 0
    assert session.state == "idle"


def test_end_detector_waits_for_full_recording_window():
    wake_detector = FakeDetector([Detection("wake-01.wav", 0.05)])
    end_detector = FakeDetector([Detection("end-01.wav", 0.04)])
    session = HandsFreeSession(
        wake_detector,
        end_detector,
        sample_rate=10,
        window_seconds=0.2,
        tail_seconds=0.1,
        wake_confirmations=1,
    )
    session.feed(chunk(1))
    session.feed(chunk(1))

    assert session.feed(chunk(1)) == []

    assert end_detector.calls == 0
    assert session.state == "recording"


def test_stricter_end_threshold_rejects_cross_phrase_distance():
    wake_detector = ThresholdDetector(distance=0.04, threshold=0.1)
    end_detector = ThresholdDetector(distance=0.068, threshold=0.055)
    session = HandsFreeSession(
        wake_detector,
        end_detector,
        sample_rate=10,
        window_seconds=0.2,
        tail_seconds=0.1,
        wake_confirmations=1,
    )
    session.feed(chunk(1))
    session.feed(chunk(1))

    assert session.feed(chunk(1)) == []
    assert session.feed(chunk(1)) == []

    assert end_detector.calls == 1
    assert session.state == "recording"


def test_recording_chunks_report_audio_level():
    levels = []
    session = HandsFreeSession(
        FakeDetector([Detection("wake-01.wav", 0.05)]),
        FakeDetector([]),
        sample_rate=10,
        window_seconds=0.2,
        tail_seconds=0.1,
        level_callback=levels.append,
        wake_confirmations=1,
    )
    session.feed(chunk(1))
    session.feed(chunk(1))

    session.feed(chunk(0.5))

    assert len(levels) == 1
    assert levels[0] > 0


def test_suspended_session_ignores_audio():
    session = HandsFreeSession(
        FakeDetector([Detection("wake-01.wav", 0.05)]),
        FakeDetector([]),
        sample_rate=10,
        window_seconds=0.2,
        wake_confirmations=1,
    )

    session.suspend()

    assert session.feed(chunk(1)) == []
    assert session.state == "idle"


def test_idle_command_detection_requires_confirmation_and_resets_buffer():
    command_detector = FakeDetector([
        Detection("page-up-01.wav", 0.05),
        Detection("page-up-02.wav", 0.04),
        Detection("page-up-03.wav", 0.03),
    ])
    session = HandsFreeSession(
        FakeDetector([None, None, None]),
        FakeDetector([]),
        command_detectors={"page-up": command_detector},
        command_confirmations=2,
        sample_rate=10,
        window_seconds=0.2,
        slide_seconds=0.1,
    )

    assert session.feed(chunk(1)) == []
    assert session.feed(chunk(1)) == []
    events = session.feed(chunk(1))

    assert [(event.kind, event.command) for event in events] == [("command.detected", "page-up")]
    assert events[0].detection.name == "page-up-02.wav"
    assert session.state == "idle"

    assert session.feed(chunk(1)) == []
    assert command_detector.calls == 2


def test_command_detector_is_ignored_while_recording():
    command_detector = FakeDetector([Detection("page-down-01.wav", 0.04)])
    session = HandsFreeSession(
        FakeDetector([]),
        FakeDetector([None, None]),
        command_detectors={"page-down": command_detector},
        command_confirmations=1,
        sample_rate=10,
        window_seconds=0.2,
    )

    session.manual_start()
    session.feed(chunk(1))
    session.feed(chunk(1))

    assert command_detector.calls == 0
    assert session.state == "recording"


def test_command_detection_uses_best_distance_when_multiple_slots_match():
    page_up_detector = FakeDetector([Detection("page-up-01.wav", 0.05)])
    enter_detector = FakeDetector([Detection("enter-01.wav", 0.03)])
    session = HandsFreeSession(
        FakeDetector([None, None]),
        FakeDetector([]),
        command_detectors={"page-up": page_up_detector, "enter": enter_detector},
        command_confirmations=1,
        sample_rate=10,
        window_seconds=0.2,
    )

    session.feed(chunk(1))
    events = session.feed(chunk(1))

    assert [(event.kind, event.command) for event in events] == [("command.detected", "enter")]


class FakeTelemetry:
    def __init__(self):
        self.events = []

    def emit(self, event, **properties):
        self.events.append((event, properties))


class FakeLoopSession:
    def __init__(self, events=None):
        self.slide_samples = 16000
        self.state = "idle"
        self.events = list(events or [])
        self.feed_calls = []

    def feed(self, chunk):
        self.feed_calls.append(chunk.copy())
        return self.events.pop(0) if self.events else []


class OneReadStream:
    def __init__(self, stop_event, *, overflowed=False):
        self.stop_event = stop_event
        self.overflowed = overflowed
        self.reads = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, frames):
        self.reads += 1
        self.stop_event.set()
        return np.ones((frames, 1), dtype=np.float32), self.overflowed


def test_audio_loop_capture_enqueues_without_running_detector_inline():
    stop_event = threading.Event()
    telemetry = FakeTelemetry()
    session = FakeLoopSession()
    stream = OneReadStream(stop_event)
    loop = HandsFreeAudioLoop(
        session,
        queue.Queue(),
        stop_event=stop_event,
        telemetry=telemetry,
        stream_factory=lambda: (stream, 16000),
    )

    loop._capture_loop()

    assert stream.reads == 1
    assert session.feed_calls == []
    assert loop._audio_queue.qsize() == 1
    assert telemetry.events[0][0] == "handsfree.audio_loop_started"


def test_audio_loop_detector_worker_drains_chunks_and_emits_events():
    stop_event = threading.Event()
    event_queue = queue.Queue()
    session = FakeLoopSession([[HandsFreeEvent("wake.detected", detection=Detection("wake.wav", 0.03))]])
    loop = HandsFreeAudioLoop(session, event_queue, stop_event=stop_event)
    loop._audio_queue.put(AudioChunk(np.array([1.0], dtype=np.float32), 16000))
    stop_event.set()

    loop._detector_loop()

    assert len(session.feed_calls) == 1
    assert event_queue.get_nowait().kind == "wake.detected"


def test_audio_loop_drops_oldest_chunk_when_queue_is_full():
    stop_event = threading.Event()
    telemetry = FakeTelemetry()
    session = FakeLoopSession()
    loop = HandsFreeAudioLoop(
        session,
        queue.Queue(),
        stop_event=stop_event,
        telemetry=telemetry,
        audio_queue_seconds=0.5,
    )

    loop._enqueue_audio_chunk(AudioChunk(np.array([1.0], dtype=np.float32), 16000))
    loop._enqueue_audio_chunk(AudioChunk(np.array([2.0], dtype=np.float32), 16000))

    queued = loop._audio_queue.get_nowait()
    np.testing.assert_array_equal(queued.audio, np.array([2.0], dtype=np.float32))
    assert ("handsfree.audio_queue_dropped", {
        "count": 1,
        "queue_size": 0,
        "queue_max_chunks": 1,
        "audio_queue_seconds": 0.5,
    }) in telemetry.events


def test_audio_loop_start_and_join_stops_workers():
    stop_event = threading.Event()
    session = FakeLoopSession()
    stream = OneReadStream(stop_event)
    loop = HandsFreeAudioLoop(
        session,
        queue.Queue(),
        stop_event=stop_event,
        stream_factory=lambda: (stream, 16000),
    )

    loop.start()
    loop.join(timeout=2.0)

    assert loop._capture_thread is not None
    assert loop._detector_thread is not None
    assert not loop._capture_thread.is_alive()
    assert not loop._detector_thread.is_alive()


def test_session_emits_telemetry_for_detection_and_finish():
    telemetry = FakeTelemetry()
    session = HandsFreeSession(
        FakeDetector([Detection("wake-01.wav", 0.05)]),
        FakeDetector([Detection("end-01.wav", 0.04)]),
        sample_rate=10,
        window_seconds=0.2,
        slide_seconds=0.1,
        tail_seconds=0.1,
        telemetry=telemetry,
        distance_summary_seconds=0,
        wake_confirmations=1,
    )

    session.feed(chunk(1))
    session.feed(chunk(1))
    session.feed(chunk(1))
    events = session.feed(chunk(1))

    assert [event.kind for event in events] == ["end.detected"]
    event_names = [event for event, properties in telemetry.events]
    assert "handsfree.detector_distance_summary" in event_names
    assert "handsfree.session_started_recording" in event_names
    assert "handsfree.session_finished_recording" in event_names


def test_session_emits_gate_summary_for_silent_window():
    telemetry = FakeTelemetry()
    session = HandsFreeSession(
        FakeDetector([Detection("wake-01.wav", 0.05)]),
        FakeDetector([]),
        sample_rate=10,
        window_seconds=0.2,
        telemetry=telemetry,
    )

    session.feed(chunk(0))
    session.feed(chunk(0))

    assert telemetry.events[-1][0] == "handsfree.detector_gate_summary"
    assert telemetry.events[-1][1]["reason"] == "low_rms"
