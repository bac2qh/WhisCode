# WhisCode

Voice-to-keyboard for code dictation on macOS. Press a hotkey, speak, and your words are typed into any text field. Powered by [MLX Whisper](https://github.com/ml-explore/mlx-examples) by default, with optional MLX VibeVoice and llama.cpp/Qwen3-ASR backends for local experiments. The older CrispASR/VibeVoice GGUF path is still available as a legacy compatibility backend.

## Version Status

Current beta: `v2.0.0-beta.1`.

This v2 beta marks the move from hotkey-first dictation toward hands-free operation. The main v2 changes are local wake/end phrase detection, trained voice commands, continuous microphone capture with bounded queues, and the floating recording overlay as the default recording indicator. The older macOS start/end notification banners are now opt-in with `--recording-notifications`.

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Accessibility permissions (for keyboard simulation)
- Microphone access

## Installation

```bash
git clone https://github.com/bac2qh/WhisCode.git
cd WhisCode
```

Two install options:

- **`./install.sh`** — base install (uv + dependencies + Whisper large-v3 model, ~3GB)
- **`./install_full.sh`** — base + Ollama + Qwen3.5 4B model (~3.4GB extra), required for `--refine` mode

## Usage

### Recommended daily workflow

For regular dictation, the recommended current workflow is:

```bash
uv run whiscode --hands-free --asr-backend mlx-vibevoice
```

This is not a change to the CLI defaults. `uv` runs WhisCode in the project-managed environment, `--hands-free` keeps interaction natural with local phrase detection, and `--asr-backend mlx-vibevoice` selects the preferred local VibeVoice ASR backend.

Say your wake phrase to start recording. While recording, say the wake phrase again to Send Chunk: WhisCode queues the current chunk into an in-memory delivery batch, transcribes and prints it as soon as it finishes, and immediately starts the next recording. Use Send Chunk for long messages because smaller chunks transcribe sooner, the queue keeps moving, and the pause gives you a moment to breathe, recollect details, and organize the next thought.

Say your end phrase to finish the message. **Right Shift** remains available as the manual start/stop fallback. WhisCode copies and pastes the full Send Chunk batch at your cursor once the final recording finishes transcribing.

### Hotkey flow

```bash
uv run whiscode
```

Press **Right Shift** to start recording, then press **Right Shift** again to stop and transcribe. The transcribed text is typed at your cursor position. If a prior recording is still transcribing, WhisCode queues the new recording and keeps transcriptions typed in order.

Manual hotkeys do not Send Chunk. The older **Right Option** + **Right Shift** chord is ignored.

For the v2 hands-free flow, start with:

```bash
uv run whiscode --hands-free
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--hotkey HOTKEY` | `shift_r` | Manual recording toggle key: start recording, then stop/finalize while recording |
| `--asr-backend BACKEND` | `mlx-whisper` | ASR backend: `mlx-whisper`, optional `mlx-vibevoice`, optional `llama-cpp`, or legacy `crispasr` |
| `--language LANG` | `auto` | Language code (e.g. `en`, `zh`, `ja`) or `auto` to detect from audio |
| `--prompt TEXT` | — | Additional context to improve transcription accuracy |
| `--hotwords-file PATH` | `~/.config/whiscode/hotwords.txt` | Path to hotwords/replacements config file |
| `--mlx-vibevoice-model MODEL` | `~/Documents/models/mlx-community/VibeVoice-ASR-8bit` | MLX VibeVoice model path or Hugging Face repo |
| `--max-recording-seconds FLOAT` | `600.0` | Maximum recording length before auto-finalizing; `0` disables the cap |
| `--refine` | off | Polish transcription with a local Ollama LLM (prose mode) |
| `--refine-model MODEL` | `qwen3.5:4b` | Ollama model to use for refinement |
| `--hands-free` | off | Use local start/end phrase detection instead of manual hotkeys as the primary trigger |
| `--hands-free-threshold FLOAT` | `0.055` | Detection threshold for wake phrase matching |
| `--hands-free-end-threshold FLOAT` | `0.055` | Detection threshold for end phrase matching |
| `--hands-free-command-threshold FLOAT` | `0.055` | Detection threshold for hands-free command matching |
| `--hands-free-command-config PATH` | `~/.config/whiscode/commands.ini` | Hands-free command enablement config |
| `--hands-free-tail-seconds FLOAT` | auto, fallback `1.0` | Audio tail to discard when the end phrase is detected; omitted values are inferred from end phrase references |
| `--hands-free-tail-extra-seconds FLOAT` | `1.0` | Extra end-detection lag buffer added to the inferred or explicit hands-free tail; set to `0` for the previous base-only trim |
| `--hands-free-audio-queue-seconds FLOAT` | `10.0` | Queued hands-free audio allowed between mic capture and detection before oldest chunks are dropped |
| `--hands-free-min-rms FLOAT` | `0.006` | Minimum detector-window RMS before keyword matching |
| `--hands-free-min-active-ratio FLOAT` | `0.05` | Minimum ratio of active samples before keyword matching |
| `--hands-free-active-level FLOAT` | `0.01` | Absolute sample level counted as active |
| `--hands-free-wake-confirmations INT` | `2` | Consecutive wake matches required before recording starts |
| `--hands-free-command-confirmations INT` | `2` | Consecutive command matches required before pressing a key |
| `--hands-free-debug` | off | Print detector distances for threshold tuning |
| `--no-enroll-prompt` | off | Exit instead of offering guided enrollment when samples are missing |
| `--telemetry-path PATH` | `~/Library/Logs/WhisCode/events.jsonl` | Local JSONL telemetry path |
| `--no-telemetry` | off | Disable local telemetry |
| `--recording-overlay` | on | Show floating recording and transcription overlay |
| `--no-recording-overlay` | off | Disable floating recording and transcription overlay |
| `--recording-notifications` | off | Keep macOS start/end notification banners in addition to overlay |
| `--external-only` | off | Run external transcription watchers without hotkeys, recording, or keyboard injection |
| `--external-audio-inbox PATH` | — | Watch a top-level folder or SMB URL for external audio files |
| `--external-transcript-outbox PATH` | sibling `outbox` | Folder for external `.txt` and `.json` transcript results |
| `--external-ccab-root PATH` | — | Discover CCAB short inboxes under `PATH/*/workspace/transcription/short` |
| `--external-poll-seconds FLOAT` | `2.0` | External inbox scan cadence |
| `--external-stable-seconds FLOAT` | `5.0` | Quiet period before an external file is considered ready |

### Optional MLX VibeVoice ASR

`mlx-vibevoice` is the recommended VibeVoice backend. It is an opt-in MLX-Audio path for local VibeVoice ASR models and is useful when you want VibeVoice's strong mixed Chinese/English and technical-term behavior without running a CrispASR server. In local use it has been noticeably faster than the CrispASR/GGUF path:

```bash
uv run whiscode --asr-backend mlx-vibevoice
```

By default this loads the local 8-bit model from:

```text
~/Documents/models/mlx-community/VibeVoice-ASR-8bit
```

Override the default with `WHISCODE_MLX_VIBEVOICE_MODEL` or `--mlx-vibevoice-model`. For the local BF16 reference model:

```bash
WHISCODE_MLX_VIBEVOICE_MODEL=~/Documents/models/mlx-community/VibeVoice-ASR-bf16 \
  uv run whiscode --asr-backend mlx-vibevoice
```

or:

```bash
uv run whiscode --asr-backend mlx-vibevoice \
  --mlx-vibevoice-model ~/Documents/models/mlx-community/VibeVoice-ASR-bf16
```

This backend keeps WhisCode's hotkeys, hands-free detection, overlay, terminal output, text injection, replacements, optional `--refine` behavior, and existing hotwords file. Hotwords and `--prompt` are passed to VibeVoice through MLX-Audio's `context` parameter, which is the prompt/hotword path VibeVoice was designed to use. This is a soft model hint, not a guaranteed glossary constraint: VibeVoice can still miss project-specific phrases, hyphenated names, or tool names such as `Goal Mode` or `long-autonomous-run`.

For terms that must be corrected reliably, add replacements to `~/.config/whiscode/hotwords.txt`. Plain lines are ASR hints; `wrong -> right` lines are deterministic post-ASR replacements:

```text
LLM
WhisCode
goal mode -> Goal Mode
long autonomous run -> long-autonomous-run
long autonomous run skill -> long-autonomous-run skill
```

If the local model snapshot does not include tokenizer files, MLX-Audio may fetch and cache the intended `Qwen/Qwen2.5-7B` tokenizer on first load.

Benchmark backend latency on a WAV file:

```bash
uv run whiscode-benchmark-asr --audio sample.wav --asr-backend mlx-vibevoice
```

### External NAS Transcription Queue

WhisCode can also watch shared inbox folders for audio files written by external agents or NAS workflows. External intake supports `mlx-whisper` and `mlx-vibevoice`. The single-inbox form can be a local filesystem path or a native SMB URL; SMB does not require mounting the share locally.

```bash
uv run whiscode --asr-backend mlx-vibevoice \
  --external-audio-inbox smb://192.168.4.21/NAS_1/whiscode/inbox
```

Use `--external-only` when WhisCode is being managed by tmux or another process supervisor and should not install hotkeys, open the microphone, show overlays, or inject text:

```bash
uv run whiscode \
  --external-only \
  --asr-backend mlx-whisper \
  --model mlx-community/whisper-large-v3-turbo-asr-fp16 \
  --external-audio-inbox /path/to/inbox \
  --external-transcript-outbox /path/to/outbox \
  --no-recording-overlay
```

For CCAB short transcription, one external-only WhisCode process can discover all user short lanes under a root whose children contain `workspace/transcription/short/{inbox,outbox}`:

```bash
uv run whiscode \
  --external-only \
  --asr-backend mlx-whisper \
  --model mlx-community/whisper-large-v3-turbo-asr-fp16 \
  --external-ccab-root /Users/xinding/openclaw \
  --external-poll-seconds 2 \
  --external-stable-seconds 1 \
  --no-recording-overlay
```

When `--external-transcript-outbox` is omitted, WhisCode writes results to a sibling `outbox` folder next to the inbox. For the SMB example above, the default outbox is `smb://192.168.4.21/NAS_1/whiscode/outbox`. Keep these settings in a repo-local `.env.1password.whiscode-smb` file copied from `.env.1password.whiscode-smb.example`, not in `~/.zshrc`:

```bash
WHISCODE_EXTERNAL_AUDIO_INBOX=smb://192.168.4.21/NAS_1/whiscode/inbox
WHISCODE_EXTERNAL_TRANSCRIPT_OUTBOX=smb://192.168.4.21/NAS_1/whiscode/outbox
WHISCODE_EXTERNAL_EXTENSIONS=.wav,.mp3,.flac,.ogg,.opus,.m4a,.aac
WHISCODE_EXTERNAL_POLL_SECONDS=2
WHISCODE_EXTERNAL_STABLE_SECONDS=5
WHISCODE_EXTERNAL_SMB_USERNAME="op://<vault>/<item>/username"
WHISCODE_EXTERNAL_SMB_PASSWORD="op://<vault>/<item>/password"
WHISCODE_EXTERNAL_SMB_DOMAIN=WORKGROUP
```

The real `.env.1password.whiscode-smb` file is ignored by Git. It should contain 1Password reference pointers such as `op://...`, not plaintext SMB credentials. Run with 1Password so the referenced SMB credentials are resolved and injected only into the WhisCode process:

```bash
op run --env-file .env.1password.whiscode-smb -- \
  uv run whiscode --asr-backend mlx-vibevoice
```

Do not put SMB credentials in the `smb://` URL. If `WHISCODE_EXTERNAL_SMB_DOMAIN` is set, WhisCode passes the username to SMB as `DOMAIN\username`.

The watcher scans only the top level of the inbox, ignores hidden files and unsupported extensions, and queues a file only after its size and mtime have stayed unchanged for the stable period. Supported extensions default to `.wav`, `.mp3`, `.flac`, `.ogg`, `.opus`, `.m4a`, and `.aac`. MLX-Audio handles decoding through its audio I/O layer; for SMB inputs, WhisCode streams the remote file into a temporary local file with the same suffix before decoding. Telegram-style OGG/Opus and M4A files require a working ffmpeg backend on the machine running WhisCode.

Each completed external file produces `source-stem-<id>.txt` and `source-stem-<id>.json` in the outbox. SMB sidecars are written to temporary remote files and then published with SMB replace/rename so readers do not see partial results. The JSON records bounded source metadata, duration, backend, model label, status, transcript text on success, or a bounded error type/message on failure. External transcripts are the plain backend output: WhisCode does not apply hotwords, replacements, postprocessing, refinement, typing, or manual dictation stats to this queue.

Manual dictation remains higher priority. External work starts only while no local recording is reserved, queued, or actively transcribing. If a manual recording arrives while a long external VibeVoice transcription is already using the loaded MLX engine, WhisCode lazily starts one rescue VibeVoice engine for manual work. After the external job finishes, the old external engine is retired and the rescue engine becomes primary. WhisCode uses at most two in-process VibeVoice engines for this behavior.

### Optional llama.cpp ASR

The default command remains MLX Whisper:

```bash
uv run whiscode
```

Users who maintain a source-built llama.cpp checkout can opt into Qwen3-ASR transcription:

```bash
uv run whiscode --asr-backend llama-cpp
```

This mode keeps WhisCode's hotkeys, hands-free detection, overlay, terminal output, text injection, replacements, and optional `--refine` behavior. Only the final transcription backend changes.

WhisCode does not install llama.cpp or Qwen3-ASR for default users. Build llama.cpp from source and provide local GGUF files:

```bash
cd /Users/xin/Documents/repos/llama.cpp
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j 8
```

Default llama.cpp paths target a sibling source checkout and LM Studio's Qwen3-ASR cache:

```text
/Users/xin/Documents/repos/llama.cpp/build/bin/llama-server
/Users/xin/.lmstudio/models/ggml-org/Qwen3-ASR-1.7B-GGUF/Qwen3-ASR-1.7B-Q8_0.gguf
/Users/xin/.lmstudio/models/ggml-org/Qwen3-ASR-1.7B-GGUF/mmproj-Qwen3-ASR-1.7B-bf16.gguf
```

Override them when needed:

```bash
uv run whiscode --asr-backend llama-cpp \
  --llama-server-bin /path/to/llama-server \
  --llama-model /path/to/Qwen3-ASR-1.7B-Q8_0.gguf \
  --llama-mmproj /path/to/mmproj-Qwen3-ASR-1.7B-bf16.gguf
```

By default WhisCode starts a warm llama.cpp server on `127.0.0.1:8091` and stops only the child process it started when WhisCode exits. Use `--no-llama-autostart` to connect to an already running server.

### Legacy CrispASR VibeVoice ASR

`crispasr` is a legacy backend for VibeVoice ASR GGUF experiments. Prefer `mlx-vibevoice` for current local VibeVoice use; it avoids the CrispASR server layer, supports VibeVoice context/hotwords directly, and has been faster in local testing. Keep `crispasr` only for existing GGUF setups or compatibility experiments:

```bash
WHISCODE_CRISPASR_MODEL=~/Documents/models/vibevoice-asr-GGUF/vibevoice-asr-f16.gguf \
  uv run whiscode --asr-backend crispasr --language en
```

WhisCode does not install CrispASR or VibeVoice GGUF assets for default users. Build a sibling CrispASR checkout from source only if you need this legacy path:

```bash
cd ~/Documents/repos/CrispASR
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=ON
cmake --build build --target crispasr-cli
```

Download a GGUF from `cstr/vibevoice-asr-GGUF` and place it at the path in `WHISCODE_CRISPASR_MODEL`, or pass paths explicitly. The upstream GGUF repo lists `vibevoice-asr-q4_k.gguf` as the recommended default at about 5 GB and `vibevoice-asr-f16.gguf` as the 16 GB reference-quality file. On local WhisCode smoke tests, Q4 was correct and about 2x faster than warm F16 on an 8.2-second synthetic sample, but only about 0.09 seconds faster on a 1.9-second sample. Treat Q4 mainly as the smaller model and a possible latency improvement for longer recordings, not a guaranteed dramatic speedup for short dictation.

```bash
uv run whiscode --asr-backend crispasr \
  --crispasr-bin ~/Documents/repos/CrispASR/build/bin/crispasr \
  --crispasr-model ~/Documents/models/vibevoice-asr-GGUF/vibevoice-asr-q4_k.gguf
```

By default WhisCode starts a warm CrispASR server on `127.0.0.1:8092`, sends final recordings to `/v1/audio/transcriptions`, and stops only the child process it started when WhisCode exits. Use `--no-crispasr-autostart` to connect to an already running server.

The current CrispASR/VibeVoice integration is a blocking full-recording request. CrispASR returns the final transcript after the request completes, but this HTTP path does not expose per-request stage, token, or percentage progress while VibeVoice is running. WhisCode can still show queued/transcribing overlay cards for VibeVoice jobs, but it cannot show a meaningful frame percentage or FPS progress bar for this backend yet. CrispASR's CLI streaming and live-monitor modes are separate execution paths and are not the same as WhisCode's warm-server `/v1/audio/transcriptions` flow.

The current CrispASR VibeVoice backend accepts WhisCode's hotwords as an OpenAI-style `prompt` field, but CrispASR's VibeVoice server path does not currently pass that prompt into the VibeVoice decoder. Use `mlx-vibevoice` when you need VibeVoice hotword/context conditioning from WhisCode.

Benchmark backend latency on a WAV file:

```bash
uv run whiscode-benchmark-asr --audio sample.wav --asr-backend crispasr --language en
```

## Recording Overlay

WhisCode shows a small floating macOS overlay while recording and transcribing. During recording it shows an elapsed stopwatch and live microphone levels as waveform bars. Completed recordings enter a FIFO transcription queue, and the overlay stacks cards with the newest recording on top while queued/transcribing cards shift downward. During transcription it shows queued/transcribing state for every backend, plus a compact frame progress bar with percentage, processed/total frames, and frames per second when the selected backend reports progress, such as MLX Whisper. Guided enrollment uses the same overlay while each sample is being recorded.

Use `--no-recording-overlay` to disable it. Use `--recording-notifications` with `whiscode` if you also want the older macOS start/end notification banners during normal recording.

Successful transcripts are also printed to stdout as flush-left single-line blocks with blank spacing between entries, so terminal output can be copied without touching the system clipboard.

## Hands-Free Mode

Hands-free mode keeps the microphone open and uses local keyword matching for your recorded start and end phrases. The microphone capture loop continuously drains audio into a bounded queue, and a separate detector worker runs wake/end/command matching so detector work does not block microphone reads. The selected ASR backend only receives the captured audio between the start and end phrases.

Recordings auto-finalize after `--max-recording-seconds` seconds, which defaults to 10 minutes. This cap applies to both Right Shift recording and hands-free recording, and bounds buffered audio if a wake phrase fires accidentally. The older `--hands-free-max-seconds` flag is still accepted as a hands-free-only override.

Start hands-free mode:

```bash
uv run whiscode --hands-free
```

If samples are missing, WhisCode offers guided enrollment and points to a top-up command that records only incomplete reference sets. Each sample is trimmed with local VAD and then padded to the detector window before it is saved, so the reference WAVs focus on the phrase while still matching the runtime comparison window.

Run a full guided enrollment to record three wake samples, three end samples, and three samples for each enabled hands-free command from your default microphone:

```bash
uv run whiscode-enroll --record
```

Run a top-up enrollment to skip complete reference folders and record only the samples needed to reach three WAVs per enabled phrase set:

```bash
uv run whiscode-enroll --record --record-missing
```

Guided enrollment shows the floating recording overlay for each sample by default. Disable it with `uv run whiscode-enroll --record --no-recording-overlay`.

Existing audio files can still be imported manually:

```bash
uv run whiscode-enroll wake wake1.m4a wake2.m4a wake3.m4a
uv run whiscode-enroll end end1.m4a end2.m4a end3.m4a
uv run whiscode-enroll page-up pageup1.m4a pageup2.m4a pageup3.m4a
uv run whiscode-enroll shift-enter shiftenter1.m4a shiftenter2.m4a shiftenter3.m4a
uv run whiscode-enroll shift-tab shifttab1.m4a shifttab2.m4a shifttab3.m4a
uv run whiscode-enroll tab tab1.m4a tab2.m4a tab3.m4a
uv run whiscode-enroll arrow-up arrowup1.m4a arrowup2.m4a arrowup3.m4a
uv run whiscode-enroll arrow-down arrowdown1.m4a arrowdown2.m4a arrowdown3.m4a
uv run whiscode-enroll scroll-up scrollup1.m4a scrollup2.m4a scrollup3.m4a
uv run whiscode-enroll scroll-down scrolldown1.m4a scrolldown2.m4a scrolldown3.m4a
```

Hands-free mode also supports ten trained command slots while not actively recording: `page-up`, `page-down`, `enter`, `shift-enter`, `shift-tab`, `tab`, `arrow-up`, `arrow-down`, `scroll-up`, and `scroll-down`. The spoken phrase is whatever you record for that slot. WhisCode maps the key slots to the physical Page Up, Page Down, Enter, Shift+Enter, Shift+Tab, Tab, Arrow Up, or Arrow Down key action. `scroll-up` emits a native macOS pixel scroll wheel action that reveals older terminal output above the current view, and `scroll-down` emits the inverse action toward newer output. Each scroll command moves about half of the main display height. Command detection is disabled while recording so dictated speech cannot inject keys or scrolls, but it can run while earlier recordings are queued or transcribing.

The wake phrase also acts as Send Chunk while actively recording. When detected during a recording, WhisCode trims the spoken wake phrase tail using the active span inferred from the wake references plus `--hands-free-tail-extra-seconds`, queues the chunk into an in-memory delivery batch with a blank line after it, and immediately starts a new recording. Intermediate chunks are transcribed and printed to stdout as they finish, but they are not copied to the clipboard or pasted into the focused app until the final end phrase, manual Right Shift stop, or timeout completes the batch.

You can selectively enable command slots with `~/.config/whiscode/commands.ini`:

```ini
[commands]
page-up = true
page-down = true
enter = true
shift-enter = false
shift-tab = false
tab = true
arrow-up = true
arrow-down = true
scroll-up = true
scroll-down = true
```

If this file does not exist, all command slots stay enabled for backward compatibility. If it exists, only commands set to `true` are enabled; omitted or `false` commands are ignored and do not need reference samples. Enabled commands still need enough recorded samples before they can load. Override the path with `--hands-free-command-config PATH`; guided enrollment and calibration use the same config by default and accept `--command-config PATH`. For a scroll-only add-on after wake/end references already exist, enable `scroll-up` and `scroll-down`, then run `uv run whiscode-enroll --record --record-missing`; complete wake/end folders and other complete enabled commands are skipped.

After enrollment, inspect the local detector score separation:

```bash
uv run whiscode-calibrate
```

The report compares wake samples against wake samples, end samples against end samples, command samples against their own command sets, cross-command samples, wake samples against end samples, and recent telemetry trigger distances. Use it to choose threshold changes after observing live runs rather than guessing from one false positive.

Right Shift remains available as the manual start/stop fallback while hands-free mode is running.

When the end phrase stops a recording, WhisCode discards the inferred or explicit end-word tail plus an extra detection-lag buffer before queueing audio for transcription. The extra buffer defaults to `1.0` second through `--hands-free-tail-extra-seconds`; set it to `0` to restore the previous base-only end-tail trim. Manual Right Shift stops and timeout stops still keep the pending tail.

WhisCode ignores partial detector windows and quiet windows before calling the keyword matcher. This prevents silence and microphone background noise from triggering wake/end phrases. Wake detection also requires two consecutive matching windows by default, which prevents a single noisy match from starting a recording. If your wake phrase is very quiet, lower `--hands-free-min-rms` or `--hands-free-min-active-ratio`, raise `--hands-free-threshold` slightly, or set `--hands-free-wake-confirmations 1`; if your end phrase is not detected, raise `--hands-free-end-threshold` slightly.

WhisCode writes local JSONL telemetry by default to:

```bash
~/Library/Logs/WhisCode/events.jsonl
```

Use it to inspect app startup, selected ASR backend, recording durations, queue depth, hands-free Send Chunk request/queue/restart outcomes, deferred delivery buffer/flush outcomes, transcription outcomes, backend failures, wake/end/wake-as-chunk/command detections, detector distances, key-command and scroll-command injection outcomes, and suspected rapid trigger loops. `uv run whiscode-calibrate` summarizes hands-free distances alongside reference-sample distances. Routine telemetry stays on your machine and does not include raw audio, transcripts, prompts, hotword contents, provider payloads, or typed text. Scroll injection telemetry includes only bounded command metadata such as command name, older/newer direction, pixel amount, outcome, and error type. If CrispASR/VibeVoice returns malformed chunk output, WhisCode also writes the original provider response body to `~/Library/Logs/WhisCode/crispasr-raw-responses.jsonl`, or a sibling file next to a custom `--telemetry-path`, for local debugging. That raw debug file can contain transcript or provider output text. Disable telemetry and raw debug logging with `--no-telemetry`, or write both files under another directory with `--telemetry-path`.

`handsfree.audio_overflow` means PortAudio reported an input overflow because the audio read loop could not keep up with the microphone stream. WhisCode keeps microphone capture lightweight and uses a bounded detector queue to reduce this. If detector processing still falls behind, `handsfree.audio_queue_dropped`, `handsfree.audio_queue_summary`, and `handsfree.detector_processing_summary` show how much queued audio was dropped and how long detection took. These diagnostics do not include raw audio or transcript text.

## Refine Mode

`--refine` sends the raw transcription through a local Ollama LLM to produce cleaner, more polished prose. Useful for dictating notes, emails, or documentation.

Requires Ollama to be running locally. Install via `./install_full.sh` or manually install Ollama and pull the model:

```bash
ollama pull qwen3.5:4b
```

Override the model with `--refine-model`:

```bash
uv run whiscode --refine --refine-model llama3.2:3b
```

## Examples

```bash
# Use a different manual toggle key
uv run whiscode --hotkey f9

# Transcribe in Chinese
uv run whiscode --language zh

# Add project-specific terms for better accuracy
uv run whiscode --prompt "NextJS, Prisma, tRPC, Zustand"

# Polish output with LLM refinement
uv run whiscode --refine

# Start hands-free mode after importing or recording hands-free samples
uv run whiscode --hands-free

# Use local MLX VibeVoice ASR with the existing hotwords file
uv run whiscode --asr-backend mlx-vibevoice
```

## Known Issues

- **Whisper single-language behavior:** In the default MLX Whisper backend, Whisper v3 applies one language to the entire audio clip. Mixed-language speech (e.g., Chinese with English terms) will be forced into whichever language is set, which may cause misrecognition of the other language.
- **Whisper auto-detect picks dominant language:** With `--language auto` in the default MLX Whisper backend, Whisper analyzes the first ~2 seconds of audio to detect the language. If your speech starts in a different language than the main content, detection may be wrong.
