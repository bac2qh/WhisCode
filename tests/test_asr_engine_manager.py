import threading

import numpy as np

from whiscode.asr_engine_manager import AsrEngineManager


class FakeTelemetry:
    def __init__(self):
        self.events = []

    def emit(self, event, **properties):
        self.events.append((event, properties))


class FakeEngine:
    backend_name = "mlx-vibevoice"

    def __init__(self, label, *, started=None, release=None):
        self.model_label = label
        self.started = started
        self.release = release
        self.calls = []
        self.closed = False

    def transcribe(self, audio, **kwargs):
        self.calls.append((np.asarray(audio), kwargs))
        if self.started is not None:
            self.started.set()
        if self.release is not None:
            self.release.wait(timeout=2)
        return f"{self.model_label} transcript"

    def close(self):
        self.closed = True


def test_manual_during_external_starts_one_rescue_and_promotes_it():
    external_started = threading.Event()
    release_external = threading.Event()
    primary = FakeEngine("primary", started=external_started, release=release_external)
    telemetry = FakeTelemetry()
    created = []

    def factory():
        engine = FakeEngine(f"rescue-{len(created) + 1}")
        created.append(engine)
        return engine

    manager = AsrEngineManager(primary_engine=primary, engine_factory=factory, telemetry=telemetry)
    result_holder = {}
    external_thread = threading.Thread(
        target=lambda: result_holder.setdefault(
            "external",
            manager.transcribe_external(np.array([1.0], dtype=np.float32), language="en"),
        )
    )

    external_thread.start()
    assert external_started.wait(timeout=2)

    assert manager.transcribe_manual(np.array([2.0], dtype=np.float32), language="en") == "rescue-1 transcript"
    assert manager.transcribe_manual(np.array([3.0], dtype=np.float32), language="en") == "rescue-1 transcript"
    assert len(created) == 1

    release_external.set()
    external_thread.join(timeout=2)

    assert result_holder["external"] == "primary transcript"
    assert primary.calls[0][1]["extra_prompt"] is None
    assert primary.calls[0][1]["hotwords"] is None
    assert primary.calls[0][1]["progress_callback"] is None
    assert primary.closed is True
    assert manager.model_label == "rescue-1"
    assert [event for event, _ in telemetry.events] == [
        "asr.engine_rescue_started",
        "asr.engine_rescue_completed",
        "asr.engine_promoted",
        "asr.engine_retired",
    ]


def test_external_uses_primary_when_local_idle():
    primary = FakeEngine("primary")
    created = []
    manager = AsrEngineManager(primary_engine=primary, engine_factory=lambda: created.append(FakeEngine("rescue")) or created[-1])

    assert manager.transcribe_external(np.array([1.0], dtype=np.float32), language="en") == "primary transcript"

    assert created == []
    assert primary.closed is False
