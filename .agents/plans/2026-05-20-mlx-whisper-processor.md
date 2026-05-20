# MLX Whisper Processor Plan

## Status
Active.

## Problem
Running `uv run whiscode` with the current default `mlx-community/whisper-large-v3-mlx` model exits during startup because the loaded MLX Whisper model has no Hugging Face processor/tokenizer files and WhisCode only knows how to repair the turbo MLX repo.

## Approach
- Extend the existing exact fallback map so `mlx-community/whisper-large-v3-mlx` uses the upstream `openai/whisper-large-v3` processor.
- Keep unsupported missing-processor Whisper models fail-fast with the existing compatibility error.
- Add focused unit coverage for the default model mapping and fallback attachment.
- Update durable model-loading memory after verification.

## Verification
- Run targeted CLI/model-loading tests.
- Run the full test suite if feasible.
- Run a minimal startup/model-load smoke check if feasible without recording audio.

## Telemetry And Diagnostics
The existing processor fallback telemetry remains the right diagnostic surface: `model.processor_fallback_attempted`, `model.processor_fallback_completed`, `model.processor_fallback_failed`, and `model.processor_fallback_skipped`. This change only adds a supported mapping, so telemetry properties should remain bounded to model family/source/outcome/error type and must not include audio, prompts, transcripts, tokens, credentials, or full provider payloads.
