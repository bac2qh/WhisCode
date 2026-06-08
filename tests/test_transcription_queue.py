import numpy as np

from whiscode.transcription_queue import TranscriptionJobQueue


def test_transcription_job_queue_reserves_capacity_for_active_recording():
    jobs = TranscriptionJobQueue(capacity=1)

    first = jobs.try_reserve_recording(source="hotkey")
    assert first is not None
    assert jobs.try_reserve_recording(source="hotkey") is None

    job = jobs.finish_recording(audio=np.array([0.1], dtype=np.float32), audio_seconds=0.5, job_id=first.job_id)
    assert job is not None
    assert jobs.try_reserve_recording(source="hotkey") is None

    active = jobs.get(timeout=0.01)
    assert active == job
    assert jobs.try_reserve_recording(source="hotkey") is not None


def test_transcription_job_queue_drains_fifo_and_tracks_active_work():
    jobs = TranscriptionJobQueue(capacity=5)
    first = jobs.try_reserve_recording(source="hotkey")
    assert first is not None
    first_job = jobs.finish_recording(audio=np.array([1.0], dtype=np.float32), audio_seconds=1.0, job_id=first.job_id)
    second = jobs.try_reserve_recording(source="handsfree_wake")
    assert second is not None
    second_job = jobs.finish_recording(audio=np.array([2.0], dtype=np.float32), audio_seconds=2.0, job_id=second.job_id)

    assert jobs.pending_depth() == 2
    assert jobs.has_transcription_work() is True

    assert jobs.get(timeout=0.01) == first_job
    assert jobs.active_job_id() == first_job.job_id
    jobs.complete_active(first_job.job_id)

    assert jobs.get(timeout=0.01) == second_job
    assert jobs.active_job_id() == second_job.job_id
    jobs.complete_active(second_job.job_id)

    assert jobs.has_transcription_work() is False
    assert jobs.is_idle() is True


def test_transcription_job_queue_idle_includes_reserved_recording():
    jobs = TranscriptionJobQueue(capacity=1)

    reservation = jobs.try_reserve_recording(source="hotkey")

    assert reservation is not None
    assert jobs.has_transcription_work() is False
    assert jobs.is_idle() is False


def test_transcription_job_queue_carries_text_suffix():
    jobs = TranscriptionJobQueue(capacity=1)
    reservation = jobs.try_reserve_recording(source="hotkey")

    job = jobs.finish_recording(
        audio=np.array([0.1], dtype=np.float32),
        audio_seconds=0.5,
        job_id=reservation.job_id,
        text_suffix="\n\n",
    )

    assert job is not None
    assert job.text_suffix == "\n\n"
    assert jobs.get(timeout=0.01).text_suffix == "\n\n"
