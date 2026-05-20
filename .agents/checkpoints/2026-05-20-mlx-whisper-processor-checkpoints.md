# MLX Whisper Processor Checkpoints

## 2026-05-20 Start
- Done: Reviewed project memory and confirmed the previous fallback only documented support for `mlx-community/whisper-large-v3-turbo`.
- Done: Created task worktree `.agents/worktrees/fix-mlx-whisper-processor` on branch `fix-mlx-whisper-processor`.
- Immediate next step: Extend the exact processor fallback map for the current default model and add tests.
- Decisions: Keep the fix scoped to known MLX Whisper repos instead of deriving arbitrary processor names.
- Verification: Not run yet.

## 2026-05-20 Implementation
- Done: Added `mlx-community/whisper-large-v3-mlx` to the exact Whisper processor fallback map with upstream processor source `openai/whisper-large-v3`.
- Done: Preserved the existing `mlx-community/whisper-large-v3-turbo` to `openai/whisper-large-v3-turbo` fallback.
- Done: Added unit coverage for the current default mapping and kept turbo mapping coverage separate.
- Commit: `ba10df1` (`Fix default MLX Whisper processor fallback`).
- Decisions: Did not derive OpenAI processor repos from arbitrary MLX model names; unsupported missing-processor Whisper models still fail fast with the clear compatibility error.
- Diagnostics: Reused existing bounded `model.processor_fallback_*` telemetry events; no new telemetry names were needed.
- Verification: `uv run --with pytest pytest tests/test_main_cli.py` passed with 16 tests. A non-recording smoke check loaded `mlx-community/whisper-large-v3-mlx`, ran `ensure_whisper_processor`, and confirmed `_processor` is a `WhisperProcessor`. `uv run --with pytest pytest` passed with 134 tests.
- Immediate next step: Commit checkpoint hash bookkeeping, then close out by merging back to local `main`.

## 2026-05-20 Closeout
- Done: Fast-forwarded local `main` to `8af9a25`; no merge commit was created.
- Done: Moved the plan to `.agents/plans/archive/2026-05-20-mlx-whisper-processor.md` and added the closeout note.
- Done: The repo has no `.agents/scripts/main-branch-lock.sh`; closeout proceeded with clean task and main worktrees.
- Done: Removed `.agents/worktrees/fix-mlx-whisper-processor` and deleted local branch `fix-mlx-whisper-processor`.
- Verification: No additional tests were needed after archival-only closeout edits; implementation verification remains the targeted CLI tests, default-model smoke check, and full suite listed above.
- Immediate next step: None for this plan.
