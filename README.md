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
./install.sh
```

The install script will:
- Install [uv](https://docs.astral.sh/uv/) if not present
- Install Python dependencies
- Download the Whisper large-v3 model (~3GB)

## Usage

```bash
uv run whiscode
```

Press **Right Shift** to start recording, press again to stop. The transcribed text is typed at your cursor position.

### Options

```
--hotkey HOTKEY    Toggle key for recording (default: shift_r)
--language LANG    Language code, e.g. en, zh, ja, de (default: auto). Use 'auto' to detect from audio.
--prompt TEXT      Additional context to improve transcription accuracy
```

### Examples

```bash
# Use a different hotkey
uv run whiscode --hotkey f10

# Add project-specific terms for better accuracy
uv run whiscode --prompt "NextJS, Prisma, tRPC, Zustand"

# Transcribe in Chinese
uv run whiscode --language zh

# Auto-detect language (detects from audio)
uv run whiscode --language auto
```

## Known Issues

- **Single-language per recording:** Whisper v3 applies one language to the entire audio clip. Mixed-language speech (e.g., Chinese with English terms) will be forced into whichever language is set, which may cause misrecognition of the other language.
- **Auto-detect picks dominant language:** With `--language auto`, Whisper analyzes the first ~2 seconds of audio to detect the language. If your speech starts in a different language than the main content, detection may be wrong.
