# Hands-Free Keyword Detection

WhisCode supports an optional hands-free mode that keeps the microphone open and uses local keyword matching to start and stop capture. The existing Right Shift hotkey remains available as a fallback while hands-free mode is running.

## Enrollment

The normal enrollment path records samples directly from the default microphone:

```bash
uv run whiscode-enroll --record
```

This records three wake samples, three end samples, and three samples for each key command slot. The command slots are `page-up`, `page-down`, `enter`, `shift-enter`, `shift-tab`, `tab`, `arrow-up`, and `arrow-down`; the spoken phrase for each slot is arbitrary and comes from the user's recorded samples. Enrollment trims leading and trailing silence with local VAD, pads each result to the detector window, then writes 16 kHz mono WAV files under `~/.config/whiscode/wake/`.

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

## Runtime

Start hands-free mode with:

```bash
uv run whiscode --hands-free
```

If any wake, end, or command reference folder has fewer than three WAV files, startup offers to run guided enrollment before loading the wake detectors. Use `--no-enroll-prompt` to fail fast instead.

The wake phrase starts capture, the end phrase stops capture, and the captured audio between those phrases is passed to the selected ASR backend through the shared transcription queue. WhisCode continuously drains microphone audio into a bounded detector queue and runs detector work on a separate worker, so wake/end/command matching does not block the PortAudio read loop. The detector still uses the configured sliding window and slide interval; `--hands-free-audio-queue-seconds` controls how much queued detector audio can build up before oldest chunks are dropped.

WhisCode waits until a detector window is fully populated and has enough speech-like energy before calling the keyword matcher, so silence and low-level room noise do not trigger wake/end detection. Wake detection uses a stricter default threshold and requires two consecutive matching windows before recording starts. Use `--hands-free-debug` to print detector distances while tuning `--hands-free-threshold`, `--hands-free-end-threshold`, and `--hands-free-wake-confirmations`.

While not actively recording, WhisCode also checks the eight trained command slots. A confirmed `page-up`, `page-down`, `enter`, `shift-enter`, `shift-tab`, `tab`, `arrow-up`, or `arrow-down` command taps the corresponding physical key or key combo through `pynput`. Command detection is disabled while recording so dictated text cannot inject keys, but it can run while earlier recordings are queued or transcribing. Tune commands separately with `--hands-free-command-threshold` and `--hands-free-command-confirmations`.

While actively recording, WhisCode reuses the wake phrase as Send Chunk. A confirmed wake phrase during recording trims the spoken wake phrase tail using the inferred active span of the wake references plus `--hands-free-tail-extra-seconds`, queues the chunk into an in-memory delivery batch with a blank line after the transcript, and immediately starts a new recording. Intermediate chunks still print to stdout as they transcribe, but clipboard copy and Cmd+V paste are deferred until the final end phrase, manual stop, or timeout completes the batch.

Hotkey mode and the hands-free fallback hotkey also support Send Chunk manually: hold Right Option and press Right Shift while recording. That chord suppresses the plain Right Shift toggle for the press, queues the current recording into the same in-memory batch with the same blank-line suffix, and immediately starts the next recording. Hotkey-only Send Chunk uses the same deferred final paste behavior.

The speech-energy gate can be tuned with `--hands-free-min-rms`, `--hands-free-min-active-ratio`, and `--hands-free-active-level`.

When the end phrase stops a recording, WhisCode discards the buffered tail that contains the spoken end phrase before queueing audio for transcription. By default, the base tail length is inferred from the enrolled end-phrase WAVs: each readable reference is measured from the first through last sample whose absolute level is at least `--hands-free-active-level`, and the session uses the median valid active span. `--hands-free-tail-seconds FLOAT` remains an explicit base-tail override. If no valid active span can be computed, WhisCode falls back to a `1.0` second base tail. WhisCode then adds `--hands-free-tail-extra-seconds`, which defaults to `1.0` second, as an end-detection lag buffer. Set `--hands-free-tail-extra-seconds 0` to restore the previous base-only trim. Right Shift/manual stops and timeout stops still keep the pending tail.

Recordings auto-finalize after `--max-recording-seconds`, which defaults to `600.0` seconds and also applies to Right Shift recording. Set it to `0` to disable the cap. The legacy `--hands-free-max-seconds` flag remains available as a hands-free-only override. Finished recordings enter a FIFO transcription queue with up to five waiting jobs, so wake/end recordings can continue while earlier audio transcribes.

Inspect reference and telemetry distance distributions with:

```bash
uv run whiscode-calibrate
```

Use the report to decide threshold changes after re-enrollment and live observation.

## Telemetry

WhisCode runtime and guided enrollment write local JSONL telemetry by default:

```bash
~/Library/Logs/WhisCode/events.jsonl
```

The telemetry records app lifecycle, selected ASR backend, enrollment progress, reference counts, detector load results, end and wake-as-chunk tail-trim resolution source and counts, Send Chunk request/queue/restart/reject outcomes, deferred delivery buffer/skip/flush outcomes, audio loop status, detector gate summaries, throttled detector distance summaries, wake/end/wake-as-chunk/command detections, key-command injection outcomes, recording durations, transcription queue depth, transcription outcomes, backend failure shape diagnostics, audio queue backlog/drop summaries, detector processing summaries, and suspected rapid trigger loops. Routine telemetry does not record raw audio, transcripts, prompts, hotword contents, provider payloads, or typed text. CrispASR malformed-response debugging is the exception: when VibeVoice chunk parsing fails or needs recovery, WhisCode writes the original provider response body to local-only `crispasr-raw-responses.jsonl`, which can contain transcript or provider output text. Successful transcripts remain visible in stdout for local copying instead of being copied into telemetry.

`handsfree.audio_overflow` means PortAudio reported that the microphone read loop fell behind. `handsfree.audio_queue_dropped`, `handsfree.audio_queue_summary`, and `handsfree.detector_processing_summary` help determine whether detector work is falling behind the live microphone stream. These are not direct macOS swap or memory-overflow signals.

Use `--telemetry-path PATH` to write to another JSONL file, or `--no-telemetry` to disable local telemetry.
