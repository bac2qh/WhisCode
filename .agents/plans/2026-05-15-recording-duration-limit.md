# Recording Duration Limit Plan

## Summary
Add a shared recording length cap so accidental recordings cannot grow indefinitely. Use `10 minutes / 600 seconds` as the new default, configurable from the CLI. Current hands-free already has a `180s` timeout, so this replaces that default with a shared limit and extends the same protection to right-shift/manual recording.

## Key Changes
- Add preferred CLI option: `--max-recording-seconds FLOAT`, default `600.0`; `0` disables the cap.
- Keep `--hands-free-max-seconds` as a backward-compatible hands-free-only override.
- Update manual `Recorder` so it stops appending audio once the cap is reached and notifies the main loop to finalize/transcribe the capped audio automatically.
- Update hands-free mode to use the shared default unless the legacy hands-free-specific option is provided.
- Clarify logs/docs that “overflow” is PortAudio input overflow, while the duration cap is for bounding buffered audio, memory use, and transcription workload.

## Telemetry / Diagnostics
- Emit a bounded `recording.timeout` event when manual recording hits the cap, including mode, configured max seconds, and captured audio duration.
- Preserve existing `handsfree.timeout` telemetry.
- Do not log raw audio, transcript text, wake words, or user content.

## Tests
- Add recorder unit coverage proving chunks are capped at the configured max duration and the timeout callback fires once.
- Update CLI tests for the new default `--max-recording-seconds 600.0`, explicit override, `0` disable, and legacy `--hands-free-max-seconds`.
- Run the existing test suite with `uv run pytest`.

## Assumptions
- The intended default is exactly `600` seconds for both manual and hands-free recording.
- The cap should auto-finalize and transcribe the audio captured so far rather than silently discard it.
- Existing users of `--hands-free-max-seconds` should not break immediately.
