# Closeout
- Final status: implemented.
- Related checkpoint: `.agents/checkpoints/2026-05-15-handsfree-audio-queue-checkpoints.md`.
- Implementation commits: `1ff9a58`, `b51a123`.
- Merge commit: none; local `main` fast-forwarded to `b51a123`.
- Verification: `uv run --with pytest python -m pytest` passed with 118 tests; focused hands-free/main CLI tests passed with 30 tests; `uv run whiscode --help` and `git diff --check` passed.
- Worktree and branch cleanup: removed `.agents/worktrees/handsfree-audio-queue` and deleted local branch `handsfree-audio-queue`.
- Summary: Shipped a bounded hands-free audio queue that decouples microphone capture from detector processing, added `--hands-free-audio-queue-seconds`, and added queue/drop/processing telemetry.

# Decouple Hands-Free Audio Capture From Detection

## Summary
Eliminate frequent `handsfree.audio.overflow` by keeping microphone reads lightweight and continuous. The capture loop will only drain PortAudio into a bounded queue; a separate detector worker will run wake/end/command detection. This targets the root cause: detector work can block the mic read loop long enough for PortAudio to overflow.

## Key Changes
- Refactor `HandsFreeAudioLoop` into two internal workers:
  - capture worker: opens the mic stream, reads every slide interval, copies chunks into a queue.
  - detector worker: drains that queue, resamples if needed, calls `HandsFreeSession.feed(...)`, and forwards emitted events.
- Add `--hands-free-audio-queue-seconds`, default `10.0`, to bound queued audio between capture and detection.
- When the queue is full, drop the oldest queued chunk and keep the newest audio so the app recovers toward live listening instead of building stale backlog.
- Preserve existing behavior for wake/end/command detection, Right Shift fallback, overlay updates, and the 10-minute `--max-recording-seconds` cap.
- On shutdown, stop both workers cleanly and emit the final overflow/drop/backlog counts.

## Telemetry / Diagnostics
- Keep existing `handsfree.audio_overflow` for PortAudio-reported input overflow.
- Add bounded diagnostics:
  - `handsfree.audio_queue_dropped`
  - `handsfree.audio_queue_summary`
  - `handsfree.detector_processing_summary`
- Include only safe metadata: counts, queue size, queue seconds, state, durations, and status. Do not log raw audio, transcripts, prompts, or phrase text.

## Tests
- Unit-test that capture enqueues chunks without calling detector logic inline.
- Unit-test that detector worker drains queued chunks and still emits wake/end/command events.
- Unit-test queue-full behavior drops oldest chunks and emits telemetry.
- Unit-test shutdown joins both workers without hanging.
- Run `uv run --with pytest python -m pytest`, `uv run whiscode --help`, and `git diff --check`.

## Assumptions
- Default queue cap is `10.0` seconds, not 60 seconds.
- Under severe overload, dropping stale queued audio is preferable to PortAudio overflow or unbounded memory growth.
- Existing command slots, recording timeout behavior, and transcription flow stay unchanged.
