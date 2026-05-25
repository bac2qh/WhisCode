from datetime import datetime, timezone

import numpy as np

from whiscode.transcription_queue import TranscriptRecoveryLog, TranscriptionJobQueue


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


def test_transcript_recovery_log_keeps_last_five_entries(tmp_path):
    recovery = TranscriptRecoveryLog(
        path=tmp_path / "whiscode-last-transcripts.txt",
        clock=lambda: datetime(2026, 5, 24, 22, 0, tzinfo=timezone.utc),
    )

    for index in range(6):
        result = recovery.record(
            text=f"transcript {index}",
            job_id=f"job-{index}",
            source="hotkey",
            audio_seconds=index + 0.25,
        )
        assert result.ok is True

    text = (tmp_path / "whiscode-last-transcripts.txt").read_text(encoding="utf-8")
    assert "transcript 0" not in text
    assert "job_id=job-0" not in text
    for index in range(1, 6):
        assert f"transcript {index}" in text
        assert f"job_id=job-{index}" in text
    assert text.count("--- timestamp=") == 5


def test_transcript_recovery_log_reports_write_errors(tmp_path):
    blocker = tmp_path / "not-a-dir"
    blocker.write_text("file")
    recovery = TranscriptRecoveryLog(path=blocker / "whiscode-last-transcripts.txt")

    result = recovery.record(text="hello", job_id="job-1", source="hotkey", audio_seconds=1.0)

    assert result.ok is False
    assert result.entry_count == 1
    assert result.error_type is not None
