# CrispASR Raw Response Debugging Checkpoints

## 2026-05-24 Start
- Main project root: `/Users/xin/Documents/repos/WhisCode`.
- Task worktree: `/Users/xin/Documents/repos/WhisCode/.agents/worktrees/crispasr-raw-response-debug`.
- Branch: `crispasr-raw-response-debug`.
- User direction: log the original CrispASR output for local debugging and re-check parser robustness.
- Recent evidence: telemetry showed `crispasr.response_shape_invalid` at `stage=json_parse`, `text_type=str`, `prefix_class=list_object`, `string_length=961`, meaning the outer HTTP JSON parsed but nested VibeVoice chunk-list text did not.
- Telemetry/debuggability decision: write raw malformed provider responses to a local debug file because the user explicitly accepts local raw output logging; keep normal telemetry bounded.
- Immediate next step: implement raw response capture, best-effort parser recovery, tests, docs, and memory updates.

## 2026-05-24 Implementation Notes
- Confirmed expected VibeVoice-ASR shape from primary sources: Microsoft/Hugging Face docs describe structured Who/When/What output, the HF model card shows raw output as `Start`/`End`/`Speaker`/`Content` segment dictionaries plus a parsed list-of-dicts mode, and the Transformers processor strips an `assistant` prefix then joins `Content` values for transcription-only output.
- Implemented raw CrispASR response preservation inside transcription responses and a local-only malformed-response debug JSONL writer.
- Implemented parser support for native list chunks, direct JSON chunk-list strings, `assistant`/special-token wrapped raw VibeVoice strings, and best-effort `Content` scanning when nested JSON is malformed.
- Verification passed:
  - `uv run --with pytest pytest tests/test_crispasr_asr.py`
  - `uv run --with pytest pytest tests/test_crispasr_asr.py tests/test_telemetry.py`
  - `uv run python -m compileall whiscode`
- Immediate next step: commit implementation, record commit hash, and close out.
