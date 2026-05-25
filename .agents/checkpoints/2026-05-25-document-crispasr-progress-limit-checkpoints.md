# Document CrispASR/VibeVoice Progress Limitation Checkpoints

## 2026-05-25 Initial State

- Plan saved in `.agents/plans/2026-05-25-document-crispasr-progress-limit.md`.
- Main checkout was clean before creating task worktree `doc-crispasr-progress-limit`.
- User requested README documentation for the current CrispASR/VibeVoice progress limitation and asked to push after closeout.
- Scope is documentation-only: README and current-state wiki docs, with no runtime behavior or telemetry changes.
- Telemetry/debuggability decision: telemetry not applicable because this change only documents existing behavior.
- Immediate next step: update README/wiki docs, then run documentation verification.

## 2026-05-25 Documentation Ready

- Done: Updated `README.md`, `wiki/pages/asr-backends.md`, `wiki/pages/recording-overlay.md`, and `wiki/log.md` to document that the current CrispASR/VibeVoice warm-server `/v1/audio/transcriptions` path is blocking and does not expose concrete in-flight progress.
- Done: Updated model-loading and recording-overlay project memory with the same backend limitation.
- Immediate next step: Commit the documentation update, record the commit hash, then close out and push `main`.
- Key decisions: Keep this documentation-only. Do not add estimated progress or change telemetry because the user asked to document the limitation, not implement a workaround.
- Verification: `git diff --check` passed; `rg -n "blocking full-recording|does not expose|cannot show|backend-dependent|CrispASR/VibeVoice warm-server" README.md wiki .agents/memory` found the expected README, wiki, and memory mentions.
- Commits: Pending.
