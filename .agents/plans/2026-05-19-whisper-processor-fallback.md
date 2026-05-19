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
