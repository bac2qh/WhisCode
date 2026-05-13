# Hands-Free Keyword Detection

WhisCode supports an optional hands-free mode that keeps the microphone open and uses local keyword matching to start and stop capture. The existing Right Shift hotkey remains available as a fallback while hands-free mode is running.

## Enrollment

Record at least three samples for each phrase with Voice Memos or another recorder. Import them with:

```bash
uv run whiscode-enroll wake wake1.m4a wake2.m4a wake3.m4a
uv run whiscode-enroll end end1.m4a end2.m4a end3.m4a
```

The import command converts samples to 16 kHz mono WAV files under `~/.config/whiscode/wake/`.

## Runtime

Start hands-free mode with:

```bash
uv run whiscode --hands-free
```

The wake phrase starts capture, the end phrase stops capture, and the captured audio between those phrases is passed to Whisper. Use `--hands-free-debug` to print detector distances while tuning `--hands-free-threshold`.
