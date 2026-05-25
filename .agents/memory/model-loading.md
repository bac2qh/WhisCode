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

## 2026-05-24
- WhisCode added an optional `llama-cpp` ASR backend while keeping `mlx-whisper` as the default compatibility backend.
- The llama.cpp backend uses a warm local `llama-server` process only when `--asr-backend llama-cpp` is selected. It reuses an existing server when reachable, auto-starts the configured source-built server otherwise, and terminates only the child process it owns.
- The default local Qwen3-ASR paths target LM Studio's `ggml-org/Qwen3-ASR-1.7B-GGUF` cache: `Qwen3-ASR-1.7B-Q8_0.gguf` with the available `mmproj-Qwen3-ASR-1.7B-bf16.gguf`.
- Hands-free detection, hotkey recording, overlays, postprocessing, replacements, optional refinement, stats, and text injection remain independent from the ASR backend.
- WhisCode added an optional `crispasr` ASR backend for VibeVoice ASR GGUF while keeping `mlx-whisper` as the default compatibility backend and leaving the llama.cpp/Qwen path unchanged.
- The CrispASR backend uses a warm source-built `crispasr` server only when `--asr-backend crispasr` is selected. It reuses a reachable server, auto-starts the configured sibling executable otherwise, sends final recordings to `/v1/audio/transcriptions`, and terminates only the child process it owns.
- CrispASR defaults can be set with `WHISCODE_CRISPASR_BIN` and `WHISCODE_CRISPASR_MODEL`; the recommended VibeVoice F16 GGUF path is `~/Documents/models/vibevoice-asr-GGUF/vibevoice-asr-f16.gguf`.
- The current CrispASR checkout builds the executable with `cmake --build build --target crispasr-cli`; the `crispasr` target itself builds the library.
- VibeVoice responses from CrispASR can surface as chunk lists even when WhisCode expects a single transcript. WhisCode now normalizes stringified and native chunk lists by joining non-empty `Content` values with spaces, and drops `Start`, `End`, and `Speaker` metadata before postprocessing, refinement, hands-free command handling, or text injection.
- When VibeVoice emits malformed chunk-list output, WhisCode now records bounded `crispasr.response_shape_invalid` telemetry with structure counts only, then fails with `CrispAsrError`.
- Official VibeVoice-ASR examples and the Transformers processor use a list of speaker segments with `Start`, `End`, `Speaker`, and `Content`; raw decoded output can be prefixed with `assistant` and transcription-only mode joins `Content` fields with spaces. WhisCode now accepts direct JSON lists, `assistant`/special-token wrapped raw lists, and native list objects.
- For local debugging, malformed or recovered CrispASR/VibeVoice chunk output writes the original provider response body to `crispasr-raw-responses.jsonl` next to runtime telemetry. The raw debug file can include transcript/provider output text, while routine telemetry still avoids content.
- `cstr/vibevoice-asr-GGUF` lists `vibevoice-asr-q4_k.gguf` as the recommended default and `vibevoice-asr-f16.gguf` as reference quality. Local WhisCode smoke tests found Q4 much smaller (4.5G local file versus 16G F16) and faster on an 8.173s synthetic sample (0.895s versus 1.864s warm F16), but only slightly faster on a 1.865s sample (0.924s versus 1.014s warm F16). Treat Q4 as useful for disk/memory and possibly longer recordings, not a guaranteed major improvement for short dictation.

## 2026-05-25
- Documentation now records that WhisCode's current CrispASR/VibeVoice integration is a blocking warm-server `/v1/audio/transcriptions` request and cannot expose concrete stage, token, percentage, or FPS progress until CrispASR provides a progress-bearing server API or event stream.
