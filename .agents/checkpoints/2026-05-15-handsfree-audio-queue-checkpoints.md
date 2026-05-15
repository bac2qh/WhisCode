# Hands-Free Audio Queue Checkpoints

## 2026-05-15 Initial
- Done: Created the task worktree `handsfree-audio-queue` from local `main` at `1ed29cf`.
- Immediate next step: Refactor `HandsFreeAudioLoop` into capture and detector workers with a bounded audio queue.
- Decisions: Use a default queue cap of `10.0` seconds; drop oldest queued audio under detector backlog; keep existing detection, command, timeout, and transcription behavior unchanged.
- Verification: Not yet run.

## 2026-05-15 Implementation
- Done: Implemented in commit `1ff9a58` (`Decouple hands-free audio capture from detection`).
- Immediate next step: Close out by merging the task branch into local `main`, archive the plan, and remove the task worktree and branch.
- Decisions: `HandsFreeAudioLoop` now starts a capture worker and detector worker. The capture worker only reads/copies microphone chunks into a bounded queue; the detector worker resamples, calls `HandsFreeSession.feed`, and forwards events. Queue capacity is controlled by `--hands-free-audio-queue-seconds`, defaulting to `10.0`, and full queues drop the oldest chunk.
- Verification:
  - `uv run --with pytest python -m pytest tests/test_handsfree.py tests/test_main_cli.py` passed with 30 tests.
  - `uv run --with pytest python -m pytest` passed with 118 tests.
  - `uv run whiscode --help` passed and showed `--hands-free-audio-queue-seconds`.
  - `git diff --check` passed.
