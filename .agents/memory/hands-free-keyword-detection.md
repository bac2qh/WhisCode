# Hands-Free Keyword Detection

## 2026-05-13
- Added optional `--hands-free` mode using `local-wake==0.1.2` to detect local speaker-dependent wake and end phrases.
- Added `whiscode-enroll` to import at least three Voice Memo or other audio samples for each phrase and normalize them to 16 kHz mono WAV with macOS `afconvert`.
- Kept Right Shift as a fallback in hands-free mode; the default hotkey-only mode remains unchanged unless `--hands-free` is passed.
- Wake phrase detection starts capture after the wake phrase; end phrase detection stops capture and drops the final configurable tail before Whisper transcription.
- Added bounded diagnostic prints for start, wake detection, end detection, timeout, detector distance debugging, audio overflow, and detector errors without logging raw audio or transcripts outside the existing transcription output.
- Added guided Python microphone enrollment through `whiscode-enroll --record` and an automatic `--hands-free` startup prompt when wake/end reference WAV samples are missing.
- Guided enrollment defaults to three 2-second samples for each phrase and writes 16 kHz mono WAV files directly, so Voice Memos are no longer required for the normal setup path.
