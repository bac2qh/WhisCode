# Memory Log

## 2026-05-13
- Added recording status notification memory after replacing recording start/stop sounds with silent macOS banners.
- Added hands-free keyword detection memory after implementing local wake/end phrase triggering and Voice Memo sample import.
- Added guided hands-free enrollment memory after implementing Python microphone recording for wake/end reference samples.

## 2026-05-14
- Added hands-free telemetry memory after implementing local JSONL diagnostics for repeated hands-free trigger loops.
- Added signal-safe telemetry shutdown memory after fixing the Ctrl+C handler regression.
- Added hands-free speech-energy gate memory after preventing silence and partial-window false positives from reaching the keyword detector.
- Added hands-free end-threshold memory after splitting wake and end detection thresholds to reduce premature stop detections.
- Added repository hygiene memory after ignoring local `.agents` runtime/worktree/lock state while keeping durable agent project state tracked.
- Added recording overlay memory after replacing normal recording banners with a floating stopwatch and live microphone-level UI.
- Added hands-free wake confirmation memory after tightening wake defaults to reduce false starts from incidental sound.
- Added hands-free enrollment calibration memory after trimming reference samples with local VAD and adding a local distance report command.
- Added hands-free reference padding memory after fixing short VAD-trimmed references that no longer matched the runtime detector window.

## 2026-05-15
- Added hands-free key command memory after implementing trained Page Up, Page Down, and Enter voice command slots.
- Added enrollment overlay memory after replacing guided enrollment notification banners with the floating recording overlay.
- Added recording overlay crash memory after fixing AppKit timer text drawing and adding helper crash diagnostics.
- Added shared recording duration cap memory after bounding manual and hands-free recording length by default.
- Added shift key command memory after extending trained hands-free commands with Shift+Enter and Shift+Tab slots.
