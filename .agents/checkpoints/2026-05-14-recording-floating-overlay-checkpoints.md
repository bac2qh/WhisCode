# Recording Floating Overlay Checkpoints

## 2026-05-14
- Created task branch/worktree `add-recording-overlay` from local `main`.
- Saved the implementation plan before source edits.
- Implemented the AppKit overlay helper process and `RecordingOverlayClient`.
- Added audio level callbacks for hotkey recording and hands-free recording chunks.
- Replaced normal recording banners with overlay show/hide by default.
- Added CLI flags `--recording-overlay`, `--no-recording-overlay`, and `--recording-notifications`.
- Added explicit `pyobjc-framework-Cocoa` dependency and updated `uv.lock`.
- Updated README, wiki, and project memory.
- Implementation commit: `6a28bb5`.
- Verification passed:
  - `PYTHONPATH=. uv run --with pytest python -m pytest` passed with 89 tests.
  - `uv run whiscode --help` succeeded and showed the overlay flags.
  - `uv run whiscode-enroll --help` succeeded.
  - `PYTHONPATH=. uv run python -m py_compile whiscode/recording_overlay.py whiscode/main.py whiscode/recorder.py whiscode/handsfree.py` succeeded.
  - `git diff --check` passed.
- Merged into local `main` by fast-forward; no merge commit.
- Archived plan at `.agents/plans/archive/2026-05-14-recording-floating-overlay.md`.
- Removed task worktree `.agents/worktrees/add-recording-overlay` and deleted local branch `add-recording-overlay`.
- Immediate next step: run WhisCode normally and validate the overlay with live microphone recording on macOS.
