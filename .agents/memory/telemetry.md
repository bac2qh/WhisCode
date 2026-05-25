# Telemetry

## 2026-05-24
- WhisCode runtime telemetry is now enabled by default for hotkey and hands-free runs, with `--no-telemetry` as the opt-out and `--telemetry-path` for custom local JSONL destinations.
- The default destination is `~/Library/Logs/WhisCode/events.jsonl`, matching macOS user log placement better than `~/.config` or volatile `/tmp`.
- The overhead is expected to be low because hotkey-mode runs emit bounded lifecycle, backend, recording, and transcription events only at workflow transitions; hands-free mode already used throttled summaries for high-frequency detector activity.
- CrispASR/VibeVoice malformed chunk normalization now emits `crispasr.response_shape_invalid` before failing. The event records bounded structure such as parse stage, text type, list length, and missing or non-string `Content` counts.
- Routine telemetry must not include raw audio, transcript text, prompts, hotword contents, chunk `Content`, provider payloads, typed text, secrets, or full paths.
- After the user explicitly accepted local debug output, malformed CrispASR/VibeVoice response debugging writes original provider response bodies to `crispasr-raw-responses.jsonl` next to runtime telemetry. That file is local-only and can contain transcript or provider output text; routine shape telemetry remains bounded and content-free.
- Recording queue diagnostics now emit bounded `recording.queue_full`, `recording.queued`, `transcription.queue_started`, `transcription.queue_completed`, `transcription.queue_failed`, and `transcript_recovery_file_written` events. These include queue/job metadata only; transcript text is intentionally written only to `/tmp/whiscode-last-transcripts.txt`.
