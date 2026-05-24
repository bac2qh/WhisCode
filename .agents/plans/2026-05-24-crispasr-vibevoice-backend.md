# CrispASR VibeVoice GGUF Backend

## Summary
- Add `crispasr` as a third optional ASR backend for WhisCode, targeting VibeVoice ASR GGUF through a source-built sibling `../CrispASR` checkout.
- Keep `mlx-whisper` as the default; existing users and the current llama.cpp/Qwen backend remain unchanged.
- Use CrispASR server mode so the VibeVoice model stays warm in memory and WhisCode sends recorded WAV requests to `/v1/audio/transcriptions`.

## Key Changes
- Add `--asr-backend crispasr`.
- Add CrispASR options:
  - `--crispasr-bin`, default `WHISCODE_CRISPASR_BIN`, then `../CrispASR/build/bin/crispasr`.
  - `--crispasr-model`, default `WHISCODE_CRISPASR_MODEL`, then `~/Documents/models/vibevoice-asr-GGUF/vibevoice-asr-f16.gguf`.
  - `--crispasr-backend`, default `vibevoice`.
  - `--crispasr-host 127.0.0.1`, `--crispasr-port 8092`.
  - `--crispasr-max-tokens 2048`, `--crispasr-temperature 0.0`.
  - `--crispasr-request-timeout 300`, `--crispasr-startup-timeout 180`, `--no-crispasr-autostart`.
- Start CrispASR with `crispasr --server --backend vibevoice -m <model> --host <host> --port <port>`, reusing an existing healthy server when present and closing only the child process WhisCode owns.
- Send multipart WAV requests with `response_format=json`, `language`, `prompt`, `temperature`, and `max_tokens`.
- Build the prompt from WhisCode's existing coding prompt plus `--prompt` and hotwords, so VibeVoice gets the same coding vocabulary bias as Whisper.

## Runtime Setup
- Do not install CrispASR from a package manager and do not vendor it into WhisCode.
- Build sibling CrispASR from source with Metal:
  - `cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=ON`
  - `cmake --build build --target crispasr-cli`
- Download the model as `vibevoice-asr-f16.gguf`; recommend storing it at `~/Documents/models/vibevoice-asr-GGUF/vibevoice-asr-f16.gguf`.
- README should document the recommended command:
  - `WHISCODE_CRISPASR_MODEL=... uv run whiscode --asr-backend crispasr --language en`

## Telemetry / Debuggability
- Emit bounded telemetry for CrispASR health, startup, transcription start/completion/failure, backend name, model basename, port, timing, audio duration, output length, and HTTP status class.
- Never log raw audio, transcript text, prompt text, hotwords, full paths, secrets, or request payloads.
- Preserve the existing app-level transcription telemetry and use backend-specific events to isolate CrispASR startup/request failures from postprocessing and text injection failures.

## Benchmarking
- Add `whiscode-benchmark-asr` to run file-based latency tests against `mlx-whisper`, `llama-cpp`, and `crispasr`.
- Report audio duration, wall time, real-time factor, output text length, backend, model basename, and cold/warm mode.

## Test Plan
- Unit-test CLI parsing and env/default path resolution.
- Unit-test CrispASR health/start command construction, child-process ownership, multipart request fields, JSON/text response parsing, and HTTP error handling with fake clients.
- Unit-test that the CrispASR prompt includes the coding vocabulary and user hotwords without changing postprocessing behavior.
- Run the full existing test suite to verify Whisper, llama.cpp, hands-free mode, overlay, hotwords, and text injection remain unchanged.
- Manual smoke phrases:
  - "open the repo and run pytest"
  - "switch to the worktree and inspect the README"
  - mixed Chinese/English with `repo`, `uv`, `pytest`, `llama.cpp`, and `WhisCode`.

## Assumptions
- VibeVoice GGUF runs through CrispASR, not current llama.cpp.
- The first integration uses F16 GGUF for quality and accepts slower-than-Whisper latency.
- WhisCode's max recording limit stays unchanged, but benchmark results decide whether to add VibeVoice-specific shorter defaults later.
