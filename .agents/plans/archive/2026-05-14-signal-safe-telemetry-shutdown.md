# Closeout
- Final status: implemented.
- Checkpoint: `.agents/checkpoints/2026-05-14-signal-safe-telemetry-shutdown-checkpoints.md`.
- Implementation commit: `5e95c82`.
- Merge: fast-forward to `5e95c82`; no merge commit created.
- Verification: `PYTHONPATH=. uv run --with pytest python -m pytest` passed with 78 tests; `uv run whiscode --help` and `uv run whiscode-enroll --help` succeeded.
- Cleanup: removed task worktree `.agents/worktrees/fix-signal-safe-telemetry` and deleted local branch `fix-signal-safe-telemetry`.
- Summary: restored signal-safe Ctrl+C behavior by moving telemetry emission out of the signal handler.

# Signal-Safe Telemetry Shutdown Fix

## Summary
Fix the regression where telemetry writes run inside the Ctrl+C signal handler. Restore the prior shutdown invariant: the signal handler only records minimal in-memory state, sets the shutdown event, and uses `os._exit(0)` only on repeated Ctrl+C.

## Key Changes
- Remove telemetry file writes from `handle_signal`.
- Record signal number/count in simple in-memory variables only.
- Emit `app.signal_received` after the main listener loop exits, outside the signal handler.
- Keep the hotkey callback fast and non-suppressing; do not change hands-free detector behavior.

## Tests
- Add a focused unit test for the signal-safe shutdown helper/state if needed.
- Run the existing suite with `PYTHONPATH=. uv run --with pytest python -m pytest`.
- Run `uv run whiscode --help` and `uv run whiscode-enroll --help`.

## Assumptions
- The keyboard hijack/Ctrl+C symptom is the same class of issue fixed before: unsafe work from the signal path or event tap path.
- This fix should not change telemetry event schemas except moving `app.signal_received` emission out of the signal handler.
