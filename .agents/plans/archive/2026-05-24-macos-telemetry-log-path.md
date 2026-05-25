# Closeout 2026-05-24
- Final status: `implemented`.
- Related checkpoint: `.agents/checkpoints/2026-05-24-macos-telemetry-log-path-checkpoints.md`.
- Implementation commits: `8038a5c` (`Use macOS log folder for telemetry`) and `0e953b3` (`Record macOS telemetry path checkpoint`).
- Merge result: fast-forwarded local `main` to `0e953b3`; no merge commit was created.
- Verification: `uv run --with pytest pytest tests/test_telemetry.py tests/test_main_cli.py tests/test_enroll.py tests/test_calibrate.py` passed; `uv run python -m compileall whiscode` passed.
- Cleanup: removed task worktree `.agents/worktrees/macos-telemetry-log-path` and deleted local branch `macos-telemetry-log-path`; unrelated worktree `.agents/worktrees/env-llama-paths` was left untouched.
- Shipped: default telemetry now writes to `~/Library/Logs/WhisCode/events.jsonl`, while `--telemetry-path` and `--no-telemetry` remain unchanged.

# macOS Telemetry Log Path

## Summary
Move WhisCode's default telemetry file out of `~/.config` and into the macOS user log location.

## Scope
- Change the default telemetry JSONL path to `~/Library/Logs/WhisCode/events.jsonl`.
- Keep `--telemetry-path` as the explicit override.
- Keep `--no-telemetry` behavior unchanged.
- Update runtime, enrollment, calibration, docs, wiki, tests, and memory references that describe the default telemetry location.

## Telemetry / Debuggability
- This change affects where diagnostics are written, not event contents.
- Existing events and privacy boundaries remain unchanged.
- The new path is persistent enough for diagnostics and follows macOS log placement better than `/tmp` or `~/.config`.
- Do not add transcript text, raw audio, prompts, hotwords, provider payloads, secrets, or typed text to telemetry.

## Verification
- `uv run --with pytest pytest tests/test_telemetry.py tests/test_main_cli.py tests/test_enroll.py tests/test_calibrate.py`
- `uv run python -m compileall whiscode`

## Assumptions
- WhisCode currently targets this local macOS environment, so `~/Library/Logs/WhisCode/events.jsonl` is the preferred default over `/tmp`.
