# Recording Status Notifications

## 2026-05-13
- Replaced start/stop recording confirmation sounds with silent macOS Notification Center banners.
- Preserved the local default model decision to use `mlx-community/whisper-large-v3-turbo`.
- Kept the existing keyboard-triggered in-memory recording and transcription flow unchanged; only the user feedback mechanism changed.
- Notification failures are non-blocking and emit a bounded stderr warning without transcript, prompt, or audio content.

## 2026-05-14
- Replaced normal recording start/end banners with a floating AppKit overlay by default.
- The overlay is shown only while recording, displays a stopwatch and live microphone level bars, and runs in a helper process so UI failures do not block recording.
- Added `--no-recording-overlay` to disable the overlay and `--recording-notifications` to keep start/end notification banners in addition to the overlay.
- Guided enrollment keeps using the existing notification banners.
