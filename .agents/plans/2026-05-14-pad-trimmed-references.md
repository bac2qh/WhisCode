# Pad Trimmed References To Detector Window

## Summary
Fix the post-trim enrollment regression where VAD-trimmed wake/end reference WAVs became `0.775s`, while runtime detection compares against `2.0s` rolling mic windows.

## Key Changes
- Keep VAD trimming, but pad processed references to the default detector window length, not only `local-wake`'s minimum sample length.
- Preserve CLI behavior and thresholds.
- Update calibration/enrollment docs to note that samples are speech-trimmed and then padded to the detector window.

## Test Plan
- Unit-test default preprocessing pads to `SAMPLE_RATE * DEFAULT_WINDOW_SECONDS`.
- Keep explicit min-sample preprocessing tests for smaller injected test sizes.
- Run full pytest suite.
- Run `uv run whiscode-enroll --help`, `uv run whiscode-calibrate --help`, and `git diff --check`.
