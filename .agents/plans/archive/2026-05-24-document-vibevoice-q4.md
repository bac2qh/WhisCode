# Closeout 2026-05-24
- Final status: `implemented`.
- Related checkpoint: `.agents/checkpoints/2026-05-24-document-vibevoice-q4-checkpoints.md`.
- Implementation commits: `817a5dd` (`Document VibeVoice Q4 tradeoff`) and `f88ae08` (`Record VibeVoice Q4 docs checkpoint`).
- Merge result: fast-forwarded local `main`; no merge commit was created.
- Verification: `git diff --check` passed; `rg -n "vibevoice-asr-q4_k|real-time factor|Q4" README.md wiki/pages/asr-backends.md .agents/memory/model-loading.md` found the expected documentation references.
- Cleanup: removed task worktree `.agents/worktrees/document-vibevoice-q4` and deleted local branch `document-vibevoice-q4`; unrelated worktree `.agents/worktrees/env-llama-paths` was left untouched.
- Shipped: documented that Q4 is much smaller and can help longer recordings, but local short-dictation latency was not meaningfully better than warm F16.

# Document VibeVoice Q4 Tradeoff

## Summary
Document the observed VibeVoice Q4_K GGUF tradeoff for WhisCode's CrispASR backend.

## Scope
- Add a concise note to the CrispASR README section about the Q4 and F16 GGUF choices.
- Update the ASR backend wiki with the local benchmark results and practical recommendation.
- Update project memory with the durable finding.

## Telemetry / Debuggability
Telemetry not applicable. This is a documentation-only change that does not alter runtime behavior, event contents, logging paths, or diagnostic signals.

## Verification
- Review the changed Markdown.
- `rg -n "vibevoice-asr-q4_k|real-time factor|Q4" README.md wiki/pages/asr-backends.md .agents/memory/model-loading.md`

## Assumptions
- The documented benchmark is a local smoke result, not a general performance guarantee.
- Keep F16 as the quality-oriented default in docs while describing Q4 as a memory/disk-saving option that may be faster on longer recordings.
