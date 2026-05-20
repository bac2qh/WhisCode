# Transcription Progress Overlay

## Summary
Add a compact top-screen transcription overlay using the existing AppKit recording overlay helper. It will appear after recording stops, show `Transcribing`, percent complete, processed/total frames, and frames/sec when available, then hide when the app returns to idle.

## Key Changes
- Extend `RecordingOverlayClient` with transcription commands while preserving existing recording behavior: `show()` still means recording, and new methods handle `show_transcribing()`, progress updates, completion/failure, and hide.
- Update the helper view to render two modes:
  - Recording: unchanged stopwatch plus live waveform bars.
  - Transcribing: compact progress bar with bounded text such as `Transcribing 73% 3486/4775 frames 4309 fps`.
- Capture MLX Whisper progress by wrapping its internal `tqdm.tqdm` during `transcribe(...)`, not by scraping terminal output. Keep the terminal progress bar working.
- In `start_transcription`, show an indeterminate transcription overlay immediately, pass progress callbacks into `transcribe`, mark 100% on completion, and hide in `finally`.
- Add a send lock around overlay IPC writes so recording level updates, transcription progress, hide, and stop commands cannot interleave JSON lines.

## Interfaces And Diagnostics
- No new CLI flag. Existing `--no-recording-overlay` disables both recording and transcription overlays.
- Existing telemetry remains the main diagnostic surface: `transcription.started`, `transcription.completed`, `transcription.failed`, and `recording_overlay.disabled`.
- Overlay progress data stays UI-only and bounded: frame counts, percent, rate, elapsed; no audio, transcript, prompt, hotwords, or provider payloads.

## Test Plan
- Add/extend overlay client tests for transcription command serialization, progress clamping, hide/stop behavior, and helper-exit diagnostics with new command stages.
- Add transcriber unit tests using a fake MLX Whisper model/module to verify progress callbacks receive total/current/rate snapshots and the original `tqdm` object is restored after success or failure.
- Run targeted tests: `.venv/bin/python -m pytest tests/test_recording_overlay.py tests/test_main_cli.py` plus the new transcriber tests.

## Assumptions
- Use the selected compact bar style, not a literal terminal text clone.
- Use this task worktree for tracked plan/checkpoint/source/doc/memory state, then close out through local `main` after verification.
