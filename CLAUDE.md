# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- **Run the app:** `uv run whiscode`
- **Run with file watching:** `uv run whiscode --input-dir /tmp/whiscode/in --output-dir /tmp/whiscode/out`
- **Run tests:** `uv run pytest` or `uv run pytest tests/test_postprocess.py -v` for single file
- **Install dependencies:** `uv sync`
- **Install Whisper model:** `./install.sh` (downloads ~3GB model to `~/.cache/huggingface/`)

## Architecture

### Data Flow

The voice-to-text pipeline flows through these stages:

1. **Recording** (`recorder.py`): Captures audio via `sounddevice`, resamples to 16kHz if needed using linear interpolation
2. **Transcription** (`transcriber.py`): MLX Whisper with a code-focused prompt (`CODE_PROMPT`) plus optional user hotwords/prompts
3. **Post-processing** (`postprocess.py`): Optional path depending on mode:
   - **Standard mode**: Strip repetitions → apply hotword replacements → symbol substitution (`slash`→`/`) → casing transforms (`camel case foo bar`→`fooBar`) → spelling mode (`spell a b c`→`abc`) → space collapse around punctuation
   - **Refine mode** (`--refine`): Strip repetitions → apply replacements only; passes to LLM
4. **Refinement** (`refiner.py`, optional): HTTP call to local Ollama API (`localhost:11434`), strips `<think>` tags, falls back to original text on any error
5. **Injection** (`injector.py`): Copies text to clipboard via `pbcopy`, simulates Cmd+V paste via `pynput`

### State Machine

The main thread uses a hotkey listener that pushes events to a queue. A worker thread maintains three states:

- `IDLE` → `RECORDING`: On hotkey press, start audio stream
- `RECORDING` → `TRANSCRIBING`: On second hotkey press, stop recording, spawn thread for async processing
- `TRANSCRIBING` → `IDLE`: After transcription/injection completes

The `TRANSCRIBING` state blocks new recordings to prevent overlapping sessions.

### File-Based Transcription

With `--input-dir` and `--output-dir`, WhisCode watches a directory for audio files and processes them sequentially:

- **Hotkey priority**: If recording or transcribing, hotkey takes precedence; file processing waits
- **Busy feedback**: Pressing hotkey during transcription plays "Basso" sound (busy signal)
- **Filesystem events**: Uses `watchdog` for efficient file watching (not polling)
- **Supported formats**: OGG, WAV, MP3, M4A, FLAC (via `soundfile`)
- **Sequential processing**: Files processed in mtime order; new files queue behind existing ones

**Integration pattern** (e.g., Telegram bot):
```python
# Bot drops file
shutil.copy("voice.ogg", "/tmp/whiscode/in/msg_123.ogg")

# Bot polls for result
while not Path("/tmp/whiscode/out/msg_123.txt").exists():
    time.sleep(0.5)
text = Path("/tmp/whiscode/out/msg_123.txt").read_text()
```

### Hotwords System

Users define custom vocabulary and text replacements in `~/.config/whiscode/hotwords.txt`:

- One word/phrase per line adds to the Whisper prompt context
- `wrong -> right` syntax creates case-insensitive replacements applied after transcription

### Key Dependencies

- `mlx-audio[stt]`: Apple Silicon-optimized Whisper inference
- `sounddevice` + `portaudio`: Cross-platform audio capture
- `pynput`: Global hotkey listener and keyboard control
- `numpy`: Audio resampling and array operations
- `watchdog`: Filesystem event monitoring for file-based transcription
- `soundfile`: Audio file loading (OGG, WAV, etc.)

### Testing Patterns

Tests use standard `pytest` with `unittest.mock` for HTTP/API mocking (see `test_refiner.py`). No external test fixtures; tests use temporary files via `tmp_path` fixture.
