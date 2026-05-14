# Tighten Hands-Free End Detection Threshold

## Summary
Prevent wake/normal speech from stopping recording by giving the end detector its own stricter default threshold. Keep wake detection permissive while requiring stronger matches for end detection.

## Key Changes
- Add `DEFAULT_END_THRESHOLD = 0.055`.
- Add `--hands-free-end-threshold` CLI flag.
- Keep `--hands-free-threshold` as the wake threshold by default.
- Preserve explicit legacy behavior: if a user explicitly passes `--hands-free-threshold` and omits `--hands-free-end-threshold`, use that value for both wake and end.
- Log both wake and end thresholds in telemetry.
- Update docs/tests for the new threshold split.

## Test Plan
- Add CLI tests for default wake/end thresholds and explicit legacy threshold behavior.
- Add a session/detector test proving a stricter end threshold rejects wake-like cross matches.
- Run `PYTHONPATH=. uv run --with pytest python -m pytest`.
- Run `uv run whiscode --help` and `uv run whiscode-enroll --help`.

## Assumptions
- The latest premature transcription is caused by the end support set matching wake/non-end speech around distance `0.063-0.070`, below the previous shared `0.1` threshold.
