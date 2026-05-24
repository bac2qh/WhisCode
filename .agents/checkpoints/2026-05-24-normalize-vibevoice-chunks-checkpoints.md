# Normalize VibeVoice Chunk Output Checkpoints

## 2026-05-24 Start
- Main project root: `/Users/xin/Documents/repos/WhisCode`.
- Task worktree: `/Users/xin/Documents/repos/WhisCode/.agents/worktrees/normalize-vibevoice-chunks`.
- Branch: `normalize-vibevoice-chunks`.
- Source intent: implement the provided plan to normalize CrispASR/VibeVoice chunk arrays into a single transcript string before WhisCode paste/refine/hands-free handling.
- Initial code finding: `extract_crispasr_text` currently returns `str(response["text"] or "").strip()`, so structured VibeVoice chunks can leak metadata to user-visible output.
- Telemetry decision: no new signal is required; existing CrispASR completion/failure telemetry observes normalized output length or `CrispAsrError` without exposing transcript content or chunk metadata.
- Implemented:
  - `extract_crispasr_text` now preserves plain strings, parses VibeVoice chunk-list strings, accepts native chunk lists, and joins non-empty `Content` fields with single spaces.
  - Empty chunk lists, chunks without usable content, missing `Content`, non-dict chunk items, and malformed chunk-list JSON now raise `CrispAsrError`.
  - `_request_json` now preserves non-dict parsed JSON values so top-level JSON chunk arrays can reach the extractor as native lists.
  - Added focused unit tests for plain text, stringified chunks, native chunks, mixed English/Chinese chunks, and empty/malformed chunk failures.
- Verification:
  - `uv run --with pytest pytest tests/test_crispasr_asr.py` passed: 20 tests.
- Implementation commit: `3c88b43` (`Normalize CrispASR VibeVoice chunk text`).
- Closeout preparation:
  - The repo did not have `.agents/scripts/main-branch-lock.sh`, so added the standard main-branch lock helper before running local `main` closeout.
  - `bash -n .agents/scripts/main-branch-lock.sh` passed.
- Immediate next step: commit the lock-helper/checkpoint bookkeeping, then run main closeout under the helper.
