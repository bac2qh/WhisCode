# Recording Queue And Stacked Overlay

## Summary
Allow WhisCode to keep recording while earlier audio is transcribing. Finished recordings enter a FIFO transcription queue, transcription remains single-worker/sequential, and completed text is typed immediately in job order. The overlay becomes a stack of cards: newest recording on top, older queued/transcribing jobs pushed down, and cards disappear when typed or failed.

## Key Changes
- Replace the global "transcribing blocks recording" state with separate recording and transcription concerns:
  - Only one active recording at a time.
  - One transcription worker drains queued jobs FIFO.
  - Queue capacity is fixed at 5 waiting jobs, plus the currently transcribing job; reserve a slot when a new recording starts.
  - If the queue is full, reject new hotkey/hands-free starts with terminal output and bounded telemetry.
- Apply queueing to all modes:
  - Hotkey mode: Right Shift starts/stops recording even while prior jobs transcribe.
  - Hands-free mode: wake/end/manual recordings enqueue and detection resumes immediately after each recording finishes.
  - Hands-free key commands remain available whenever no recording is active.
- Type completed transcriptions immediately, even if a new recording is active. Preserve FIFO ordering by using one transcription worker.
- Add a simple transcript recovery file at `/tmp/whiscode-last-transcripts.txt`:
  - Store the last 5 successfully typed, postprocessed/refined transcripts.
  - Rewrite the file after each successful typed job.
  - Use plain text with timestamp/job metadata and clear delimiters.
  - Do not use or modify the system clipboard.

## Overlay Behavior
- Extend the overlay helper from one card to a dynamic stack in one top-centered panel.
- Each recording/transcription job has a stable overlay item id.
- New items are inserted at the top. Existing items keep order and shift down.
- Item states:
  - `recording`: stopwatch + live level bars.
  - `queued`: compact "Queued" card with audio duration/order.
  - `transcribing`: current "Transcribing" card; progress bar remains indeterminate for CrispASR when no frame progress exists.
  - completed/failed: remove the item.
- Keep existing `RecordingOverlayClient.show()/hide()/show_transcribing()` compatibility for guided enrollment and older tests; add item-aware methods for queued runtime transcription.

## Telemetry / Debuggability
- Add bounded events only, no transcript text:
  - `recording.queue_full`
  - `recording.queued`
  - `transcription.queue_started`
  - `transcription.queue_completed`
  - `transcription.queue_failed`
  - `transcript_recovery_file_written`
- Include safe fields such as `job_id`, `source`, `queue_depth`, `audio_seconds`, `duration_seconds`, and `error_type`.
- Do not put transcript content, prompts, hotwords, provider payloads, or full paths in telemetry. The `/tmp` recovery file intentionally contains local transcript text.

## Test Plan
- Unit-test queue coordination:
  - allows recording while worker is transcribing.
  - enforces capacity 5 with active-recording reservation.
  - drains jobs FIFO and types results in order.
  - records failures without blocking later jobs.
- Unit-test hands-free flow:
  - wake/end recordings enqueue while transcription is active.
  - detection resumes after enqueue instead of staying suspended.
  - queue-full wake resets hands-free session to idle.
- Unit-test overlay client/helper commands:
  - item creation, state transition, progress update, removal.
  - newest card ordering.
  - legacy `show()/hide()/show_transcribing()` still emits compatible commands.
- Unit-test `/tmp/whiscode-last-transcripts.txt` writer:
  - stores typed/postprocessed text only.
  - keeps only last 5 entries.
  - handles write errors without failing transcription.
- Run focused tests:
  - `uv run --with pytest pytest tests/test_recording_overlay.py tests/test_handsfree.py tests/test_main_cli.py`
  - any new queue/recovery-log test file.
  - `uv run python -m compileall whiscode`

## Assumptions
- No clipboard integration in this iteration.
- No new CLI flag for v1; queue capacity is fixed at 5.
- Transcription remains sequential to avoid backend concurrency issues with VibeVoice/CrispASR.
- The recovery file path is fixed: `/tmp/whiscode-last-transcripts.txt`.
- The typed/recovery transcript is the same processed text WhisCode injects into the active app, not raw ASR output.
