# Hands-Free Keyword Detection

WhisCode supports an optional hands-free mode that keeps the microphone open and uses local keyword matching to start and stop capture. The existing Right Shift hotkey remains available as a fallback while hands-free mode is running.

## Enrollment

The normal enrollment path records samples directly from the default microphone:

```bash
uv run whiscode-enroll --record
```

This records three wake samples followed by three end samples, trims leading and trailing silence with local VAD, pads each result to the detector window, then writes 16 kHz mono WAV files under `~/.config/whiscode/wake/`.

Existing audio files can still be imported manually:

```bash
uv run whiscode-enroll wake wake1.m4a wake2.m4a wake3.m4a
uv run whiscode-enroll end end1.m4a end2.m4a end3.m4a
```

## Runtime

Start hands-free mode with:

```bash
uv run whiscode --hands-free
```

If either reference folder has fewer than three WAV files, startup offers to run guided enrollment before loading the wake detectors. Use `--no-enroll-prompt` to fail fast instead.

The wake phrase starts capture, the end phrase stops capture, and the captured audio between those phrases is passed to Whisper. WhisCode waits until a detector window is fully populated and has enough speech-like energy before calling the keyword matcher, so silence and low-level room noise do not trigger wake/end detection. Wake detection uses a stricter default threshold and requires two consecutive matching windows before recording starts. Use `--hands-free-debug` to print detector distances while tuning `--hands-free-threshold`, `--hands-free-end-threshold`, and `--hands-free-wake-confirmations`.

The speech-energy gate can be tuned with `--hands-free-min-rms`, `--hands-free-min-active-ratio`, and `--hands-free-active-level`.

Inspect reference and telemetry distance distributions with:

```bash
uv run whiscode-calibrate
```

Use the report to decide threshold changes after re-enrollment and live observation.

## Telemetry

Hands-free mode and guided enrollment write local JSONL telemetry by default:

```bash
~/.config/whiscode/telemetry/events.jsonl
```

The telemetry records app lifecycle, enrollment progress, reference counts, detector load results, audio loop status, detector gate summaries, throttled detector distance summaries, wake/end detections, recording durations, transcription outcomes, and suspected rapid trigger loops. It does not record raw audio, transcripts, prompts, hotword contents, or typed text.

Use `--telemetry-path PATH` to write to another JSONL file, or `--no-telemetry` to disable local telemetry.
