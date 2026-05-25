# Document CrispASR/VibeVoice Progress Limitation

## Summary

Update docs to make clear that WhisCode cannot show concrete in-flight progress for the current CrispASR/VibeVoice HTTP integration. This is documentation-only: no CLI, telemetry, parser, overlay, or backend behavior changes.

## Key Changes

- Update `README.md` in the CrispASR/VibeVoice section:
  - State that `/v1/audio/transcriptions` is a blocking final-response API for WhisCode's current integration.
  - State that CrispASR/VibeVoice does not currently expose per-request progress, token progress, or stage progress through that API.
  - Clarify that the overlay can show queued/transcribing state for VibeVoice, but not a meaningful percent/FPS progress bar.
  - Mention that CrispASR CLI streaming/live modes are separate paths and are not the same as WhisCode's warm-server full-recording flow.
- Update `README.md` Recording Overlay wording so percentage/frames/FPS is described as backend-dependent, currently available when the backend reports progress such as MLX Whisper.
- Update current-state docs consistently:
  - `wiki/pages/asr-backends.md` with the same CrispASR limitation.
  - `wiki/pages/recording-overlay.md` with backend-specific progress behavior.
  - Append a short dated entry to `wiki/log.md`.

## Telemetry / Debuggability

Telemetry not applicable: this is a documentation-only change and does not alter runtime behavior, signals, logs, model calls, queues, or user data handling.

## Verification

- Run `git diff --check`.
- Use `rg` to verify the README and wiki mention the limitation consistently.
- No pytest run required unless implementation accidentally touches code.

## Assumptions

- "Update readme" means README plus the repo's current-state wiki docs, because this repo treats `wiki/` as maintained durable documentation.
- The docs should avoid promising an estimated progress bar; they should describe the current limitation and the real requirement for future progress support: CrispASR exposing progress through a server-side API or event stream.
