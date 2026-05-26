# External NAS Transcription Queue Checkpoints

## 2026-05-26 Start

### Done
- Created task worktree `external-nas-transcription-queue` at `.agents/worktrees/external-nas-transcription-queue` from local `main`.
- Saved implementation plan before source edits.

### Immediate Next Step
- Inspect existing CLI, queue, backend, telemetry, docs, and tests, then implement the external intake queue in scoped milestones.

### Decisions And Reasoning
- Use a task worktree because implementation requires tracked plan/checkpoint/docs/source edits.
- Keep the prior agent's plan as the source of user intent.
- `pyproject.toml` dependency updates are permitted by the user.
- User clarified that Whisper does not need to be supported for this new path and that moving forward the intended backend is VibeVoice ASR. Scope narrowed so external NAS intake is `mlx-vibevoice` only; existing Whisper app behavior remains untouched for compatibility.

### Verification
- Not run yet.

## 2026-05-26 Implementation Milestone

### Done
- Added `AsrEngineManager` for MLX VibeVoice manual-priority rescue behavior with a maximum of two in-process engines.
- Added external inbox/outbox support:
  - env/CLI config for inbox, outbox, extensions, poll cadence, and stable-file quiet period.
  - top-level watcher with hidden/unsupported filtering, stability detection, duplicate/result skipping, and bounded telemetry.
  - MLX-Audio disk decode path with mono 16 kHz float32 normalization.
  - `.txt` and `.json` success/error sidecars with source metadata, backend/model, transcript on success, and bounded error details on failure.
- Wired external intake into the app only for `mlx-vibevoice`; other backends fail fast when an external inbox is configured.
- Kept external jobs out of WhisCode manual hotwords, prompt, replacements, postprocessing, refinement, keyboard typing, and stats.
- Documented the external NAS queue in README and wiki, and added durable project memory.

### Immediate Next Step
- Commit the implementation, then update this checkpoint with the commit hash and closeout status.

### Decisions And Reasoning
- User clarified that Whisper support is not needed for this new feature, so external intake is `mlx-vibevoice` only.
- Existing `mlx-whisper`, `llama-cpp`, and `crispasr` app behavior remains available outside the external NAS queue path.
- The external queue uses quiet-period stability instead of ready markers because external publishers may write directly into the inbox.
- Routine telemetry uses file ids, extensions, sizes, durations, model labels, and error types; transcript text and full paths stay out of telemetry.

### Verification
- `uv run --with pytest pytest` passed: 230 tests.
