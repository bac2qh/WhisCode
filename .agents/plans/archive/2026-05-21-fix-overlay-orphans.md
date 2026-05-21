# Fix Stuck Recording Overlay Helpers

## Closeout

- Final status: implemented.
- Related checkpoint: `.agents/checkpoints/2026-05-21-fix-overlay-orphans-checkpoints.md`.
- Implementation commits: `b8d9f0d` (overlay helper lifecycle hardening), `d5080b3` (checkpoint hash update).
- Merge commit: none; local `main` fast-forwarded to `d5080b3`.
- Verification performed: `uv run --with pytest pytest tests/test_recording_overlay.py tests/test_main_cli.py`, `uv run --with pytest pytest`, `uv run python -m whiscode.recording_overlay --cleanup-orphans`, and `git diff --check`.
- Worktree and branch cleanup: removed `.agents/worktrees/fix-overlay-orphans`; deleted local branch `fix-overlay-orphans`.
- Summary: overlay helpers now monitor their parent PID, WhisCode cleans stale PPID `1` helpers before launch, and a manual orphan-cleanup CLI is available.

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
