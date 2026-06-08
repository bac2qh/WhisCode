# Telemetry

## 2026-05-24
- WhisCode runtime telemetry is now enabled by default for hotkey and hands-free runs, with `--no-telemetry` as the opt-out and `--telemetry-path` for custom local JSONL destinations.
- The default destination is `~/Library/Logs/WhisCode/events.jsonl`, matching macOS user log placement better than `~/.config` or volatile `/tmp`.
- The overhead is expected to be low because hotkey-mode runs emit bounded lifecycle, backend, recording, and transcription events only at workflow transitions; hands-free mode already used throttled summaries for high-frequency detector activity.
- CrispASR/VibeVoice malformed chunk normalization now emits `crispasr.response_shape_invalid` before failing. The event records bounded structure such as parse stage, text type, list length, and missing or non-string `Content` counts.
- Routine telemetry must not include raw audio, transcript text, prompts, hotword contents, chunk `Content`, provider payloads, typed text, secrets, or full paths.
- After the user explicitly accepted local debug output, malformed CrispASR/VibeVoice response debugging writes original provider response bodies to `crispasr-raw-responses.jsonl` next to runtime telemetry. That file is local-only and can contain transcript or provider output text; routine shape telemetry remains bounded and content-free.
- Recording queue diagnostics now emit bounded `recording.queue_full`, `recording.queued`, `transcription.queue_started`, `transcription.queue_completed`, and `transcription.queue_failed` events. These include queue/job metadata only; transcript text is intentionally kept out of telemetry and shown in copy-friendly stdout blocks.

## 2026-05-25
- The optional `mlx-vibevoice` backend emits bounded `mlx_vibevoice.model_load_*` and `mlx_vibevoice.transcription_*` telemetry. These events use safe model labels, durations, audio length, hotword counts, prompt presence, context length, output length, and error types.
- MLX VibeVoice telemetry intentionally excludes raw audio, transcript text, prompts, hotword contents, full model paths, tokenizer payloads, and raw model output.

## 2026-06-06
- Hands-free setup emits `handsfree.tail_seconds_resolved` after resolving end-tail trim length. The payload is bounded to source (`inferred`, `explicit`, or `fallback`), rounded resolved seconds, reference counts, valid active-span counts, and a small fallback reason enum; it excludes raw audio, phrase text, transcripts, sample data, and paths.

## 2026-06-08
- Send Chunk emits bounded `send_chunk.requested`, `send_chunk.queued`, `send_chunk.restarted`, and `send_chunk.rejected` events with mode/source, local job IDs, queue depth, timing, and suffix length only. It does not emit raw audio, transcript text, prompts, hotwords, provider payloads, or typed content.
- Hands-free chunk support emits bounded `handsfree.chunk_detected` and `handsfree.chunk_tail_seconds_resolved` events. The tail-resolution payload mirrors end-tail resolution fields and excludes phrase text, sample paths, raw audio, transcripts, and typed text.
