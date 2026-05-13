# Replace Recording Sounds With Silent macOS Status Notifications

## Summary
- Create a task worktree from local `main` at `.agents/worktrees/recording-status-notifications` on branch `recording-status-notifications`.
- Preserve the current intended Turbo default if it is still only present as the existing unstaged one-line `whiscode/main.py` change.
- Replace the start/stop `afplay` confirmation sounds with silent macOS Notification Center banners:
  - Start recording: `Recording now`
  - Stop recording: `Recording completed`
- Keep the existing Right Shift toggle flow, in-memory recording, transcription, and paste behavior unchanged.

## Key Changes
- Add a small notification helper, preferably `whiscode/status_notifier.py`, using `osascript` with `display notification`.
- Update `whiscode/main.py` to remove `beep_start()` / `beep_stop()` usage and call the notifier when entering `RECORDING` and when stopping capture before transcription begins.
- Do not add new Python dependencies; use the macOS tools already available on the target platform.
- Keep notification failures non-blocking: if launching the notification command fails, print a concise warning to stderr and continue recording/transcribing.

## Project State Workflow
- Before code edits, save this plan into the task worktree under `.agents/plans/2026-05-13-recording-status-notifications.md` and create the matching checkpoint under `.agents/checkpoints/2026-05-13-recording-status-notifications-checkpoints.md`.
- Do not mutate the current dirty `main` checkout directly.
- After implementation and verification, commit from the task worktree, update memory/checkpoint per repo instructions, then close out by merging back to local `main`.

## Test Plan
- Add focused unit tests for the notification helper:
  - builds/launches `osascript` for `Recording now`
  - builds/launches `osascript` for `Recording completed`
  - handles `OSError` without raising
- Run `uv run pytest`.
- Run `uv run whiscode --help` to confirm CLI parsing still works.
- Optional manual check on macOS: start the app, press Right Shift once and confirm a silent `Recording now` banner; press again and confirm `Recording completed`, with no Morse/Frog audio.

## Diagnostics
- Existing terminal status lines remain the primary debug surface: `Recording...`, `Transcribing...`, transcript/error output, and session stats.
- Notification helper failure emits only a bounded stderr warning; it must not include transcript text, audio data, prompts, or personal content.
- No persistent telemetry or metrics are added because this is a local CLI UX change.

## Assumptions
- "Status bar" means silent macOS notification banner, not a persistent menu bar item or custom overlay.
- Only start/stop capture states get notifications; no extra `Transcribing` or transcript-complete banner.
- The current unstaged Turbo default reflects desired local behavior and should not be lost during branch/worktree setup.
