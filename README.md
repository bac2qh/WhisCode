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
--language LANG    Language code (default: en)
--prompt TEXT      Additional context to improve transcription accuracy
```

### Examples

```bash
# Use a different hotkey
uv run whiscode --hotkey f10

# Add project-specific terms for better accuracy
uv run whiscode --prompt "NextJS, Prisma, tRPC, Zustand"
```

## Known Issues

- **Audio thread safety:** The audio recorder's internal buffer is accessed from both the audio callback thread and the main thread without a lock. In practice this is protected by CPython's GIL and the narrow timing window, but it could theoretically cause issues if a late audio callback fires during transcription. Not currently planned to fix.
