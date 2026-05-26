# ASR Backends

WhisCode keeps recording, hands-free detection, overlays, postprocessing, text injection, and optional refinement independent from the transcription engine.

## Default Backend

`mlx-whisper` is the default ASR backend. It loads MLX Whisper in process during startup and keeps the model warm while WhisCode runs.

```bash
uv run whiscode
```

This path remains the compatibility default and is the backend installed by the base installer.

## Optional MLX VibeVoice Backend

`mlx-vibevoice` is the recommended VibeVoice backend. It is an opt-in in-process backend that uses MLX-Audio's VibeVoice ASR implementation and has been noticeably faster locally than the older CrispASR/GGUF path:

```bash
uv run whiscode --asr-backend mlx-vibevoice
```

The default model path is:

```text
~/Documents/models/mlx-community/VibeVoice-ASR-8bit
```

Override it with `WHISCODE_MLX_VIBEVOICE_MODEL` or `--mlx-vibevoice-model`, for example:

```bash
uv run whiscode --asr-backend mlx-vibevoice \
  --mlx-vibevoice-model ~/Documents/models/mlx-community/VibeVoice-ASR-bf16
```

This backend passes WhisCode hotwords and `--prompt` through VibeVoice's MLX-Audio `context` parameter, then joins VibeVoice segment text into a plain transcript before the existing postprocessing, replacement, optional refinement, and text-injection flow. It is the preferred VibeVoice path when hotword/context conditioning matters. The local MLX model snapshots may rely on MLX-Audio to fetch/cache the intended `Qwen/Qwen2.5-7B` tokenizer on first load.

Telemetry for this backend is limited to bounded operational status such as model label, load duration, audio duration, hotword count, prompt presence, context length, output length, transcription duration, and error type. It does not record raw audio, transcript text, prompts, hotword contents, full model paths, tokenizer payloads, or model output content.

## External NAS Transcription Queue

WhisCode can watch a top-level external audio inbox when running `--asr-backend mlx-vibevoice`. Set `WHISCODE_EXTERNAL_AUDIO_INBOX` or pass `--external-audio-inbox PATH` to enable it. `WHISCODE_EXTERNAL_TRANSCRIPT_OUTBOX` or `--external-transcript-outbox PATH` controls result delivery; when omitted, the outbox defaults to a sibling `outbox` folder next to the inbox.

The watcher ignores hidden files, unsupported extensions, and files whose source metadata already has a matching result sidecar. It waits until file size and mtime remain unchanged for `WHISCODE_EXTERNAL_STABLE_SECONDS` / `--external-stable-seconds` before queueing. It scans on `WHISCODE_EXTERNAL_POLL_SECONDS` / `--external-poll-seconds`. Supported extensions default to `.wav`, `.mp3`, `.flac`, `.ogg`, `.opus`, `.m4a`, and `.aac`; override with comma-separated `WHISCODE_EXTERNAL_EXTENSIONS`.

External audio is decoded through MLX-Audio audio I/O, normalized to mono 16 kHz float32, then sent to MLX VibeVoice without WhisCode hotwords, prompt, replacements, postprocessing, optional refinement, typing, or manual dictation stats. OGG/Opus and M4A support depends on MLX-Audio's ffmpeg-capable decode path being available on the host.

Outbox files are named `source-stem-<short-id>.txt` and `source-stem-<short-id>.json`. The JSON contains status, source basename, source size/mtime, duration, backend, model label, file id, transcript on success, or bounded error type/message on failure. Transcript text is intentionally present in outbox files because that is the external delivery channel; routine telemetry still excludes transcript text and full file paths.

Manual dictation has priority over external files. External jobs start only while no local recording is reserved, queued, or actively transcribing. If a manual recording arrives while an external VibeVoice job is already using the primary in-process engine, WhisCode starts one rescue VibeVoice engine for manual work. When the external job completes, WhisCode retires the old external engine and promotes the rescue engine as primary. This caps the process at two in-process VibeVoice engines.

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

## Legacy CrispASR Backend

`crispasr` is a legacy backend for local VibeVoice ASR GGUF experiments. Prefer `mlx-vibevoice` for current VibeVoice use; keep this path only for existing GGUF setups or compatibility experiments:

```bash
WHISCODE_CRISPASR_MODEL=~/Documents/models/vibevoice-asr-GGUF/vibevoice-asr-f16.gguf \
  uv run whiscode --asr-backend crispasr --language en
```

WhisCode expects a source-built sibling CrispASR checkout by default when this legacy backend is selected:

```text
~/Documents/repos/CrispASR/build/bin/crispasr
~/Documents/models/vibevoice-asr-GGUF/vibevoice-asr-f16.gguf
```

Build the executable target with `cmake --build build --target crispasr-cli`.

Override those defaults with `WHISCODE_CRISPASR_BIN`, `WHISCODE_CRISPASR_MODEL`, `--crispasr-bin`, or `--crispasr-model`.

The `cstr/vibevoice-asr-GGUF` model card lists `vibevoice-asr-q4_k.gguf` as the recommended default at about 5 GB and `vibevoice-asr-f16.gguf` as the 16 GB reference-quality file. In local WhisCode smoke benchmarks on synthetic speech, both files transcribed correctly:

| Model | Audio length | Transcription wall time | Real-time factor |
| --- | ---: | ---: | ---: |
| `vibevoice-asr-q4_k.gguf` | 1.865s | 0.924s | 0.496 |
| `vibevoice-asr-f16.gguf` warm server | 1.865s | 1.014s | 0.544 |
| `vibevoice-asr-q4_k.gguf` | 8.173s | 0.895s | 0.109 |
| `vibevoice-asr-f16.gguf` warm server | 8.173s | 1.864s | 0.228 |

Q4 is much smaller and can be meaningfully faster on longer recordings, but these local numbers did not show a dramatic short-dictation latency improvement. Keep F16 available when reference quality matters; use Q4 when disk, memory, or longer-recording latency matters more. To compare without disturbing a warm F16 server on port `8092`, start Q4 on another port:

```bash
uv run whiscode --asr-backend crispasr \
  --crispasr-port 8093 \
  --crispasr-model ~/Documents/models/vibevoice-asr-GGUF/vibevoice-asr-q4_k.gguf
```

The backend starts `crispasr --server --backend vibevoice`, keeps the model warm while WhisCode runs, sends final recordings as multipart WAV requests to `/v1/audio/transcriptions`, and returns plain transcript text to the existing WhisCode postprocessing pipeline. It reuses existing healthy servers and terminates only the child process it started.

This CrispASR/VibeVoice path is a blocking full-recording request. The server returns the final transcript only after the request completes and does not currently expose per-request stage, token, percentage, or FPS progress through `/v1/audio/transcriptions`. The recording overlay can show queued/transcribing cards for VibeVoice jobs, but it cannot show concrete in-flight VibeVoice progress in this integration. CrispASR CLI streaming and live-monitor modes are different execution paths, not the warm-server full-recording API WhisCode uses here.

Routine telemetry for this backend is limited to bounded operational status such as health-check outcomes, startup duration, child PID, backend name, model basename, audio duration, output length, HTTP status class, error type, and malformed response shape counts. It does not record raw audio, transcript text, prompts, hotwords, chunk content, full request payloads, secrets, or full model paths. When CrispASR/VibeVoice chunk parsing fails or needs best-effort recovery, WhisCode writes the original provider response body to local-only `crispasr-raw-responses.jsonl` next to runtime telemetry for debugging; that file can contain transcript or provider output text.

The current CrispASR VibeVoice path receives WhisCode's hotwords as an OpenAI-style `prompt` field, but the CrispASR VibeVoice server backend does not currently route that prompt into VibeVoice decoding. Use `mlx-vibevoice` for VibeVoice hotword/context conditioning inside WhisCode.
