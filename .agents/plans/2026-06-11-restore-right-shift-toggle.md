# Restore Right Shift Toggle Controls

Date: 2026-06-11
Branch: `restore-right-shift-toggle`
Worktree: `.agents/worktrees/restore-right-shift-toggle`
Status: active

## Objective

Restore manual recording to the old single-key model: plain Right Shift starts recording, and plain Right Shift again stops/finalizes it.

## Scope

- Remove the dedicated manual end hotkey CLI path added for `--end-hotkey`.
- Keep `--hotkey`, default `shift_r`, as the manual recording toggle key.
- Ignore Right Option + Right Shift entirely for manual hotkey handling.
- Preserve hands-free wake-phrase Send Chunk behavior and deferred batch flushing.
- Update tests, README, wiki, and project memory so they describe the restored behavior.

## Public Interface

- `--hotkey` remains and is documented as a recording toggle.
- `--end-hotkey` is removed; argparse should reject it as an unknown option.
- No new CLI flags, config files, or persistent data formats.

## Validation Contract

- VC-001 critical: Plain Right Shift toggles start/stop in hotkey mode. Evidence: focused unit tests.
- VC-002 critical: Right Option + Right Shift emits no manual action and does not Send Chunk. Evidence: router unit test.
- VC-003 critical: F10 no longer ends/finalizes recording and `--end-hotkey` is not accepted. Evidence: parser/router tests.
- VC-004 important: Hands-free wake-phrase Send Chunk and deferred batch flush behavior still work. Evidence: existing deferred delivery tests kept/passing.
- VC-005 important: Docs no longer claim F10 or manual Send Chunk chord support. Evidence: static review plus `rg` for stale references.

## Telemetry / Debuggability

No new telemetry signal is needed because this restores the previous manual toggle shape and removes a CLI/event branch. Implementation should remove stale manual-end or manual-Send-Chunk labels from code/docs/tests if present, while preserving existing recording, hands-free, and deferred delivery diagnostics.

## Implementation Plan

1. Inspect existing CLI, hotkey router, worker loop, tests, and docs for the F10/end-hotkey and manual Send Chunk paths.
2. Replace primary/end routing with a toggle router:
   - Plain configured `--hotkey` emits a toggle event.
   - Right Option held while Right Shift is pressed emits no event.
   - F10 has no special handling or macOS suppression.
3. Update hotkey worker behavior:
   - Idle/transcribing plus toggle starts recording.
   - Recording plus toggle stops and queues the recording.
   - Timeout still finalizes an active recording.
   - Manual hotkeys no longer request or restart Send Chunk.
4. Update focused tests and any parser/router coverage for removed `--end-hotkey`.
5. Update README/wiki/memory to describe Right Shift start/stop and hands-free-only Send Chunk.
6. Verify with focused tests, full tests if feasible, `git diff --check`, stale-reference search, and independent validator review if available.

## Test Plan

- `uv run --with pytest python -m pytest tests/test_main_cli.py`
- `uv run --with pytest python -m pytest`
- `git diff --check`
- `rg` for stale F10/end-hotkey/manual Send Chunk documentation.

## Assumptions

- "Right Shift, Right Option + Right Shift combo does not do anything" means the combo is ignored entirely, not treated as a plain Right Shift toggle.
- Hands-free voice Send Chunk remains in scope and should not be removed.
- Stale `manual_end_hotkey` or manual hotkey `send_chunk` labels should be removed from code/docs/tests.
