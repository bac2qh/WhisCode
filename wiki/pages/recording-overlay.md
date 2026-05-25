# Recording Overlay

WhisCode shows a small floating macOS overlay while normal recording, queued transcription, or active transcription is present. It is hidden when there are no active overlay items.

During recording, the overlay shows:
- elapsed recording time as a stopwatch.
- live microphone level bars.
- a red recording indicator.

Completed recordings enter a FIFO transcription queue. The overlay stacks cards in one top-centered panel, with the newest recording card on top and older queued/transcribing cards pushed down.

During transcription, each card switches to a compact progress view. For backends that report progress, such as MLX Whisper, it shows:
- percentage complete.
- processed and total Whisper frames.
- frames per second when available from the local progress source.

For backends without an in-flight progress source, the overlay still shows queued/transcribing state but does not show concrete percentage or FPS progress. The current CrispASR/VibeVoice warm-server integration is in this category because WhisCode sends one blocking `/v1/audio/transcriptions` request and receives only the final transcript.

The overlay is implemented as a separate AppKit helper process controlled by the main WhisCode process through newline-delimited JSON commands. Runtime recording/transcription cards use stable job ids so a card can move from recording to queued to transcribing before it disappears. If the helper cannot start, recording and transcription continue without the overlay. If the parent command stream closes, the helper treats EOF as a stop command so orphaned panels do not remain on screen. The helper also monitors its parent PID and exits if the parent process disappears before stdin reaches EOF.

Before launching a new helper, WhisCode removes stale orphan helpers whose parent process is already gone. Manual cleanup is available with `python -m whiscode.recording_overlay --cleanup-orphans`.

If the helper exits unexpectedly after startup, WhisCode disables the overlay for the current process and reports bounded diagnostic metadata through `recording_overlay.disabled` telemetry and stderr. Orphan cleanup emits `recording_overlay.orphan_cleanup` with helper counts only. Diagnostics include lifecycle stage, return code, and counts only; they do not include audio or transcribed text.

Use `--no-recording-overlay` to disable both recording and transcription overlay states. Use `--recording-notifications` with `whiscode` to keep macOS start/end notification banners in addition to the overlay during normal recording.

Guided enrollment uses the same overlay for each recorded sample and no longer shows notification banners. It can be disabled with `uv run whiscode-enroll --record --no-recording-overlay`.
