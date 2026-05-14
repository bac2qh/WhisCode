# Signal-Safe Telemetry Shutdown Checkpoints

## 2026-05-14
- Created task branch/worktree `fix-signal-safe-telemetry` from local `main`.
- Saved the implementation plan before source edits.
- Root cause identified from history: prior fixes `d14b740` and `f83328d` made Ctrl+C signal-safe and moved hotkey work off the event tap; telemetry commit `914cdbd` reintroduced file I/O in `handle_signal`.
- Removed telemetry emission from the signal handler. The handler now only increments Ctrl+C count, records the last signal number, sets `shutdown_event`, and uses `os._exit(0)` on repeated Ctrl+C.
- Moved `app.signal_received` telemetry emission to the main shutdown path after the listener loop exits.
- Updated project memory with the signal-safety invariant.
- Verification passed:
  - `PYTHONPATH=. uv run --with pytest python -m pytest` passed with 78 tests.
  - `uv run whiscode --help` succeeded.
  - `uv run whiscode-enroll --help` succeeded.
- Implemented in commit `5e95c82`.
- Fast-forward merged into local `main` at `5e95c82`; no merge commit was created.
- Archived the plan to `.agents/plans/archive/2026-05-14-signal-safe-telemetry-shutdown.md`.
- Removed task worktree `.agents/worktrees/fix-signal-safe-telemetry` and deleted local branch `fix-signal-safe-telemetry`.
- Immediate next step: none for this plan.
