import numpy as np

from whiscode.handsfree import Detection, HandsFreeSession


class FakeDetector:
    def __init__(self, detections):
        self.detections = list(detections)
        self.last_distance = None

    def detect(self, audio):
        if not self.detections:
            self.last_distance = 1.0
            return None
        detection = self.detections.pop(0)
        self.last_distance = detection.distance if detection else 1.0
        return detection


def chunk(value):
    return np.array([value], dtype=np.float32)


def test_wake_detection_starts_recording_without_capturing_wake_audio():
    session = HandsFreeSession(
        FakeDetector([Detection("wake-01.wav", 0.05)]),
        FakeDetector([]),
        sample_rate=10,
        window_seconds=0.2,
        slide_seconds=0.1,
        tail_seconds=0.2,
    )

    events = session.feed(chunk(9))

    assert [event.kind for event in events] == ["wake.detected"]
    assert session.state == "recording"
    assert session.manual_stop().audio.size == 0


def test_end_detection_stops_recording_and_excludes_pending_tail():
    session = HandsFreeSession(
        FakeDetector([Detection("wake-01.wav", 0.05)]),
        FakeDetector([None, None, None, Detection("end-01.wav", 0.04)]),
        sample_rate=10,
        window_seconds=0.2,
        slide_seconds=0.1,
        tail_seconds=0.2,
    )
    session.feed(chunk(0))

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


def test_suspended_session_ignores_audio():
    session = HandsFreeSession(
        FakeDetector([Detection("wake-01.wav", 0.05)]),
        FakeDetector([]),
        sample_rate=10,
        window_seconds=0.2,
    )

    session.suspend()

    assert session.feed(chunk(1)) == []
    assert session.state == "idle"


class FakeTelemetry:
    def __init__(self):
        self.events = []

    def emit(self, event, **properties):
        self.events.append((event, properties))


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
    )

    session.feed(chunk(0))
    events = session.feed(chunk(1))

    assert [event.kind for event in events] == ["end.detected"]
    event_names = [event for event, properties in telemetry.events]
    assert "handsfree.detector_distance_summary" in event_names
    assert "handsfree.session_started_recording" in event_names
    assert "handsfree.session_finished_recording" in event_names
