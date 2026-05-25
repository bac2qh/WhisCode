# Add MLX VibeVoice ASR Backend To WhisCode

## Summary
Add a first-class `mlx-vibevoice` ASR backend so the normal app command can use the downloaded MLX VibeVoice models directly, with existing hotwords flowing into VibeVoice's `context` parameter. Keep `mlx-whisper` as the default backend, but make the VibeVoice command simple and local.

## Key Changes
- Add a new in-process backend, selected with `uv run whiscode --asr-backend mlx-vibevoice`.
- Default the model path from `WHISCODE_MLX_VIBEVOICE_MODEL`, falling back to `~/Documents/models/mlx-community/VibeVoice-ASR-8bit`, and allow override with `--mlx-vibevoice-model`.
- Reuse the existing hotwords file unchanged. Build VibeVoice context from hotwords, optional `--prompt`, and a short technical-dictation hint.
- Normalize MLX-Audio VibeVoice output into one pasteable transcript string by joining parsed segment text with single spaces, with raw text fallback using VibeVoice chunk parsing behavior.
- Add the same backend option to `whiscode-benchmark-asr` for latency/quality comparison.

## Telemetry / Debuggability
- Emit bounded events for `mlx_vibevoice.model_load_started/completed/failed` and `mlx_vibevoice.transcription_started/completed/failed`.
- Include only safe fields: model basename or repo/path label, audio duration, hotword count, whether `--prompt` was present, context length, output length, duration, and error type.
- Do not log audio, transcripts, prompts, hotword contents, full provider payloads, or raw decoded text.

## Docs
- Update README and `wiki/pages/asr-backends.md` with the new backend command, default 8-bit model path/env override, BF16 override command, and the difference from the current CrispASR/GGUF path.
- Note that MLX-Audio may fetch/cache the intended `Qwen/Qwen2.5-7B` tokenizer if it is not already present.

## Tests
- Add unit tests for default model path/env var resolution, VibeVoice context building, backend transcription invocation, segment joining/raw fallback, safe telemetry, CLI parsing, and benchmark backend selection.
- Run `uv run --with pytest pytest tests/test_mlx_vibevoice_asr.py tests/test_main_cli.py tests/test_benchmark_asr.py`.
- Run `uv run --with pytest pytest`.
- Run `uv run python -m compileall whiscode`.

## Assumptions
- Do not make VibeVoice the global default yet; use explicit `--asr-backend mlx-vibevoice` while validating daily latency and quality.
- Use 8-bit as the default VibeVoice model because it is the practical quantized candidate.
- No CrispASR changes are needed; CrispASR remains available for GGUF experiments.
