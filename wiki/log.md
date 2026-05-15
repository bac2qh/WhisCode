# WhisCode Maintenance Log

## 2026-05-13
- Added hands-free keyword detection documentation for local start/end phrase triggering.
- Updated hands-free documentation for guided Python microphone enrollment.

## 2026-05-14
- Documented local JSONL telemetry for hands-free diagnostics and guided enrollment.
- Documented hands-free detector speech-energy gating for suppressing silence and partial-window false positives.
- Documented stricter end-threshold tuning for hands-free mode.
- Documented the floating recording overlay with stopwatch and live microphone levels.
- Documented stricter wake defaults and wake confirmation tuning to reduce hands-free false starts from incidental sound.
- Documented VAD-trimmed hands-free enrollment and the local calibration report for threshold tuning.
- Documented trained hands-free key command slots for Page Up, Page Down, and Enter.
- Documented the guided enrollment recording overlay replacing enrollment notification banners.
- Documented recording overlay helper crash diagnostics.
- Documented padding VAD-trimmed reference samples to the detector window length.

## 2026-05-15
- Documented the shared 10-minute recording duration cap and clarified PortAudio overflow telemetry.
- Documented Shift+Enter and Shift+Tab trained hands-free command slots.
- Documented the hands-free audio queue that decouples microphone capture from detector processing.
- Documented Tab, Arrow Up, and Arrow Down trained hands-free command slots.
