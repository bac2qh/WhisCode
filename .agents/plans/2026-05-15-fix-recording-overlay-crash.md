# Fix Invisible Recording Overlay Crash

## Summary

The recording overlay helper crashes during drawing because `drawRect_` calls an Objective-C drawing selector on a Python `str`. Fix the timer text drawing path so the AppKit helper stays alive and the floating overlay appears during normal recording and guided enrollment.

## Key Changes

- Draw the timer text through `NSAttributedString` instead of calling `drawAtPoint_withAttributes_` on a Python string.
- Keep existing overlay position, red dot, waveform bars, timer style, and show/hide behavior unchanged.
- Add bounded helper crash diagnostics so an unexpected overlay helper exit is visible in stderr and telemetry instead of silently failing.
- Keep Notification Center banners disabled by default; do not restore banners as fallback unless `--recording-notifications` is explicitly used.

## Telemetry And Diagnostics

- Emit or print only helper lifecycle metadata: return code, operation stage, and error class if available.
- Do not log audio, transcripts, prompts, or typed text.

## Test Plan

- Unit-test timer text drawing uses an attributed string draw path.
- Unit-test helper process crash detection disables the overlay and reports a bounded diagnostic.
- Run `uv run --with pytest python -m pytest`.
- Run `uv run whiscode --help` and `uv run whiscode-enroll --help`.
- Run a live overlay helper probe that sends `show`, `level`, and `stop`, and verify the helper stays alive until `stop` without SIGTRAP.

## Assumptions

- The overlay design is acceptable; the issue is helper crash, not layout or styling.
- The shared helper fix applies to both normal recording and guided enrollment.
- The live probe may briefly show the overlay during verification.
