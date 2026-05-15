# Hands-Free Keyword Detection

## 2026-05-13
- Added optional `--hands-free` mode using `local-wake==0.1.2` to detect local speaker-dependent wake and end phrases.
- Added `whiscode-enroll` to import at least three Voice Memo or other audio samples for each phrase and normalize them to 16 kHz mono WAV with macOS `afconvert`.
- Kept Right Shift as a fallback in hands-free mode; the default hotkey-only mode remains unchanged unless `--hands-free` is passed.
- Wake phrase detection starts capture after the wake phrase; end phrase detection stops capture and drops the final configurable tail before Whisper transcription.
- Added bounded diagnostic prints for start, wake detection, end detection, timeout, detector distance debugging, audio overflow, and detector errors without logging raw audio or transcripts outside the existing transcription output.
- Added guided Python microphone enrollment through `whiscode-enroll --record` and an automatic `--hands-free` startup prompt when wake/end reference WAV samples are missing.
- Guided enrollment defaults to three 2-second samples for each phrase and writes 16 kHz mono WAV files directly, so Voice Memos are no longer required for the normal setup path.

## 2026-05-14
- Added local JSONL telemetry for diagnosing repeated hands-free wake/end/transcribe/resume loops.
- Telemetry is local-only and defaults to `~/.config/whiscode/telemetry/events.jsonl` for `--hands-free` and guided `whiscode-enroll --record`.
- Added `--telemetry-path` and `--no-telemetry` to both runtime and enrollment CLIs.
- Telemetry records bounded lifecycle, detector, recording, enrollment, transcription, and loop-suspected metadata, while avoiding raw audio, transcripts, prompts, hotword contents, and typed text.
- Fixed a telemetry regression where `app.signal_received` was emitted inside the Ctrl+C signal handler. Signal handlers must remain signal-safe and only update simple in-memory shutdown state; telemetry is emitted after the main listener loop exits.
- Added detector-window readiness and speech-energy gating to prevent `local-wake` from matching zero-padded startup windows, silence, or low-level background noise.
- Added `--hands-free-min-rms`, `--hands-free-min-active-ratio`, and `--hands-free-active-level` for tuning the gate; default thresholds were chosen from observed enrolled sample levels.
- Hands-free telemetry now includes detector gate summaries plus RMS and active-sample ratio on wake/end detection events.
- Split wake and end thresholds so end detection was initially stricter by default. Wake stayed at `0.1` at that point; end defaulted to `0.055` to reject wake/non-end speech that previously matched the end detector around `0.063-0.070`.
- Added `--hands-free-end-threshold` for tuning end detection separately while preserving explicit legacy `--hands-free-threshold` behavior when the end threshold is omitted.
- Tightened wake defaults after observing high false-positive rates from incidental sound. Wake now defaults to threshold `0.055` and requires two consecutive matching windows before recording starts; `--hands-free-wake-confirmations` can tune that confirmation count.
- Added VAD trimming to guided/imported enrollment samples after observing 2-second reference WAVs with only about 0.54-0.80 seconds of actual speech. Added `whiscode-calibrate` to summarize reference and telemetry distance distributions before changing thresholds.
- Corrected the VAD-trimmed enrollment output to pad references back to the detector window length. Padding only to `local-wake`'s `12400`-sample minimum produced `0.775s` references, while runtime compares `2.0s` rolling windows and wake distances rose to about `0.22`.

## 2026-05-15
- Added trained idle-only hands-free key command slots for `page-up`, `page-down`, and `enter`. Guided enrollment now records samples for wake, end, and each command slot; runtime loads separate local-wake detectors for commands and maps confirmed detections to physical Page Up, Page Down, and Enter key taps through `pynput`. Command detection is ignored while recording or transcribing, uses command-specific threshold/confirmation CLI flags, and emits bounded command/key-injection telemetry without raw audio or transcripts.
- Added a shared `--max-recording-seconds` duration cap that defaults to `600.0` seconds and feeds hands-free timeout behavior unless the legacy `--hands-free-max-seconds` override is set. The cap limits buffered audio and transcription workload after accidental wake detections.
- Extended trained idle-only hands-free key command slots with `shift-enter` and `shift-tab`. Guided enrollment and manual import now use the same command-slot pipeline for all five slots, and runtime maps the new slots to Shift+Enter and Shift+Tab key combinations.
