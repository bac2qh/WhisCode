# Add Local Telemetry For Hands-Free Loop Diagnosis

## Summary
Add local-only structured telemetry so a hands-free wake/end/transcribe/resume loop can be diagnosed after a run. Keep behavior unchanged for this pass: no cooldowns, auto-pauses, threshold changes, or detector tuning.

Use the task worktree branch `add-handsfree-telemetry`. Leave unrelated untracked `.agents` files on the main checkout untouched.

## Key Changes
- Add a `whiscode.telemetry` module that writes JSONL events to `~/.config/whiscode/telemetry/events.jsonl`.
- Add CLI controls to `whiscode` and `whiscode-enroll`: `--telemetry-path PATH` and `--no-telemetry`.
- Enable telemetry by default for `--hands-free` and guided enrollment paths.
- Log safe, bounded events for app lifecycle, enrollment, reference counts, detector setup, audio loop status, hands-free transitions, wake/end detections, timeouts, transcription lifecycle, and suspected rapid trigger loops.
- Add throttled detector distance summaries instead of per-frame JSON spam.
- Do not log raw audio, transcripts, prompts, hotword contents, typed text, full provider payloads, or imported audio contents.

## Tests And Verification
- Unit-test telemetry JSONL writing, disabled mode, directory creation, and JSON-safe event shape.
- Unit-test CLI parsing for telemetry flags.
- Unit-test hands-free telemetry with fake detectors for wake, end, timeout, suspend/resume, and distance summaries.
- Unit-test guided enrollment telemetry with fake capture functions.
- Run the existing test suite plus `uv run whiscode --help` and `uv run whiscode-enroll --help`.
- Document how to inspect the latest telemetry file in `README.md`.

## Assumptions
- The observed loop was repeated hands-free recording/transcription cycles after wake/end detection.
- Telemetry is local JSONL by default, not networked telemetry.
- This change is diagnostic only; any cooldown or auto-pause guard will be a separate follow-up after inspecting events.
