# Telemetry

## 2026-05-24
- WhisCode runtime telemetry is now enabled by default for hotkey and hands-free runs, with `--no-telemetry` as the opt-out and `--telemetry-path` for custom local JSONL destinations.
- The default destination is `~/Library/Logs/WhisCode/events.jsonl`, matching macOS user log placement better than `~/.config` or volatile `/tmp`.
- The overhead is expected to be low because hotkey-mode runs emit bounded lifecycle, backend, recording, and transcription events only at workflow transitions; hands-free mode already used throttled summaries for high-frequency detector activity.
- CrispASR/VibeVoice malformed chunk normalization now emits `crispasr.response_shape_invalid` before failing. The event records bounded structure such as parse stage, text type, list length, and missing or non-string `Content` counts.
- Telemetry must not include raw audio, transcript text, prompts, hotword contents, chunk `Content`, provider payloads, typed text, secrets, or full paths.
