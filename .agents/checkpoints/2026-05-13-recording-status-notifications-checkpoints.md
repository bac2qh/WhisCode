# Replace Recording Sounds With Silent macOS Status Notifications Checkpoints

## 2026-05-13
- Saved the finalized plan before implementation in branch `recording-status-notifications` at worktree `.agents/worktrees/recording-status-notifications`.
- Current state before implementation:
  - Source branch is local `main` at `2d6c0e952fd62f65d2d620291e24ebc5080c3b02`.
  - The main checkout has an unrelated unstaged one-line Turbo default change in `whiscode/main.py`; this task will preserve that intended default in the task branch without mutating the main checkout directly.
  - No tracked project memory index is present in this checkout.
- Immediate next step: replace start/stop audio beeps with macOS notification helper calls, add focused tests, then verify with pytest and CLI help.

## Implementation
- Replaced `beep_start()` / `beep_stop()` and their `afplay` calls with `notify_recording_now()` and `notify_recording_completed()`.
- Added `whiscode/status_notifier.py` using non-blocking `osascript -e 'display notification ...'` calls.
- Added tests for recording start notification, recording completion notification, AppleScript string escaping, and non-raising notification launch failure.
- Preserved the default model value as `mlx-community/whisper-large-v3-turbo`.
- Verification:
  - `uv run pytest` failed because it picked up a system pytest running outside the uv venv and could not import `whiscode`.
  - `uv run --with pytest python -m pytest` passed: 52 tests.
  - `uv run whiscode --help` passed.
- Immediate next step: commit the implementation, then record the implementation commit hash in this checkpoint.
