# Low Mic Gain Handling Checkpoints

## 2026-05-21

### Current State

- User reported microphone input voice seems really low.
- Initial inspection found WhisCode captures raw `float32` PortAudio samples and passes them directly to Whisper.
- The visible overlay level also uses a fixed RMS scale (`rms / 0.08`), so quiet microphones can look nearly flat.
- Hands-free detector energy thresholds rely on raw microphone levels; changing detector input would invalidate existing calibration.

### Plan

- Add shared bounded normalization for recorded speech before transcription.
- Apply it to hotkey and hands-free transcription audio only.
- Keep detector and enrollment reference behavior raw/stable unless a later plan explicitly retunes thresholds.
- Add bounded telemetry for whether gain was applied and the before/after levels.

### Next Step

- None. Closeout completed on local `main`.

### Verification

- `uv run --with pytest pytest tests/test_recorder.py tests/test_main_cli.py tests/test_handsfree.py` passed: 42 tests.
- `uv run --with pytest pytest` passed: 142 tests.
- `git diff --check` passed.

### Implemented

- Added shared pre-transcription audio normalization with RMS/peak measurement, `8x` maximum boost, near-silence skip, and `0.95` peak limiting.
- Wired hotkey and hands-free transcription paths through the normalizer without changing raw hands-free detector input.
- Added bounded `audio.normalization_applied` telemetry when gain is applied.
- Updated README, wiki, and project memory to document the behavior and diagnostics.

### Commits

- `6fb4556` Add bounded gain normalization for quiet mic input.
- `c9f826d` Record low mic gain checkpoint.

### Closeout

- Local `main` fast-forwarded to `c9f826d`; no merge commit was created.
- Removed task worktree `.agents/worktrees/fix-low-mic-gain`.
- Deleted local branch `fix-low-mic-gain`.
- Archived the plan to `.agents/plans/archive/2026-05-21-low-mic-gain.md`.
