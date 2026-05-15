# Trim Hands-Free Samples And Calibration Checkpoints

## 2026-05-14
- Pushed local `main` to `origin/main` through `7a612bc`.
- Created task branch/worktree `trim-calibrate-handsfree` from local `main`.
- Saved the implementation plan before source edits.
- Key finding from planning: current 2s enrollment WAVs contain only about 0.54-0.80s speech by Silero VAD, while upstream `local-wake` trims silence before saving reference samples.
- Implemented VAD trim/pad preprocessing for guided recording and imported samples.
- Added `whiscode-calibrate` as a read-only calibration report CLI.
- Calibration report includes reference distances, telemetry trigger distances, detector-summary minima, p05/median/p95 tails, and an advisory reference-separation threshold.
- Updated README, wiki, and project memory.
- Verification passed:
  - `PYTHONPATH=. uv run --with pytest python -m pytest` passed with 96 tests.
  - `uv run whiscode-enroll --help` succeeded.
  - `uv run whiscode-calibrate --help` succeeded.
  - `uv run whiscode-calibrate` succeeded against local samples and telemetry.
  - `PYTHONPATH=. uv run python -m py_compile whiscode/enroll.py whiscode/calibrate.py` succeeded.
  - `uv lock --check` succeeded.
  - `git diff --check` passed.
- Immediate next step: commit and merge the task branch back into local `main`.
