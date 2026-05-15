# Hands-Free Audio Queue Checkpoints

## 2026-05-15 Initial
- Done: Created the task worktree `handsfree-audio-queue` from local `main` at `1ed29cf`.
- Immediate next step: Refactor `HandsFreeAudioLoop` into capture and detector workers with a bounded audio queue.
- Decisions: Use a default queue cap of `10.0` seconds; drop oldest queued audio under detector backlog; keep existing detection, command, timeout, and transcription behavior unchanged.
- Verification: Not yet run.
