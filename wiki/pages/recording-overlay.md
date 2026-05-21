# Recording Overlay

WhisCode shows a small floating macOS overlay while normal recording or transcription is active. It is hidden while idle and after transcription finishes.

During recording, the overlay shows:
- elapsed recording time as a stopwatch.
- live microphone level bars.
- a red recording indicator.

During transcription, the same overlay switches to a compact progress view that shows:
- percentage complete.
- processed and total Whisper frames.
- frames per second when available from the local progress source.

Before audio reaches Whisper, WhisCode applies bounded gain normalization to quiet recordings. The normalizer targets a usable RMS level, caps boost at `8x`, and peak-limits output at `0.95` to avoid clipping. Hands-free wake, end, and command detectors continue to use raw microphone audio so detector thresholds and enrolled references remain comparable.

The overlay is implemented as a separate AppKit helper process controlled by the main WhisCode process through newline-delimited JSON commands. If the helper cannot start, recording and transcription continue without the overlay. If the parent command stream closes, the helper treats EOF as a stop command so orphaned panels do not remain on screen.

If the helper exits unexpectedly after startup, WhisCode disables the overlay for the current process and reports bounded diagnostic metadata through `recording_overlay.disabled` telemetry and stderr. Audio normalization emits `audio.normalization_applied` with bounded RMS, peak, gain, sample-count, duration, and source metadata when a boost is applied. Diagnostics do not include raw audio or transcribed text.

Use `--no-recording-overlay` to disable both recording and transcription overlay states. Use `--recording-notifications` with `whiscode` to keep macOS start/end notification banners in addition to the overlay during normal recording.

Guided enrollment uses the same overlay for each recorded sample and no longer shows notification banners. It can be disabled with `uv run whiscode-enroll --record --no-recording-overlay`.
