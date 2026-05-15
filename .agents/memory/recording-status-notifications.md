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
- Guided enrollment initially kept using the existing notification banners.

## 2026-05-15
- Replaced guided enrollment sample recording banners with the same floating recording overlay used by normal recording.
- Enrollment capture now streams microphone levels to the overlay while each sample records, hides the overlay on success or failure, and supports `uv run whiscode-enroll --record --no-recording-overlay`.
- Fixed an overlay helper crash that made the overlay invisible. The AppKit view was calling `drawAtPoint_withAttributes_` on a Python `str`; timer text now renders through `NSAttributedString`. Overlay helper exits now emit bounded `recording_overlay.disabled` telemetry and a stderr warning instead of failing silently.
