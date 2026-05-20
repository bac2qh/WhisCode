# Model Loading

## 2026-05-19
- The `mlx-community/whisper-large-v3-turbo` model can load MLX weights without bundled Hugging Face processor/tokenizer files. `mlx_audio` then raises `Processor not found` during transcription.
- WhisCode now repairs that turbo model at startup by attaching `WhisperProcessor.from_pretrained("openai/whisper-large-v3-turbo")` when the loaded Whisper model has no processor.
- The fallback is intentionally narrow and fail-fast. Unknown Whisper models without processors now exit during model load with a clear compatibility error instead of recording audio and failing only after transcription starts.
- Added bounded diagnostics for processor fallback attempts, completion, skip, and failure; telemetry does not include raw audio, prompts, transcripts, tokens, or full model paths.
- Later on 2026-05-19, the CLI default returned to `mlx-community/whisper-large-v3-mlx` to match the installer and prefer the larger non-turbo model. The turbo processor fallback remains for users who explicitly pass the turbo model.

## 2026-05-20
- The current default `mlx-community/whisper-large-v3-mlx` also ships without Hugging Face processor/tokenizer files in the local MLX repo, so startup failed with WhisCode's missing-processor compatibility error.
- WhisCode now maps the default large-v3 MLX repo to `openai/whisper-large-v3` while retaining the turbo repo mapping to `openai/whisper-large-v3-turbo`.
- The fallback remains exact and fail-fast for unknown Whisper repos to avoid silently pairing a model with the wrong tokenizer.
