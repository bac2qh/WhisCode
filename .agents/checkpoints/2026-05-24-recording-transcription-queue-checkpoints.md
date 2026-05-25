# Recording Queue And Stacked Overlay Checkpoints

## 2026-05-24 Start
- Main project root: `/Users/xin/Documents/repos/WhisCode`.
- Task worktree: `/Users/xin/Documents/repos/WhisCode/.agents/worktrees/recording-transcription-queue`.
- Branch: `recording-transcription-queue`.
- User direction: implement a recording/transcription queue so new recordings can be captured while VibeVoice/CrispASR transcribes prior audio; show stacked overlays like macOS notifications; keep a plaintext last-five transcript recovery file in `/tmp`; do not integrate clipboard.
- Current behavior: `State.TRANSCRIBING` causes hotkeys/manual hands-free hotkeys to be ignored, hands-free detection is suspended during transcription, and `RecordingOverlayClient` manages only one card at a time.
- Telemetry/debuggability decision: add bounded queue lifecycle/recovery-file events without transcript text; `/tmp/whiscode-last-transcripts.txt` intentionally contains local typed transcripts.
- Immediate next step: implement queue worker, hands-free queue behavior, stacked overlay commands/helper rendering, transcript recovery writer, tests, docs, and memory updates.

## 2026-05-24 Implementation Notes
- Implementation commit: `e25799492f08b9e740f624ad0c34ee3aa13e8327`.
- Implemented a `TranscriptionJobQueue` with a fixed capacity of five waiting jobs, one active transcription, and one active recording reservation.
- Refactored runtime handling so hotkey and hands-free recordings enqueue completed audio while a single transcription worker drains jobs FIFO and types completed text immediately.
- Hands-free no longer suspends wake/end detection during transcription; after each end/timeout/manual stop, the session can accept another wake while earlier jobs transcribe. Command detection is disabled only during active recording.
- Extended the overlay client/helper to render a stacked top-centered panel keyed by item id. Cards can move from recording to queued to transcribing and disappear when completed or failed.
- Added `/tmp/whiscode-last-transcripts.txt` recovery logging for the last five successfully typed, postprocessed/refined transcripts. Clipboard integration was intentionally skipped.
- Added bounded queue/recovery telemetry events without transcript text.
- Verification passed:
  - `uv run --with pytest pytest tests/test_transcription_queue.py tests/test_recording_overlay.py tests/test_handsfree.py tests/test_main_cli.py`
  - `uv run python -m compileall whiscode`
  - `uv run --with pytest pytest`
  - `git diff --check`
- Immediate next step: commit checkpoint hash bookkeeping, then close out.
