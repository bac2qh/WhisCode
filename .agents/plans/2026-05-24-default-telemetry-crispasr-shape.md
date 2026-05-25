# Default Telemetry And CrispASR Shape Diagnostics

## Summary
Enable local JSONL telemetry by default for normal WhisCode runtime, not only hands-free mode, and add a bounded diagnostic for malformed CrispASR/VibeVoice chunk output.

## Scope
- Enable runtime telemetry unless `--no-telemetry` is passed.
- Keep `--telemetry-path` behavior unchanged.
- Keep telemetry local JSONL only.
- Add safe CrispASR response-shape telemetry when VibeVoice chunk normalization fails.
- Avoid logging raw audio, transcript text, prompts, hotwords, full provider payloads, or chunk content.
- Update tests and docs for the default telemetry behavior and new diagnostic event.

## Telemetry / Debuggability
- This change directly affects diagnostics.
- Hotkey-mode runs should emit existing lifecycle/backend/recording/transcription events by default, allowing failures like a malformed CrispASR response to be correlated by session and PID.
- Add a bounded `crispasr.response_shape_invalid` event with properties such as text type, parse stage, status/outcome, list length, item type, missing `Content` count, non-string `Content` count, or a safe string prefix class. Do not include transcript text, chunk content, prompts, raw payload snippets, or high-cardinality provider data.
- Existing `crispasr.transcription_failed` and app-level `transcription.failed` continue to report failure timing and `CrispAsrError`.
- Verification must cover enabled-by-default telemetry selection and the new CrispASR shape diagnostic.

## Verification
- `uv run --with pytest pytest tests/test_crispasr_asr.py tests/test_main_cli.py tests/test_telemetry.py`
- `uv run python -m compileall whiscode`

## Assumptions
- Default local telemetry overhead is acceptable because hotkey-mode event volume is low and writes are append-only JSONL lines.
- Privacy boundaries are more important than storing raw malformed provider output; shape diagnostics should explain parser failures without transcript content.
