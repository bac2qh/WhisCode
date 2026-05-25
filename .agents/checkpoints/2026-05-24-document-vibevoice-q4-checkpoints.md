# Document VibeVoice Q4 Tradeoff Checkpoints

## 2026-05-24 Start
- Main project root: `/Users/xin/Documents/repos/WhisCode`.
- Task worktree: `/Users/xin/Documents/repos/WhisCode/.agents/worktrees/document-vibevoice-q4`.
- Branch: `document-vibevoice-q4`.
- User direction: document that the recommended 4-bit VibeVoice GGUF did not look meaningfully faster for short dictation, though it is much smaller.
- Source check: the cstr Hugging Face model card lists `vibevoice-asr-q4_k.gguf` as the recommended default and `vibevoice-asr-f16.gguf` as reference quality.
- Local benchmark evidence: Q4 file was 4.5G locally versus F16 16G; Q4 and F16 both transcribed the synthetic test samples correctly. On a 1.865s sample, Q4 was 0.924s RTF 0.496 and warm F16 was 1.014s RTF 0.544. On an 8.173s sample, Q4 was 0.895s RTF 0.109 and warm F16 was 1.864s RTF 0.228.
- Telemetry/debuggability decision: not applicable, documentation only.
- Immediate next step: update README, wiki, and memory with concise guidance, then verify and close out.

## 2026-05-24 Implementation Notes
- Implementation commit: `817a5dd6149a197ac490898a2d943a0f6b24779b`.
- Documented the Q4/F16 tradeoff in `README.md` and `wiki/pages/asr-backends.md`.
- Updated model-loading memory and the memory log with the durable local benchmark finding.
- Verification passed:
  - `git diff --check`
  - `rg -n "vibevoice-asr-q4_k|real-time factor|Q4" README.md wiki/pages/asr-backends.md .agents/memory/model-loading.md`
- Immediate next step: commit checkpoint hash bookkeeping, archive the plan, merge back to local `main`, and clean up the task worktree.
