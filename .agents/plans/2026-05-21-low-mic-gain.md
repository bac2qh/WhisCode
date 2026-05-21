# Low Mic Gain Handling

## Goal

Investigate why microphone input sounds/appears very low and add a conservative app-side gain correction so quiet captures are easier for transcription without changing wake/end detector calibration.

## Scope

- Add shared audio peak/RMS measurement and normalization helpers for recorded speech.
- Apply normalization after hotkey recording stops and after hands-free capture completes, before Whisper transcription.
- Keep raw microphone audio for hands-free wake/end/command detection and reference enrollment preprocessing so existing detector thresholds remain meaningful.
- Add focused tests for quiet audio boost, clipping limits, silence handling, and integration with recorder/hands-free output.
- Update durable docs/memory if the behavior change is implemented.

## Telemetry And Diagnostics

What can fail or become ambiguous:
- Quiet captures may still be too low if they are near silence or mostly noise.
- Aggressive boosting could clip speech or amplify background noise.
- Operators need to know whether a transcription used app-side gain correction without recording raw audio or transcript text.

Signals:
- Emit bounded `audio.normalization_applied` telemetry before transcription when gain changes the audio.
- Include mode/source, gain, input/output RMS, input/output peak, audio sample count, and audio duration rounded to bounded numeric values.
- Do not include raw audio, transcript text, prompts, hotwords, device names, or user content.

Verification:
- Unit tests for normalization math and call sites.
- Run targeted recorder/hands-free/main tests, then the full test suite if practical.
