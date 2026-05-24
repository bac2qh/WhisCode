# Optional llama.cpp ASR Backend For WhisCode

## Summary

Add llama.cpp/Qwen3-ASR as an opt-in transcription backend while preserving WhisCode's current app behavior. The only user-visible workflow difference is where transcription happens after audio is recorded.

Default behavior remains unchanged:

```bash
uv run whiscode
```

Opt-in llama.cpp mode:

```bash
uv run whiscode --asr-backend llama-cpp
```

Both modes keep the same hotkeys, hands-free wake/end detection, overlay, terminal output, postprocessing, replacements, optional refinement, stats, telemetry, and text injection.

## Key Changes

- Add an ASR backend boundary around the existing transcription step:
  - `mlx-whisper`: current in-process MLX Whisper implementation and default.
  - `llama-cpp`: new local server-backed implementation.
- Keep hands-free mode intact:
  - Wake/end/command detection remains unchanged.
  - The hands-free session still produces the same final audio buffer.
  - Only the transcription backend consuming that buffer changes.
- Add CLI options:
  - `--asr-backend {mlx-whisper,llama-cpp}`, default `mlx-whisper`.
  - `--llama-server-bin PATH`, pointing to a source-built `llama-server`.
  - `--llama-model PATH`, defaulting when present to `/Users/xin/.lmstudio/models/ggml-org/Qwen3-ASR-1.7B-GGUF/Qwen3-ASR-1.7B-Q8_0.gguf`.
  - `--llama-mmproj PATH`, defaulting when present to `/Users/xin/.lmstudio/models/ggml-org/Qwen3-ASR-1.7B-GGUF/mmproj-Qwen3-ASR-1.7B-bf16.gguf`.
  - `--llama-host 127.0.0.1`, `--llama-port 8091`, `--llama-ctx 4096`, `--llama-ngl 99`.
  - `--no-llama-autostart` to require an already running server.
- Keep install/default usage unchanged:
  - Do not add a package-manager llama.cpp dependency.
  - Do not require Qwen3-ASR downloads for default users.
  - `install.sh` and `uv run whiscode` continue to support the existing MLX Whisper path.
- Implement llama.cpp mode:
  - Health-check the configured local server.
  - If unavailable and autostart is enabled, start source-built `llama-server` with `-m`, `--mmproj`, host, port, context, and GPU layer settings.
  - Keep the server warm while WhisCode runs.
  - Only terminate the server if WhisCode started it.
  - Serialize recorded audio to temporary 16 kHz mono WAV and send it to llama.cpp as base64 audio.
  - Parse the response into plain transcript text and return it to the existing WhisCode postprocessing pipeline.
- llama.cpp source workflow:
  - Rebuild from `/Users/xin/Documents/repos/llama.cpp` current source.
  - Use the rebuilt `build/bin/llama-server`.
  - Keep `personal-local-runbook`.
  - Clean up stale `release-b9254` only after the new build is verified.

## Telemetry / Debuggability

Add content-safe backend diagnostics:

- `asr.backend_selected`
- `llama.server_health`
- `llama.server_started`
- `llama.server_start_failed`
- `llama.transcription_started`
- `llama.transcription_completed`
- `llama.transcription_failed`

Telemetry must include bounded operational fields only: backend, status/outcome, duration, port, PID for child process, audio seconds, sample count, output length, HTTP status class, and error type. It must not include raw audio, transcript text, prompts, full model paths, full payloads, secrets, or model output content.

## Test Plan

- Verify `uv run whiscode` still selects MLX Whisper and does not require llama.cpp files.
- Verify `uv run whiscode --asr-backend llama-cpp` selects llama.cpp/Qwen3-ASR.
- Unit-test CLI parsing, backend selection, MLX default preservation, llama.cpp server health checks, autostart/reuse/shutdown behavior, WAV serialization, request payload construction, response parsing, and error handling.
- Run existing tests to confirm postprocessing, refiner, telemetry, and transcription-progress behavior remain stable.
- Manual smoke test:
  - Build llama.cpp from source.
  - Start WhisCode in llama.cpp mode.
  - Dictate English, Chinese, and mixed Chinese/English.
  - Confirm hands-free mode, overlay, terminal output, typed text, and telemetry behave as before except for the ASR backend.

## Assumptions

- Backward compatibility is required: default command and install flow stay MLX Whisper.
- llama.cpp mode is advanced/optional and may depend on local source-built llama.cpp plus local model files.
- The current LM Studio Qwen3-ASR files are acceptable, including the bf16 `mmproj`.
- Port `8091` is reserved for WhisCode's llama.cpp ASR server to avoid collisions with existing local LLM usage on `8080`.
