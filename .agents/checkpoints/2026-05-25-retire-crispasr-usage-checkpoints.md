# Retire CrispASR Usage Checkpoints

## 2026-05-25 Start
- Saved the implementation plan before product edits.
- Branch/worktree: `feature/retire-crispasr-usage` at `.agents/worktrees/retire-crispasr-usage`.
- Immediate next step: update CLI/help/docs to make `mlx-vibevoice` the recommended VibeVoice path and label CrispASR as legacy.
- Key decision: keep the CrispASR backend available for existing GGUF setups while retiring it from recommended usage.
- Verification: pending.

## 2026-05-25 Implementation
- Updated CLI help and CrispASR startup output to mark `crispasr` as legacy and recommend `mlx-vibevoice` for VibeVoice.
- Updated README and ASR backend wiki docs so MLX VibeVoice is the recommended local VibeVoice path and CrispASR is described as legacy GGUF compatibility only.
- Updated model-loading memory with the durable decision to keep CrispASR available but retire it from recommended usage.
- Added a CLI help test that asserts CrispASR is labelled legacy.
- Verification passed:
  - `uv run --with pytest pytest tests/test_main_cli.py tests/test_benchmark_asr.py`
  - `uv run --with pytest pytest`
  - `uv run python -m compileall whiscode`
- Implementation commit: `be057b2` (`Retire CrispASR as recommended VibeVoice path`).
- Closeout discovered that `.agents/scripts/main-branch-lock.sh` computed `project_root` with `git ... || cd ... && pwd`, which always appended `pwd` after successful `git rev-parse` because of shell operator precedence. This produced a newline-containing lock path and prevented the mutex from running the merge.
- Approved scope adjustment: fix the mutex helper in this branch so future closeouts can use it, then use a minimal manual lock for this closeout because the main helper is the broken component being fixed.
- Immediate next step: commit the checkpoint and lock-helper fix, then close out to local `main`.
