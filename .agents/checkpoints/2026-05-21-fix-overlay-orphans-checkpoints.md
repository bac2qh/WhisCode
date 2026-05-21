# Fix Stuck Recording Overlay Helpers Checkpoints

## 2026-05-21

### Current State

- User reported dead overlay helpers after Ctrl-C during active recording.
- Process inspection showed two orphan `python -m whiscode.recording_overlay --helper` processes with PPID `1`, plus one active WhisCode run with its own helper.
- Existing helper reads stdin and schedules stop on EOF, and `RecordingOverlayClient.stop()` terminates/kills its child, but orphan helpers can still survive abrupt parent exit.

### Plan

- Add parent PID watchdog in helper.
- Add orphan-only cleanup before new helper launch and as a hidden maintenance CLI.
- Make main cleanup run in a `try/finally` shape so first Ctrl-C cleans overlay/recorder consistently.
- Add focused tests and update durable docs/memory.

### Next Step

- Close out to local `main`.

### Verification

- `uv run --with pytest pytest tests/test_recording_overlay.py tests/test_main_cli.py` passed: 34 tests.
- `uv run --with pytest pytest` passed: 145 tests.
- `uv run python -m whiscode.recording_overlay --cleanup-orphans` returned `{"failed_count":0,"found_count":2,"terminated_count":2}` and removed the two stale PPID `1` helpers.
- Post-cleanup process inspection showed only the active WhisCode run and its live child helper remain.
- `git diff --check` passed.

### Implemented

- Helper launches now include `--parent-pid`.
- Helper process starts a parent watchdog that schedules the normal stop command if the parent disappears.
- Parent process runs orphan-only cleanup before launching a new helper.
- Added `python -m whiscode.recording_overlay --cleanup-orphans`.
- Main loop shutdown now uses a `finally` cleanup path so first Ctrl-C reaches listener, overlay, hands-free loop, and recorder cleanup.
- Added bounded `recording_overlay.orphan_cleanup` telemetry with helper counts only.
- Updated wiki and memory.

### Commits

- `b8d9f0d` Harden recording overlay helper cleanup.
