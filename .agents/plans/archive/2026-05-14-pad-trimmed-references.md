# Pad Trimmed References To Detector Window

## Closeout
- Final status: implemented.
- Related checkpoint: `.agents/checkpoints/2026-05-14-pad-trimmed-references-checkpoints.md`.
- Implementation commits: `7d268a0`, `80fccf0`.
- Merge: fast-forward to local `main`; no merge commit.
- Verification: `PYTHONPATH=. uv run --with pytest python -m pytest`, `uv run whiscode-enroll --help`, `uv run whiscode-calibrate --help`, `PYTHONPATH=. uv run python -m py_compile whiscode/enroll.py`, and `git diff --check`.
- Cleanup: task worktree `.agents/worktrees/pad-trimmed-references` removed; local branch `pad-trimmed-references` deleted.
- Shipped trim-then-pad reference preprocessing so regenerated reference WAVs match the runtime detector window length.

## Summary
Fix the post-trim enrollment regression where VAD-trimmed wake/end reference WAVs became `0.775s`, while runtime detection compares against `2.0s` rolling mic windows.

## Key Changes
- Keep VAD trimming, but pad processed references to the default detector window length, not only `local-wake`'s minimum sample length.
- Preserve CLI behavior and thresholds.
- Update calibration/enrollment docs to note that samples are speech-trimmed and then padded to the detector window.

## Test Plan
- Unit-test default preprocessing pads to `SAMPLE_RATE * DEFAULT_WINDOW_SECONDS`.
- Keep explicit min-sample preprocessing tests for smaller injected test sizes.
- Run full pytest suite.
- Run `uv run whiscode-enroll --help`, `uv run whiscode-calibrate --help`, and `git diff --check`.
