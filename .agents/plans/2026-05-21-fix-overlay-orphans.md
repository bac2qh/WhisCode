# Fix Stuck Recording Overlay Helpers

## Goal

Prevent AppKit recording overlay helper processes from remaining visible or orphaned when WhisCode is interrupted during recording, especially via Ctrl-C.

## Scope

- Add helper-side parent PID monitoring so the overlay exits if its WhisCode parent disappears without clean stdin EOF.
- Add parent-side stale helper cleanup before launching a new overlay helper.
- Add a maintenance CLI mode to clean orphan helpers manually.
- Make main runtime shutdown more robust so first Ctrl-C reaches overlay and recorder cleanup when possible.
- Update tests, docs, checkpoints, and memory.

## Telemetry And Diagnostics

- Emit bounded `recording_overlay.orphan_cleanup` telemetry when startup cleanup finds stale helpers.
- Include only counts: `found_count`, `terminated_count`, and `failed_count`.
- Do not emit command lines, transcript text, raw audio, prompts, hotwords, or user content.

## Verification

- Unit tests for helper launch arguments, parent watchdog behavior, orphan selection/cleanup, cleanup failures, and CLI cleanup mode.
- Existing overlay tests must remain green.
- Full test suite should pass.
- Manual cleanup command should remove orphan helpers with PPID `1` without touching active WhisCode helpers.
