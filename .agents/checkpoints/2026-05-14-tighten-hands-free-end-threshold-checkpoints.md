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
- Immediate next step: commit and merge the task branch back into local `main`.
