# ASR Backends

WhisCode keeps recording, hands-free detection, overlays, postprocessing, text injection, and optional refinement independent from the transcription engine.

## Default Backend

`mlx-whisper` is the default ASR backend. It loads MLX Whisper in process during startup and keeps the model warm while WhisCode runs.

```bash
uv run whiscode
```

This path remains the compatibility default and is the backend installed by the base installer.

## Optional llama.cpp Backend

`llama-cpp` is an opt-in backend for local Qwen3-ASR experiments:

```bash
uv run whiscode --asr-backend llama-cpp
```

WhisCode connects to or starts a local `llama-server`, sends the final recorded audio buffer as base64 WAV through the OpenAI-compatible chat endpoint, parses the Qwen3-ASR response, and returns plain transcript text to the existing WhisCode postprocessing pipeline.

The default local configuration expects:

```text
/Users/xin/Documents/repos/llama.cpp/build/bin/llama-server
/Users/xin/.lmstudio/models/ggml-org/Qwen3-ASR-1.7B-GGUF/Qwen3-ASR-1.7B-Q8_0.gguf
/Users/xin/.lmstudio/models/ggml-org/Qwen3-ASR-1.7B-GGUF/mmproj-Qwen3-ASR-1.7B-bf16.gguf
```

The backend starts the server only when selected, keeps it warm while WhisCode runs, and terminates only the child process it started. Existing external servers are reused and left running.

Telemetry for this backend is limited to bounded operational status such as backend selection, health-check outcomes, startup duration, child PID, audio duration, output length, HTTP status class, and error type. It does not record raw audio, transcript text, prompts, full request payloads, secrets, or model output content.
