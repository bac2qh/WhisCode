# Closeout 2026-05-24
- Final status: `implemented`.
- Related checkpoint: `.agents/checkpoints/2026-05-24-crispasr-raw-response-debug-checkpoints.md`.
- Implementation commits: `dc15f8c` (`Log malformed CrispASR responses`) and `b6b28cc` (`Record CrispASR raw debug checkpoint`).
- Merge result: fast-forwarded local `main`; no merge commit was created.
- Verification: `uv run --with pytest pytest tests/test_crispasr_asr.py` passed; `uv run --with pytest pytest tests/test_crispasr_asr.py tests/test_telemetry.py` passed; `uv run python -m compileall whiscode` passed.
- Cleanup: removed task worktree `.agents/worktrees/crispasr-raw-response-debug` and deleted local branch `crispasr-raw-response-debug`; unrelated worktree `.agents/worktrees/env-llama-paths` was left untouched.
- Shipped: malformed CrispASR/VibeVoice chunk responses now preserve the original provider response body in local-only `crispasr-raw-responses.jsonl`, parser handling now covers official `assistant`/special-token wrapped VibeVoice raw output, and best-effort `Content` recovery can turn common JSON-ish failures into usable transcript text.

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
