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
- Commit: pending.
- Decisions: Did not derive OpenAI processor repos from arbitrary MLX model names; unsupported missing-processor Whisper models still fail fast with the clear compatibility error.
- Diagnostics: Reused existing bounded `model.processor_fallback_*` telemetry events; no new telemetry names were needed.
- Verification: `uv run --with pytest pytest tests/test_main_cli.py` passed with 16 tests. A non-recording smoke check loaded `mlx-community/whisper-large-v3-mlx`, ran `ensure_whisper_processor`, and confirmed `_processor` is a `WhisperProcessor`. `uv run --with pytest pytest` passed with 134 tests.
- Immediate next step: Commit the implementation and bookkeeping, then close out by merging back to local `main`.
