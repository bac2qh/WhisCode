# WhisCode

Voice-to-keyboard for code dictation on macOS. Press a hotkey, speak, and your words are typed into any text field. Powered by [MLX Whisper](https://github.com/ml-explore/mlx-examples) for fast on-device transcription on Apple Silicon.

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

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--hotkey HOTKEY` | `shift_r` | Toggle key for recording |
| `--language LANG` | `auto` | Language code (e.g. `en`, `zh`, `ja`) or `auto` to detect from audio |
| `--prompt TEXT` | — | Additional context to improve transcription accuracy |
| `--hotwords-file PATH` | `~/.config/whiscode/hotwords.txt` | Path to hotwords/replacements config file |
| `--refine` | off | Polish transcription with a local Ollama LLM (prose mode) |
| `--refine-model MODEL` | `qwen3.5:4b` | Ollama model to use for refinement |
| `--hands-free` | off | Use local start/end phrase detection instead of Right Shift as the primary trigger |
| `--hands-free-threshold FLOAT` | `0.1` | Detection threshold for wake phrase matching |
| `--hands-free-end-threshold FLOAT` | `0.055` | Detection threshold for end phrase matching |
| `--hands-free-tail-seconds FLOAT` | `1.0` | Audio tail to discard when the end phrase is detected |
| `--hands-free-min-rms FLOAT` | `0.006` | Minimum detector-window RMS before keyword matching |
| `--hands-free-min-active-ratio FLOAT` | `0.05` | Minimum ratio of active samples before keyword matching |
| `--hands-free-active-level FLOAT` | `0.01` | Absolute sample level counted as active |
| `--hands-free-debug` | off | Print detector distances for threshold tuning |
| `--no-enroll-prompt` | off | Exit instead of offering guided enrollment when samples are missing |
| `--telemetry-path PATH` | `~/.config/whiscode/telemetry/events.jsonl` | Local JSONL telemetry path |
| `--no-telemetry` | off | Disable local telemetry |
| `--recording-overlay` | on | Show floating recording stopwatch/waveform overlay |
| `--no-recording-overlay` | off | Disable floating recording overlay |
| `--recording-notifications` | off | Keep macOS start/end notification banners in addition to overlay |

## Recording Overlay

WhisCode shows a small floating macOS overlay while recording. The overlay hides when recording stops, shows an elapsed stopwatch, and renders live microphone levels as waveform bars.

Use `--no-recording-overlay` to disable it. Use `--recording-notifications` if you also want the older macOS start/end notification banners.

## Hands-Free Mode

Hands-free mode keeps the microphone open and uses local keyword matching for your recorded start and end phrases. Whisper only receives the captured audio between those phrases.

Start hands-free mode:

```bash
uv run whiscode --hands-free
```

If samples are missing, WhisCode offers guided enrollment and records three 2-second wake samples followed by three 2-second end samples from your default microphone.

You can also run enrollment directly:

```bash
uv run whiscode-enroll --record
```

Existing audio files can still be imported manually:

```bash
uv run whiscode-enroll wake wake1.m4a wake2.m4a wake3.m4a
uv run whiscode-enroll end end1.m4a end2.m4a end3.m4a
```

Right Shift remains available as a fallback start/stop control while hands-free mode is running.

WhisCode ignores partial detector windows and quiet windows before calling the keyword matcher. This prevents silence and microphone background noise from triggering wake/end phrases. End detection uses a stricter threshold than wake detection because false end matches prematurely stop recording. If your wake phrase is very quiet, lower `--hands-free-min-rms` or `--hands-free-min-active-ratio`; if your end phrase is not detected, raise `--hands-free-end-threshold` slightly.

Hands-free mode and guided enrollment write local JSONL telemetry to:

```bash
~/.config/whiscode/telemetry/events.jsonl
```

Use it to inspect wake/end detections, detector distances, recording durations, transcription outcomes, and suspected rapid trigger loops. Telemetry stays on your machine and does not include raw audio, transcripts, prompts, hotword contents, or typed text. Disable it with `--no-telemetry` or write to another file with `--telemetry-path`.

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

# Start hands-free mode after importing wake/end samples
uv run whiscode --hands-free
```

## Known Issues

- **Single-language per recording:** Whisper v3 applies one language to the entire audio clip. Mixed-language speech (e.g., Chinese with English terms) will be forced into whichever language is set, which may cause misrecognition of the other language.
- **Auto-detect picks dominant language:** With `--language auto`, Whisper analyzes the first ~2 seconds of audio to detect the language. If your speech starts in a different language than the main content, detection may be wrong.
