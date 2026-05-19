# Whisper Processor Fallback Checkpoints

## 2026-05-19 Start
- Done: Reproduced the failure path from the user-provided run log and inspected local cache contents. The default MLX repo snapshot only has weights/config and no processor/tokenizer files.
- Immediate next step: Implement a narrow load-time fallback that attaches the upstream OpenAI Whisper processor when the loaded MLX Whisper model lacks one.
- Decisions: Use a task worktree `fix-whisper-processor-fallback` under the main project `.agents/worktrees/` before editing tracked files.
- Verification: Not run yet.

## 2026-05-19 Implementation
- Done: Added `ensure_whisper_processor` to attach `openai/whisper-large-v3-turbo` as the processor source for the default `mlx-community/whisper-large-v3-turbo` model when `mlx_audio` loads weights without a processor.
- Done: Model load now suppresses only the known pre-fallback `mlx_audio` warning and exits early with a clear error if a Whisper model has no processor and no supported fallback.
- Done: Added unit coverage for default source mapping, fallback attachment, skip behavior, and fail-fast behavior.
- Commit: `3f99911` (`Fix default Whisper processor loading`).
- Decisions: Kept the fallback map exact instead of deriving processor repos for arbitrary MLX Whisper variants, because a wrong tokenizer source would be harder to debug than an explicit compatibility error.
- Diagnostics: Added bounded telemetry events for processor fallback attempted, completed, failed, and skipped states.
- Verification: `uv run --with pytest pytest` passed with 133 tests. A smoke check loaded `mlx-community/whisper-large-v3-turbo`, ran `ensure_whisper_processor`, and confirmed `_processor` is a `WhisperProcessor`.
- Immediate next step: Commit checkpoint hash bookkeeping, merge the task branch to local `main`, archive the plan, and remove the task worktree/branch.
