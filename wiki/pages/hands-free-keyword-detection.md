# Hands-Free Keyword Detection

WhisCode supports an optional hands-free mode that keeps the microphone open and uses local keyword matching to start and stop capture. The existing Right Shift hotkey remains available as a fallback while hands-free mode is running.

## Enrollment

The normal enrollment path records samples directly from the default microphone:

```bash
uv run whiscode-enroll --record
```

This records three wake samples, three end samples, and three samples for each key command slot. The command slots are `page-up`, `page-down`, and `enter`; the spoken phrase for each slot is arbitrary and comes from the user's recorded samples. Enrollment trims leading and trailing silence with local VAD, pads each result to the detector window, then writes 16 kHz mono WAV files under `~/.config/whiscode/wake/`.

Existing audio files can still be imported manually:

```bash
uv run whiscode-enroll wake wake1.m4a wake2.m4a wake3.m4a
uv run whiscode-enroll end end1.m4a end2.m4a end3.m4a
uv run whiscode-enroll page-up pageup1.m4a pageup2.m4a pageup3.m4a
```

## Runtime

Start hands-free mode with:

```bash
uv run whiscode --hands-free
```

If any wake, end, or command reference folder has fewer than three WAV files, startup offers to run guided enrollment before loading the wake detectors. Use `--no-enroll-prompt` to fail fast instead.

The wake phrase starts capture, the end phrase stops capture, and the captured audio between those phrases is passed to Whisper. WhisCode waits until a detector window is fully populated and has enough speech-like energy before calling the keyword matcher, so silence and low-level room noise do not trigger wake/end detection. Wake detection uses a stricter default threshold and requires two consecutive matching windows before recording starts. Use `--hands-free-debug` to print detector distances while tuning `--hands-free-threshold`, `--hands-free-end-threshold`, and `--hands-free-wake-confirmations`.

While idle, WhisCode also checks the three trained command slots. A confirmed `page-up`, `page-down`, or `enter` command taps the corresponding physical key through `pynput`. Command detection is disabled while recording or transcribing so dictated text cannot inject keys. Tune commands separately with `--hands-free-command-threshold` and `--hands-free-command-confirmations`.

The speech-energy gate can be tuned with `--hands-free-min-rms`, `--hands-free-min-active-ratio`, and `--hands-free-active-level`.

Recordings auto-finalize after `--max-recording-seconds`, which defaults to `600.0` seconds and also applies to Right Shift recording. Set it to `0` to disable the cap. The legacy `--hands-free-max-seconds` flag remains available as a hands-free-only override. This bounds buffered audio and transcription work after accidental wake detections.

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

The telemetry records app lifecycle, enrollment progress, reference counts, detector load results, audio loop status, detector gate summaries, throttled detector distance summaries, wake/end/command detections, key-command injection outcomes, recording durations, transcription outcomes, and suspected rapid trigger loops. It does not record raw audio, transcripts, prompts, hotword contents, or typed text.

`handsfree.audio_overflow` means PortAudio reported that the microphone read loop fell behind. It is not a direct macOS swap or memory-overflow signal, but it is useful evidence when correlating accidental wake loops with system load.

Use `--telemetry-path PATH` to write to another JSONL file, or `--no-telemetry` to disable local telemetry.
