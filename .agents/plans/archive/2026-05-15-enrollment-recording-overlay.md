# Closeout

- Final status: implemented.
- Related checkpoint: `.agents/checkpoints/2026-05-15-enrollment-recording-overlay-checkpoints.md`.
- Implementation commits: `8336e05` (`Use recording overlay during enrollment`), `1a819d7` (`Record enrollment overlay checkpoint`).
- Merge result: fast-forwarded local `main` from `bae07e0` to `1a819d7`; no merge commit was created.
- Verification performed: `uv run --with pytest python -m pytest` passed with 108 tests; `uv run whiscode-enroll --help`, `uv run whiscode --help`, and `git diff --check` passed.
- Worktree and branch cleanup: removed `.agents/worktrees/enrollment-recording-overlay` and deleted local branch `enrollment-recording-overlay`.
- Summary: guided enrollment now uses the floating recording overlay with waveform/timer by default instead of notification banners, with `--no-recording-overlay` available for enrollment.

# Replace Enrollment Banners With Recording Overlay

## Summary

Guided enrollment currently still uses macOS Notification Center banners for each sample. Change `uv run whiscode-enroll --record` to use the same floating recording overlay as normal recording: red status dot, live waveform bars, and elapsed `MM:SS` counter.

## Key Changes

- Show `RecordingOverlayClient` during guided enrollment microphone capture and hide it after each sample completes or fails.
- Stream enrollment microphone levels to the overlay while capture is active.
- Remove direct enrollment calls to `notify_recording_now()` and `notify_recording_completed()`.
- Add enrollment CLI overlay flags consistent with runtime: overlay on by default, `--no-recording-overlay` to disable.
- Preserve audio import behavior and status notification support for normal runtime `--recording-notifications`.
- Update README, wiki, and project memory.

## Telemetry And Diagnostics

- Keep existing enrollment telemetry event names for sample started/completed/failed.
- Do not log raw audio, transcripts, prompts, or sample contents.
- Add only bounded overlay lifecycle behavior through tests; no new runtime telemetry is required because the overlay helper is best-effort and already degrades silently.

## Test Plan

- Unit-test guided recording shows/hides the overlay and sends level updates for each sample.
- Unit-test failure path hides overlay when capture raises.
- Unit-test enrollment CLI parses overlay flags.
- Run `uv run --with pytest python -m pytest`.
- Run `uv run whiscode-enroll --help` and `uv run whiscode --help`.

## Assumptions

- The target path is guided enrollment only: `uv run whiscode-enroll --record`.
- Notification banners should no longer appear during guided enrollment.
- Normal recording and hands-free recording overlay behavior remains unchanged.
