# Manual Right Shift/F10 Recording Controls Checkpoints

Plan: `.agents/plans/2026-06-10-manual-right-shift-f10.md`
Branch/worktree: `manual-right-shift-f10` at `.agents/worktrees/manual-right-shift-f10`
Status: implementation validated; closeout pending

## 2026-06-10 Initial Scope

- User supplied an approved implementation plan for changing manual recording controls to Right Shift start/chunk and F10 final end.
- Created task worktree from local `main` before source edits.
- Validation contract is recorded in the plan and is the source of truth for implementation verification.
- Immediate next step: inspect CLI/hotkey/hands-free/deferred delivery code paths and update implementation/tests/docs.

## Decisions

- Use existing repository patterns for saved plan/checkpoint state.
- Treat `shift_r` as the primary manual action and `f10` as the default final end key.
- Do not preserve Right Option + Right Shift as a hidden compatibility shortcut.

## Verification Log

- `uv run python -m py_compile whiscode/main.py tests/test_main_cli.py` passed.
- `uv run --with pytest python -m pytest tests/test_main_cli.py` passed: 56 tests.
- `uv run --with pytest python -m pytest tests/test_handsfree.py tests/test_transcription_queue.py` passed: 33 tests.
- `uv run --with pytest python -m pytest` passed: 294 tests.
- `git diff --check` passed.
- Static stale-reference search for `HOTKEY_TOGGLE_EVENT`, `HOTKEY_SEND_CHUNK_EVENT`, `HotkeyChordRouter`, `Toggle key`, `start/stop control`, `manual stop`, and `instead of Right Shift` returned no matches after cleanup.
- Validator Workflow: `mission_validator` independently ran focused tests, full suite, and `git diff --check`, classified VC-001 through VC-007 as passed, and returned `APPROVE` with no findings.

## Commits

- `74bf2b6` - Implement Right Shift and F10 manual controls.

## Implementation Summary

- Replaced toggle/chord routing with primary/end hotkey routing in `whiscode/main.py`.
- Added `--end-hotkey` defaulting to `f10`, plus invalid-key and same-key conflict rejection.
- Right Shift now starts recording from idle/transcribing and sends a chunk while recording; F10 finalizes recording batches and flushes deferred chunks.
- Hands-free manual fallback now mirrors the same primary/end behavior while voice wake/end/wake-as-chunk paths remain unchanged.
- Added macOS `darwin_intercept` suppression for function-key end hotkeys so F10 does not leak terminal escape text after listener dispatch.
- Updated tests, README, wiki, and memory for the new model.

## Validator Outcome

- Verdict: APPROVE.
- Findings: none.
- Validation assertions: VC-001 passed, VC-002 passed, VC-003 passed, VC-004 passed, VC-005 passed, VC-006 passed, VC-007 passed.
