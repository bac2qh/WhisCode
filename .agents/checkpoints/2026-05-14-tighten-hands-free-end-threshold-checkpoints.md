# Tighten Hands-Free End Threshold Checkpoints

## 2026-05-14
- Created task branch/worktree `tighten-handsfree-end-threshold` from local `main`.
- Saved the implementation plan before source edits.
- Current diagnosis: silence gating works, but the end detector still matches wake/non-end speech once the end window fills. Cross-score checks show wake samples matching the end support set around `0.063-0.070`, below the previous shared `0.1` threshold.
- Added `DEFAULT_END_THRESHOLD = 0.055` and `--hands-free-end-threshold`.
- Kept wake threshold default at `0.1`.
- Preserved explicit legacy behavior: if `--hands-free-threshold` is explicitly supplied and `--hands-free-end-threshold` is omitted, the supplied threshold applies to both.
- Updated end detector construction and telemetry to use/report the end-specific threshold.
- Updated README, wiki, tests, and project memory.
- Verification passed:
  - `PYTHONPATH=. uv run --with pytest python -m pytest` passed with 84 tests.
  - `uv run whiscode --help` succeeded and showed `--hands-free-end-threshold`.
  - `uv run whiscode-enroll --help` succeeded.
- Implemented in commit `5f82c7c`.
- Fast-forward merged into local `main` at `5f82c7c`; no merge commit was created.
- Archived the plan to `.agents/plans/archive/2026-05-14-tighten-hands-free-end-threshold.md`.
- Removed task worktree `.agents/worktrees/tighten-handsfree-end-threshold` and deleted local branch `tighten-handsfree-end-threshold`.
- Immediate next step: none for this plan.
