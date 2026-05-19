# Closeout
- Final status: implemented.
- Related checkpoint: `.agents/checkpoints/2026-05-19-whisper-processor-fallback-checkpoints.md`.
- Implementation commits: `3f99911` (`Fix default Whisper processor loading`) and `58545c8` (`Record Whisper processor fallback checkpoint`).
- Merge commit: none; local `main` fast-forwarded to `58545c8`.
- Verification: `uv run --with pytest pytest` passed with 133 tests; smoke check confirmed the default MLX Whisper model gets a `WhisperProcessor` fallback.
- Worktree and branch cleanup: removed `.agents/worktrees/fix-whisper-processor-fallback` and deleted local branch `fix-whisper-processor-fallback`.
- Summary: WhisCode now repairs the default MLX Whisper model by attaching the upstream OpenAI Whisper processor at startup, with fail-fast errors and bounded telemetry for unsupported missing-processor cases.

# Whisper Processor Fallback Plan

## Status
Active.

## Problem
Running `uv run whiscode` with the default `mlx-community/whisper-large-v3-turbo` model loads MLX weights but transcription fails with `Processor not found. Make sure the model was loaded with a HuggingFace processor.`

The cached MLX community model snapshot contains only `config.json` and `weights.safetensors`, while the installed `mlx_audio` Whisper implementation expects a Hugging Face `WhisperProcessor` to provide tokenizer metadata.

## Approach
- Add a load-time helper that detects loaded Whisper models with a missing processor.
- For default MLX community Whisper repo names, derive the corresponding upstream OpenAI processor repo and attach `WhisperProcessor.from_pretrained(...)`.
- Keep the helper narrow: only repair missing Whisper processors and leave models that already loaded a processor untouched.
- Emit bounded telemetry for fallback attempts, success, skip, and failure without logging model paths, prompts, audio, or user content.
- Add focused unit tests for default processor mapping and helper behavior.

## Verification
- Run targeted CLI/model-loading unit tests.
- Run the full test suite if feasible.
- Optionally run a minimal load check that verifies the default model has a processor after fallback without recording audio.

## Telemetry And Diagnostics
The behavior can fail if the derived upstream processor repo is unreachable, unavailable, or incompatible. Add stable telemetry events around fallback stages:

- `model.processor_fallback_attempted`
- `model.processor_fallback_completed`
- `model.processor_fallback_failed`
- `model.processor_fallback_skipped`

Properties stay bounded to model family/source/outcome/error type and must not include raw audio, prompts, transcripts, tokens, or full provider payloads.
