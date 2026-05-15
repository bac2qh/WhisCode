# Overlay Helper Lifecycle Fix

## Summary
Fix the floating recording overlay helper so it cannot survive after the parent WhisCode process exits. The current helper keeps the AppKit event loop alive when stdin reaches EOF, which can leave the panel visible after the parent app is gone.

## Key Changes
- Make the helper treat stdin EOF as a stop command and terminate the AppKit app.
- Keep existing explicit `hide` and `stop` commands unchanged.
- Strengthen `RecordingOverlayClient.stop()` so it waits briefly for helper exit and kills the helper if graceful shutdown fails.
- Preserve existing overlay behavior, appearance, and command protocol.

## Telemetry / Diagnostics
- Preserve existing `recording_overlay.disabled` telemetry.
- Do not add raw audio, transcripts, prompts, or user content to diagnostics.

## Tests
- Unit-test the helper command reader schedules a stop on stdin EOF.
- Unit-test malformed JSON is ignored but EOF still stops the helper.
- Unit-test client `stop()` waits for graceful exit and force-kills if the helper does not terminate.
- Run `uv run --with pytest python -m pytest`, `uv run whiscode --help`, and `git diff --check`.

## Assumptions
- The live stuck overlay was caused by orphan helper processes; those were killed before implementation.
- The overlay position and visual design are out of scope for this fix.
