# Recording Overlay

WhisCode shows a small floating macOS overlay while normal recording is active. It is hidden while idle and after recording stops.

The overlay shows:
- elapsed recording time as a stopwatch.
- live microphone level bars.
- a red recording indicator.

The overlay is implemented as a separate AppKit helper process controlled by the main WhisCode process through newline-delimited JSON commands. If the helper cannot start, recording and transcription continue without the overlay.

Use `--no-recording-overlay` to disable the overlay. Use `--recording-notifications` to keep macOS start/end notification banners in addition to the overlay.

Guided enrollment still uses the existing notification banners.
