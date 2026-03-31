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
```

## Known Issues

- **Single-language per recording:** Whisper v3 applies one language to the entire audio clip. Mixed-language speech (e.g., Chinese with English terms) will be forced into whichever language is set, which may cause misrecognition of the other language.
- **Auto-detect picks dominant language:** With `--language auto`, Whisper analyzes the first ~2 seconds of audio to detect the language. If your speech starts in a different language than the main content, detection may be wrong.
