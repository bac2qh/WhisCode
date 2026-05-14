# Recording Floating Overlay With Stopwatch And Waveform

## Summary
Replace recording start/end banners with a small macOS floating overlay shown only while recording. The overlay is non-activating, always-on-top, and shows elapsed recording time plus live input waveform bars.

## Key Changes
- Add an AppKit/PyObjC overlay helper process launched by WhisCode.
- Add a `RecordingOverlayClient` that sends newline-delimited JSON commands over stdin: `show`, `level`, `hide`, and `stop`.
- Feed throttled audio levels from hotkey recording and hands-free captured chunks.
- Replace normal recording start/end banners with overlay show/hide by default.
- Keep guided enrollment banners unchanged.
- Add CLI flags: `--recording-overlay`, `--no-recording-overlay`, and `--recording-notifications`.
- Add explicit Cocoa PyObjC dependency because the overlay imports AppKit directly.

## Test Plan
- Unit-test overlay client command serialization and failure handling with mocked `subprocess.Popen`.
- Unit-test recorder level callback without real microphone hardware.
- Unit-test hands-free session level callback with fake audio chunks.
- Unit-test CLI parsing for overlay flags.
- Run `PYTHONPATH=. uv run --with pytest python -m pytest`.
- Run `uv run whiscode --help` and `uv run whiscode-enroll --help`.

## Assumptions
- The preferred UI is a floating window only while recording, not a permanent menu-bar item.
- The overlay replaces start/end notification banners for normal recording.
- If the helper cannot start, recording must continue without UI.
