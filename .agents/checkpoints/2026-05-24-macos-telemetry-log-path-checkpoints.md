# macOS Telemetry Log Path Checkpoints

## 2026-05-24 Start
- Main project root: `/Users/xin/Documents/repos/WhisCode`.
- Task worktree: `/Users/xin/Documents/repos/WhisCode/.agents/worktrees/macos-telemetry-log-path`.
- Branch: `macos-telemetry-log-path`.
- User feedback: telemetry under `~/.config` is not an appropriate macOS default. User suggested `/tmp`; decision is to use `~/Library/Logs/WhisCode/events.jsonl` because it is a persistent user log location, while `/tmp` is volatile scratch space.
- Telemetry/debuggability: path-only change; no telemetry event contents should change.
- Implemented:
  - Runtime telemetry default path now resolves to `~/Library/Logs/WhisCode/events.jsonl`.
  - `whiscode-calibrate` imports the shared runtime telemetry default so calibration reads the same default file.
  - Runtime/enrollment help text, README, wiki, wiki log, telemetry memory, and hands-free memory were updated.
  - Added tests for the macOS default telemetry path and calibrate/runtime default alignment.
- Verification:
  - `uv run --with pytest pytest tests/test_telemetry.py tests/test_main_cli.py tests/test_enroll.py tests/test_calibrate.py` passed: 50 tests.
  - `uv run python -m compileall whiscode` passed.
- Implementation commit: `8038a5c` (`Use macOS log folder for telemetry`).
- Immediate next step: commit this checkpoint hash update and close out.
