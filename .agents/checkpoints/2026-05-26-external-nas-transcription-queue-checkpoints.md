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
- Implementation commit: `662ea5d Add external VibeVoice transcription queue`.

### Immediate Next Step
- Archive the plan, merge the task branch into local `main`, remove the worktree, and delete the local task branch.

### Decisions And Reasoning
- User clarified that Whisper support is not needed for this new feature, so external intake is `mlx-vibevoice` only.
- Existing `mlx-whisper`, `llama-cpp`, and `crispasr` app behavior remains available outside the external NAS queue path.
- The external queue uses quiet-period stability instead of ready markers because external publishers may write directly into the inbox.
- Routine telemetry uses file ids, extensions, sizes, durations, model labels, and error types; transcript text and full paths stay out of telemetry.

### Verification
- `uv run --with pytest pytest` passed: 230 tests.

## 2026-05-26 Closeout

### Done
- Merged task branch `external-nas-transcription-queue` into local `main` with a fast-forward merge.
- Archived the active plan to `.agents/plans/archive/2026-05-26-external-nas-transcription-queue.md`.
- Removed worktree `.agents/worktrees/external-nas-transcription-queue`.
- Deleted local branch `external-nas-transcription-queue`.
- Closeout/archive commit: `a1381e9 Archive external queue implementation plan`.

### Immediate Next Step
- None. Plan is implemented and archived.

### Decisions And Reasoning
- Fast-forward merge preserved the two task commits without a merge commit.
- Closeout bookkeeping was committed separately on local `main` after branch merge and cleanup.

### Verification
- Pre-merge verification remained `uv run --with pytest pytest`: 230 tests passed.
- Closeout verification checked branch deletion, worktree removal, plan archival, and clean `main` status before final reporting.
