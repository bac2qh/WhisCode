# Recording Status Notifications

## 2026-05-13
- Replaced start/stop recording confirmation sounds with silent macOS Notification Center banners.
- Preserved the local default model decision to use `mlx-community/whisper-large-v3-turbo`.
- Kept the existing keyboard-triggered in-memory recording and transcription flow unchanged; only the user feedback mechanism changed.
- Notification failures are non-blocking and emit a bounded stderr warning without transcript, prompt, or audio content.
