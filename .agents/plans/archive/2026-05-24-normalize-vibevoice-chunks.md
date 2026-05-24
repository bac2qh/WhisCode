# Closeout 2026-05-24
- Final status: `implemented`.
- Related checkpoint: `.agents/checkpoints/2026-05-24-normalize-vibevoice-chunks-checkpoints.md`.
- Implementation commit: `3c88b43` (`Normalize CrispASR VibeVoice chunk text`).
- Closeout prerequisite commit: `b749fe4` (`Add main branch closeout lock helper`).
- Merge result: fast-forwarded local `main` to `b749fe4`; no merge commit was created.
- Verification: `uv run --with pytest pytest tests/test_crispasr_asr.py` passed; `bash -n .agents/scripts/main-branch-lock.sh` passed.
- Cleanup: removed task worktree `.agents/worktrees/normalize-vibevoice-chunks` and deleted local branch `normalize-vibevoice-chunks`; unrelated worktree `.agents/worktrees/env-llama-paths` was left untouched.
- Shipped: CrispASR/VibeVoice chunk lists are normalized into a single transcript by joining non-empty `Content` fields and dropping chunk metadata before user-visible handling.

# Normalize VibeVoice Chunk Output

## Summary
Normalize CrispASR/VibeVoice transcription responses before WhisCode sends text to paste, refinement, or hands-free command handling. CrispASR may return VibeVoice's structured chunk list even when the caller expects text; WhisCode should expose only joined chunk content.

## Scope
- Update `extract_crispasr_text` in `whiscode/crispasr_asr.py`.
- Preserve plain text response handling.
- Support `response["text"]` as a JSON string containing a list of chunk objects.
- Support `response["text"]` as a native list of chunk objects.
- Join non-empty chunk `Content` values with a single space.
- Reject empty or malformed VibeVoice chunk lists with `CrispAsrError`.
- Add focused unit tests in `tests/test_crispasr_asr.py`.

## Telemetry / Debuggability
- No new telemetry event is needed for this local response-normalization change.
- Existing `crispasr.transcription_completed` reports bounded output length and empty/text outcome after normalization.
- Existing `crispasr.transcription_failed` reports `CrispAsrError` when malformed or empty structured chunks cannot be normalized.
- The implementation must not add raw transcript text, chunk contents, prompts, paths, provider payloads, or chunk metadata to telemetry.
- Verification will include unit tests for successful chunk normalization and failure cases.

## Verification
- Run `uv run --with pytest pytest tests/test_crispasr_asr.py`.

## Assumptions
- VibeVoice chunk objects expose user-visible text in `Content`.
- Single-space joining is preferred for dictation paste behavior.
- `Start`, `End`, and `Speaker` fields are metadata and should not appear in user-visible output.
