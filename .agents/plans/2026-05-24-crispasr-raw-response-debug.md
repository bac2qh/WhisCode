# CrispASR Raw Response Debugging

## Summary
Capture the original CrispASR response body when VibeVoice returns malformed chunk-list text, and harden the local normalizer with best-effort recovery for common JSON-ish chunk failures.

## Scope
- Write malformed CrispASR transcription responses to a local debug JSONL file.
- Use `~/Library/Logs/WhisCode/crispasr-raw-responses.jsonl` by default, or a sibling file next to a custom telemetry path.
- Keep normal telemetry bounded, but include the raw-debug filename in shape diagnostics.
- Preserve strict parsing for valid VibeVoice chunk lists.
- Add best-effort `Content` extraction for malformed chunk-list strings when `json.loads` fails.
- Add focused parser and raw-debug tests.
- Verify VibeVoice-ASR output shape against primary Microsoft/Hugging Face documentation and source examples.

## Telemetry / Debuggability
- This change intentionally logs provider response content for local debugging after explicit user direction.
- Raw response logging is local-only and only happens for malformed CrispASR/VibeVoice nested chunk strings, not every successful transcription.
- The normal telemetry event remains shape-oriented and should not include raw content.
- The raw debug file can contain transcript text and provider response content; docs must state that plainly.

## Verification
- `uv run --with pytest pytest tests/test_crispasr_asr.py tests/test_telemetry.py`
- `uv run python -m compileall whiscode`

## Assumptions
- User accepts raw local response logging because this is for debugging their local dictation workflow.
- Best-effort recovery should handle common malformed chunk strings, especially unescaped quotes or control characters inside `Content`.
