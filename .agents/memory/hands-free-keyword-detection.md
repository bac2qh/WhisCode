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
- Telemetry is local-only. It originally defaulted to `~/.config/whiscode/telemetry/events.jsonl` for `--hands-free` and guided `whiscode-enroll --record`; as of 2026-05-24 runtime telemetry defaults to `~/Library/Logs/WhisCode/events.jsonl` on this macOS-focused project.
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
- Decoupled hands-free microphone capture from detector processing. The capture worker now continuously drains PortAudio into a bounded queue, while a detector worker runs `HandsFreeSession.feed`; `--hands-free-audio-queue-seconds` defaults to `10.0`, oldest queued chunks are dropped under backlog, and telemetry reports queue drops plus detector processing summaries.
- Extended trained idle-only hands-free key command slots with `tab`, `arrow-up`, and `arrow-down`. Guided enrollment and manual import now cover eight command slots, and runtime maps the new slots to Tab, Arrow Up, and Arrow Down key taps.
- Added configurable command enablement via `~/.config/whiscode/commands.ini`. Missing config keeps all command slots enabled for backward compatibility; when the file exists, `[commands]` is an allowlist where only `true` slots are loaded, enrolled, calibrated, and required by startup reference checks.

## 2026-05-16
- Marked the current hands-free milestone as the `v2.0.0-beta.1` beta in README/package metadata before creating the matching local tag. V2 is documented as the hands-free beta centered on wake/end phrases, voice key commands, bounded continuous capture, and the default floating recording overlay.

## 2026-05-24
- Hands-free wake/end recordings now enqueue for transcription instead of suspending the detector until transcription completes. After an end phrase, timeout, or manual stop, the session resets to idle and can accept another wake phrase while the transcription worker drains prior jobs.
- Hands-free command detection is disabled only while actively recording; it can run while earlier audio is queued or transcribing.

## 2026-06-06
- Omitted `--hands-free-tail-seconds` now auto-infers the end-phrase trim tail from enrolled end reference WAVs. Each readable reference contributes the active span from first through last sample where `abs(audio) >= --hands-free-active-level`; runtime uses the median valid span and falls back to `1.0s` when none can be computed.
- Explicit `--hands-free-tail-seconds FLOAT` still wins. End-phrase stops trim the resolved pending tail, while manual/Right Shift stops and timeout stops keep pending tail audio.

## 2026-06-08
- Hands-free end-tail resolution now separates base trim from extra detector-lag trim. `--hands-free-tail-seconds FLOAT` remains the explicit base override, omitted values still infer/fallback the base from end references, and `--hands-free-tail-extra-seconds` adds an extra buffer on top.
- The extra hands-free tail buffer defaults to `1.0s`. Set `--hands-free-tail-extra-seconds 0` to restore the previous base-only trim behavior.
- Tail-resolution telemetry now records `base_seconds`, `extra_seconds`, and total `resolved_seconds` while preserving source/reference/fallback fields. Manual/Right Shift stops and timeout stops still keep pending tail audio.
- Added Send Chunk as a wrapper around existing recording queue behavior. Right Option + Right Shift while recording stops the current recording, queues it with a `\n\n` typed-text suffix, suppresses the plain Right Shift toggle for that press, and immediately starts the next recording.
- Added optional hands-free Send Chunk detection while recording. The chunk phrase uses `~/.config/whiscode/wake/chunk`, auto-enables only when chunk WAV samples already exist, and can be forced with `--hands-free-chunk`; existing users without chunk samples are not prompted for chunk enrollment.
- Chunk phrase stops trim a chunk-specific inferred active-span tail plus `--hands-free-tail-extra-seconds`, independent of the end-phrase tail. Manual Send Chunk uses manual-stop audio and keeps pending tail audio.
- `whiscode-enroll chunk ...` imports chunk phrase samples, and guided enrollment records them only when `--include-chunk` is passed.
- Retired the separate hands-free Send Chunk phrase. Hands-free Send Chunk now reuses the wake/start phrase during recording, uses the wake threshold and wake confirmation count, and trims the Send Chunk tail from wake references plus `--hands-free-tail-extra-seconds`. Existing user chunk sample folders are ignored, not deleted.
- README daily-driver guidance now recommends `uv run whiscode --hands-free --asr-backend mlx-vibevoice` for regular dictation while explicitly keeping hands-free mode and MLX VibeVoice as opt-in choices rather than CLI defaults.
