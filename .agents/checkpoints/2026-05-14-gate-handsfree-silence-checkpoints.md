# Gate Hands-Free Silence Checkpoints

## 2026-05-14
- Created task branch/worktree `gate-handsfree-silence` from local `main`.
- Saved the implementation plan before source edits.
- Implemented detector window readiness and speech-energy gating.
- Added CLI flags `--hands-free-min-rms`, `--hands-free-min-active-ratio`, and `--hands-free-active-level`.
- Added telemetry for detector gate summaries and RMS/active-ratio values on wake/end detections.
- Updated README, wiki, and project memory with the new gate behavior.
- Verification passed:
  - `PYTHONPATH=. uv run --with pytest python -m pytest` passed with 82 tests.
  - `uv run whiscode --help` succeeded and showed the new gate flags.
  - `uv run whiscode-enroll --help` succeeded.
- Immediate next step: commit and merge the task branch back into local `main`.
