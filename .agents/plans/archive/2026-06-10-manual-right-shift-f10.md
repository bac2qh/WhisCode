# Closeout Note

Final status: complete
Related checkpoint: `.agents/checkpoints/2026-06-10-manual-right-shift-f10-checkpoints.md`
Implementation commits: `74bf2b6` (implementation), `65c78a0` (checkpoint bookkeeping)
Merge commit: none; local `main` was fast-forwarded to `65c78a0`
Verification performed:
- `uv run python -m py_compile whiscode/main.py tests/test_main_cli.py`
- `uv run --with pytest python -m pytest tests/test_main_cli.py`
- `uv run --with pytest python -m pytest tests/test_handsfree.py tests/test_transcription_queue.py`
- `uv run --with pytest python -m pytest` (294 passed)
- `git diff --check`
- Validator Workflow with `mission_validator`: APPROVE, no findings, VC-001 through VC-007 passed
Worktree/branch cleanup: removed `.agents/worktrees/manual-right-shift-f10`; deleted local branch `manual-right-shift-f10`
Shipped summary: Right Shift is now the primary manual start/Send Chunk key, F10 is the default final end/finalize key, Right Option + Right Shift is no longer a distinct shortcut, hands-free fallback mirrors the same manual controls, and macOS function-key suppression prevents F10 escape text from leaking after WhisCode receives the key.

# Manual Right Shift/F10 Recording Controls

Date: 2026-06-10
Status: active
Branch/worktree: `manual-right-shift-f10` at `.agents/worktrees/manual-right-shift-f10`
Related checkpoint: `.agents/checkpoints/2026-06-10-manual-right-shift-f10-checkpoints.md`

## Objective

Implement the manual control model:

- Right Shift starts recording when idle or transcribing.
- Right Shift sends a chunk while recording, deferring delivery and restarting recording.
- F10 ends and finalizes the current recording batch.

## Scope

- Keep `--hotkey` default as `shift_r`, but change it from toggle semantics to the primary action: start when not recording, Send Chunk when recording.
- Add `--end-hotkey` defaulting to `f10`. This is the only default manual final-stop key.
- Remove Right Option + Right Shift as a distinct Send Chunk shortcut.
- Apply matching manual fallback behavior in hands-free mode: Right Shift mirrors wake/start-or-chunk and F10 mirrors end/finalize.
- Suppress the configured F10 end key on macOS using `pynput`'s `darwin_intercept` path so terminal escape text such as `^[[21~` does not leak into focused apps.
- Update tests and user-facing help/docs/startup text for the new controls.

## Out Of Scope

- Changing voice detection behavior beyond the manual fallback mappings.
- Changing transcription backends, deferred delivery content semantics, or overlay rendering except where labels describe the new keys.
- Supporting the removed Right Option + Right Shift chord as a compatibility shortcut.

## Validation Contract

- VC-001 critical behavior: Right Shift starts a recording from idle/transcribing. Evidence: router/unit tests and manual state-path review.
- VC-002 critical behavior: Right Shift while recording queues a Send Chunk, defers delivery, and restarts recording. Evidence: unit tests covering queued chunk and restarted reservation.
- VC-003 critical behavior: F10 while recording finalizes the batch and flushes deferred chunks. Evidence: unit tests for final job delivery and state transition.
- VC-004 important regression: F10 outside recording is ignored safely with bounded telemetry. Evidence: unit test or static review of idle/transcribing path.
- VC-005 important regression: Right Option + Right Shift is no longer a distinct shortcut. Evidence: router test update removing chord-specific Send Chunk behavior.
- VC-006 important user-flow: Hands-free manual fallback uses the same Right Shift/F10 manual behavior while voice detection remains unchanged. Evidence: targeted tests or code review.
- VC-007 advisory debug: Startup/docs clearly show Right Shift start/chunk and F10 end. Evidence: README/help/message checks.

## Implementation Plan

1. Inspect current CLI parsing, hotkey listener setup, state machine callbacks, deferred delivery, and hands-free fallback handlers.
2. Add `--end-hotkey`, validation, help text, and conflict checks for `--hotkey` versus `--end-hotkey`.
3. Refactor manual hotkey routing so the primary key dispatches start or chunk by current state, and the end key dispatches final end only while recording.
4. Update macOS key suppression so the configured end key is suppressed alongside existing suppressed keys without logging raw key payloads.
5. Remove the Right Option + Right Shift chunk chord from routing/tests/docs.
6. Mirror the same primary/end behavior in hands-free manual fallback paths while leaving wake/silence voice detection behavior unchanged.
7. Update tests and documentation, then run focused and broad verification.
8. Use Validator Workflow after implementation with the validation contract and diff.

## Telemetry / Debuggability

- The behavior change touches user workflows, keyboard routing, and recording state transitions, so diagnostics are applicable.
- Existing telemetry/logging should remain bounded to operation names, recording states, outcomes, and safe key identifiers.
- Add or update tests/static checks for ignored end-key events outside recording so any diagnostic surface remains bounded and non-spammy.
- Do not log raw transcribed content, prompts, provider payloads, credentials, or high-cardinality user data while touching this flow.

## Test Plan

- Update router tests for `shift_r` primary and `f10` end events, including held-key debounce behavior.
- Add CLI tests for default `--hotkey shift_r`, default `--end-hotkey f10`, invalid key rejection, and same-key conflict rejection.
- Add state-flow tests for start, chunk, final end, ignored end, and deferred batch flush where practical.
- Run focused tests: `tests/test_main_cli.py` and any relevant hands-free/deferred delivery tests.
- Run the full test suite if runtime and local dependencies are reasonable.
- Run Validator Workflow with `mission_validator` after implementation.
