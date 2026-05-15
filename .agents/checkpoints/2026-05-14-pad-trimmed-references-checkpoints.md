# Pad Trimmed References Checkpoints

## 2026-05-14
- Created task branch/worktree `pad-trimmed-references` from local `main`.
- Saved the implementation plan before source edits.
- Root cause: VAD-trimmed enrollment samples were padded to `12400` samples (`0.775s`), but runtime wake detection compares a `2.0s` rolling window. After re-enrollment, wake runtime distances rose to about `0.22`, so the `0.055` threshold could no longer match.
- Padded VAD-trimmed references to `DEFAULT_WINDOW_SECONDS * SAMPLE_RATE` by default.
- Updated docs, wiki, and project memory to describe trim-then-pad behavior.
- Implementation commit: `7d268a0`.
- Verification passed:
  - `PYTHONPATH=. uv run --with pytest python -m pytest` passed with 97 tests.
  - `uv run whiscode-enroll --help` succeeded.
  - `uv run whiscode-calibrate --help` succeeded.
  - `PYTHONPATH=. uv run python -m py_compile whiscode/enroll.py` succeeded.
  - `git diff --check` passed.
- Merged into local `main` by fast-forward; no merge commit.
- Archived plan at `.agents/plans/archive/2026-05-14-pad-trimmed-references.md`.
- Removed task worktree `.agents/worktrees/pad-trimmed-references` and deleted local branch `pad-trimmed-references`.
- Immediate next step: push local `main` to `origin/main`, then re-run guided enrollment so the saved references are regenerated at the detector window length.
