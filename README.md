# WhisCode

Voice-to-keyboard for code dictation on macOS. Press a hotkey, speak, and your words are typed into any text field. Powered by [MLX Whisper](https://github.com/ml-explore/mlx-examples) by default, with optional llama.cpp/Qwen3-ASR and CrispASR/VibeVoice ASR backends for local experiments.

## Version Status

Current beta: `v2.0.0-beta.1`.

This v2 beta marks the move from hotkey-first dictation toward hands-free operation. The main v2 changes are local wake/end phrase detection, trained voice key commands, continuous microphone capture with bounded queues, and the floating recording overlay as the default recording indicator. The older macOS start/end notification banners are now opt-in with `--recording-notifications`.

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

```bash
uv run whiscode
```

Press **Right Shift** to start recording, press again to stop. The transcribed text is typed at your cursor position.

For the v2 hands-free flow, start with:

```bash
uv run whiscode --hands-free
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--hotkey HOTKEY` | `shift_r` | Toggle key for recording |
| `--asr-backend BACKEND` | `mlx-whisper` | ASR backend: `mlx-whisper`, optional `llama-cpp`, or optional `crispasr` |
| `--language LANG` | `auto` | Language code (e.g. `en`, `zh`, `ja`) or `auto` to detect from audio |
| `--prompt TEXT` | — | Additional context to improve transcription accuracy |
| `--hotwords-file PATH` | `~/.config/whiscode/hotwords.txt` | Path to hotwords/replacements config file |
| `--max-recording-seconds FLOAT` | `600.0` | Maximum recording length before auto-finalizing; `0` disables the cap |
| `--refine` | off | Polish transcription with a local Ollama LLM (prose mode) |
| `--refine-model MODEL` | `qwen3.5:4b` | Ollama model to use for refinement |
| `--hands-free` | off | Use local start/end phrase detection instead of Right Shift as the primary trigger |
| `--hands-free-threshold FLOAT` | `0.055` | Detection threshold for wake phrase matching |
| `--hands-free-end-threshold FLOAT` | `0.055` | Detection threshold for end phrase matching |
| `--hands-free-command-threshold FLOAT` | `0.055` | Detection threshold for hands-free key command matching |
| `--hands-free-command-config PATH` | `~/.config/whiscode/commands.ini` | Hands-free command enablement config |
| `--hands-free-tail-seconds FLOAT` | `1.0` | Audio tail to discard when the end phrase is detected |
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

### Optional CrispASR VibeVoice ASR

`crispasr` is an opt-in backend for VibeVoice ASR GGUF experiments. It is useful when you want a slower but higher-context local ASR model for technical jargon and multilingual dictation:

```bash
WHISCODE_CRISPASR_MODEL=~/Documents/models/vibevoice-asr-GGUF/vibevoice-asr-f16.gguf \
  uv run whiscode --asr-backend crispasr --language en
```

WhisCode does not install CrispASR or VibeVoice for default users. Build a sibling CrispASR checkout from source:

```bash
cd ~/Documents/repos/CrispASR
cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=ON
cmake --build build --target crispasr-cli
```

Download `vibevoice-asr-f16.gguf` from `cstr/vibevoice-asr-GGUF` and place it at the path in `WHISCODE_CRISPASR_MODEL`, or pass paths explicitly:

```bash
uv run whiscode --asr-backend crispasr \
  --crispasr-bin ~/Documents/repos/CrispASR/build/bin/crispasr \
  --crispasr-model ~/Documents/models/vibevoice-asr-GGUF/vibevoice-asr-f16.gguf
```

By default WhisCode starts a warm CrispASR server on `127.0.0.1:8092`, sends final recordings to `/v1/audio/transcriptions`, and stops only the child process it started when WhisCode exits. Use `--no-crispasr-autostart` to connect to an already running server.

Benchmark backend latency on a WAV file:

```bash
uv run whiscode-benchmark-asr --audio sample.wav --asr-backend crispasr --language en
```

## Recording Overlay

WhisCode shows a small floating macOS overlay while recording and transcribing. During recording it shows an elapsed stopwatch and live microphone levels as waveform bars. During transcription it shows a compact frame progress bar with percentage, processed/total frames, and frames per second when available. Guided enrollment uses the same overlay while each sample is being recorded.

Use `--no-recording-overlay` to disable it. Use `--recording-notifications` with `whiscode` if you also want the older macOS start/end notification banners during normal recording.

## Hands-Free Mode

Hands-free mode keeps the microphone open and uses local keyword matching for your recorded start and end phrases. The microphone capture loop continuously drains audio into a bounded queue, and a separate detector worker runs wake/end/command matching so detector work does not block microphone reads. The selected ASR backend only receives the captured audio between the start and end phrases.

Recordings auto-finalize after `--max-recording-seconds` seconds, which defaults to 10 minutes. This cap applies to both Right Shift recording and hands-free recording, and bounds buffered audio if a wake phrase fires accidentally. The older `--hands-free-max-seconds` flag is still accepted as a hands-free-only override.

Start hands-free mode:

```bash
uv run whiscode --hands-free
```

If samples are missing, WhisCode offers guided enrollment and records three wake samples, three end samples, and three samples for each hands-free key command from your default microphone. Each sample is trimmed with local VAD and then padded to the detector window before it is saved, so the reference WAVs focus on the phrase while still matching the runtime comparison window.

You can also run enrollment directly:

```bash
uv run whiscode-enroll --record
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
```

Hands-free mode also supports eight trained key command slots while idle: `page-up`, `page-down`, `enter`, `shift-enter`, `shift-tab`, `tab`, `arrow-up`, and `arrow-down`. The spoken phrase is whatever you record for that slot; WhisCode maps the detected slot to the physical Page Up, Page Down, Enter, Shift+Enter, Shift+Tab, Tab, Arrow Up, or Arrow Down key action. Command detection is disabled while recording or transcribing so dictated speech cannot press keys.

You can selectively enable key command slots with `~/.config/whiscode/commands.ini`:

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
```

If this file does not exist, all command slots stay enabled for backward compatibility. If it exists, only commands set to `true` are enabled; omitted or `false` commands are ignored and do not need reference samples. Enabled commands still need enough recorded samples before they can load. Override the path with `--hands-free-command-config PATH`; guided enrollment and calibration use the same config by default and accept `--command-config PATH`.

After enrollment, inspect the local detector score separation:

```bash
uv run whiscode-calibrate
```

The report compares wake samples against wake samples, end samples against end samples, command samples against their own command sets, cross-command samples, wake samples against end samples, and recent telemetry trigger distances. Use it to choose threshold changes after observing live runs rather than guessing from one false positive.

Right Shift remains available as a fallback start/stop control while hands-free mode is running.

WhisCode ignores partial detector windows and quiet windows before calling the keyword matcher. This prevents silence and microphone background noise from triggering wake/end phrases. Wake detection also requires two consecutive matching windows by default, which prevents a single noisy match from starting a recording. If your wake phrase is very quiet, lower `--hands-free-min-rms` or `--hands-free-min-active-ratio`, raise `--hands-free-threshold` slightly, or set `--hands-free-wake-confirmations 1`; if your end phrase is not detected, raise `--hands-free-end-threshold` slightly.

WhisCode writes local JSONL telemetry by default to:

```bash
~/Library/Logs/WhisCode/events.jsonl
```

Use it to inspect app startup, selected ASR backend, recording durations, transcription outcomes, backend failures, wake/end/command detections, detector distances, key-command injection outcomes, and suspected rapid trigger loops. `uv run whiscode-calibrate` summarizes hands-free distances alongside reference-sample distances. Telemetry stays on your machine and does not include raw audio, transcripts, prompts, hotword contents, provider payloads, or typed text. Disable it with `--no-telemetry` or write to another file with `--telemetry-path`.

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
# Use a different hotkey
uv run whiscode --hotkey f10

# Transcribe in Chinese
uv run whiscode --language zh

# Add project-specific terms for better accuracy
uv run whiscode --prompt "NextJS, Prisma, tRPC, Zustand"

# Polish output with LLM refinement
uv run whiscode --refine

# Start hands-free mode after importing or recording hands-free samples
uv run whiscode --hands-free
```

## Known Issues

- **Whisper single-language behavior:** In the default MLX Whisper backend, Whisper v3 applies one language to the entire audio clip. Mixed-language speech (e.g., Chinese with English terms) will be forced into whichever language is set, which may cause misrecognition of the other language.
- **Whisper auto-detect picks dominant language:** With `--language auto` in the default MLX Whisper backend, Whisper analyzes the first ~2 seconds of audio to detect the language. If your speech starts in a different language than the main content, detection may be wrong.
