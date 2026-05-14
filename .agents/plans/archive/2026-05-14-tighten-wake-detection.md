# Tighten Hands-Free Wake Detection

## Closeout
- Final status: implemented.
- Related checkpoint: `.agents/checkpoints/2026-05-14-tighten-wake-detection-checkpoints.md`.
- Implementation commits: `dbf5e37`, `9c7e9ee`.
- Merge: fast-forward to local `main`; no merge commit.
- Verification: `PYTHONPATH=. uv run --with pytest python -m pytest`, `uv run whiscode --help`, `PYTHONPATH=. uv run python -m py_compile whiscode/handsfree.py whiscode/main.py`, and `git diff --check`.
- Cleanup: task worktree `.agents/worktrees/tighten-wake-detection` removed; local branch `tighten-wake-detection` deleted.
- Shipped stricter wake defaults: threshold `0.055` and two consecutive wake confirmations before recording starts.

## Summary
Reduce hands-free wake false positives by making the default wake matcher less permissive and requiring a short confirmation streak before starting recording.

## Key Changes
- Lower the default wake detection threshold from `0.1` to a stricter value aligned with the current end threshold.
- Add `--hands-free-wake-confirmations` so wake detection requires multiple consecutive matching detector windows before recording starts.
- Keep end detection at one confirmation by default to avoid making stop phrases harder to use.
- Emit bounded telemetry when a wake candidate is pending confirmation.
- Update tests and documentation for the safer default behavior and tuning flag.

## Telemetry And Diagnostics
- Candidate confirmation telemetry should identify detector label, current streak, required streak, distance, RMS, and active ratio.
- Do not log raw audio, transcripts, filenames beyond existing detector names, or user speech content.
- Existing wake/end detection telemetry remains the source of truth for confirmed starts/stops.

## Test Plan
- Unit-test that one wake candidate no longer starts recording when two confirmations are required.
- Unit-test that consecutive wake candidates do start recording.
- Unit-test CLI parsing for `--hands-free-wake-confirmations`.
- Run `PYTHONPATH=. uv run --with pytest python -m pytest`.
- Run `uv run whiscode --help`.
