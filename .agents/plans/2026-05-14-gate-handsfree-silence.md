# Prevent Hands-Free False Triggers On Silence

## Summary
Fix the hands-free loop by adding detector gating before calling `local-wake`. Detection should only run after the rolling window is fully populated and the audio window has enough speech-like energy.

## Key Changes
- Track how many real samples have filled the wake/end detector windows.
- Do not call wake or end detectors until their rolling window has at least `window_seconds` of real microphone audio.
- Add a speech-energy gate before detector calls with defaults: minimum RMS `0.006`, active sample ratio `0.05`, active sample level `0.01`.
- Add CLI tuning flags: `--hands-free-min-rms`, `--hands-free-min-active-ratio`, and `--hands-free-active-level`.
- Keep Right Shift/manual start-stop and detector threshold behavior unchanged.
- Add telemetry for skipped detector windows and include RMS/active ratio on wake/end detections.

## Test Plan
- Add session tests for partial-window suppression, silent-window suppression, active-window detection, and end detector window readiness.
- Add CLI parse tests for the new energy-gate flags.
- Run `PYTHONPATH=. uv run --with pytest python -m pytest`.
- Run `uv run whiscode --help` and `uv run whiscode-enroll --help`.

## Assumptions
- Wake and end phrases are intentionally different.
- The immediate loop is caused by zero-padded or low-energy windows being accepted by `local-wake`.
- Defaults are conservative for the observed samples: phrase RMS was about `0.0096-0.0226`, quiet leading/trailing portions about `0.0025-0.0038`.
