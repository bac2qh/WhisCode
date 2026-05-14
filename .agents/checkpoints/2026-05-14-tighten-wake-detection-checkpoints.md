# Tighten Wake Detection Checkpoints

## 2026-05-14
- Created task branch/worktree `tighten-wake-detection` from local `main`.
- Saved the implementation plan before source edits.
- Root cause hypothesis: wake detection is still using the original permissive `0.1` threshold and starts recording on a single matched detector window, so any active sound that lands below that loose distance threshold can trigger recording.
- Lowered the default wake threshold to `0.055`.
- Added `--hands-free-wake-confirmations`, defaulting to `2`, and wired it into `HandsFreeSession`.
- Added wake confirmation state so one matched detector window is treated as pending instead of starting recording.
- Added bounded `handsfree.detector_confirmation_pending` and `handsfree.detector_confirmation_completed` telemetry.
- Updated README, wiki, and project memory for the safer defaults and tuning path.
- Implementation commit: `dbf5e37`.
- Verification passed:
  - `PYTHONPATH=. uv run --with pytest python -m pytest` passed with 90 tests.
  - `uv run whiscode --help` succeeded and showed `--hands-free-wake-confirmations` plus threshold default `0.055`.
  - `PYTHONPATH=. uv run python -m py_compile whiscode/handsfree.py whiscode/main.py` succeeded.
  - `git diff --check` passed.
- Merged into local `main` by fast-forward; no merge commit.
- Archived plan at `.agents/plans/archive/2026-05-14-tighten-wake-detection.md`.
- Removed task worktree `.agents/worktrees/tighten-wake-detection` and deleted local branch `tighten-wake-detection`.
- Immediate next step: run `uv run whiscode --hands-free --hands-free-debug` against live room audio to confirm incidental sounds no longer produce confirmed wake detections.
