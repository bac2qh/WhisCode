# Audio Capture And Normalization

## 2026-05-21
- Added bounded pre-transcription gain normalization after a low microphone input report.
- WhisCode still captures raw `float32` PortAudio samples and keeps raw audio for hands-free wake/end/command detection so existing detector thresholds and enrolled references stay comparable.
- Hotkey and hands-free recording audio is normalized before Whisper transcription when RMS is below the target level but above the near-silence floor.
- The normalizer targets RMS `0.08`, skips audio below RMS `0.001`, caps boost at `8x`, and peak-limits output at `0.95`.
- When a boost is applied, local telemetry emits `audio.normalization_applied` with bounded source, gain, RMS, peak, sample count, and duration metadata only. It does not emit raw audio, transcripts, prompts, hotwords, device names, or user content.
