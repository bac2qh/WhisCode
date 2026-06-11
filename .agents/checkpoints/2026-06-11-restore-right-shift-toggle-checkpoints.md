# Restore Right Shift Toggle Controls Checkpoints

Plan: `.agents/plans/archive/2026-06-11-restore-right-shift-toggle.md`
Branch: `restore-right-shift-toggle`
Worktree: `.agents/worktrees/restore-right-shift-toggle`

## 2026-06-11 Initial Checkpoint

Status: active

Done:
- Confirmed main project root is `/Users/xin/Documents/repos/WhisCode`.
- Reviewed project memory index; relevant topics include hands-free keyword detection, external transcription queue, recording status notifications, and telemetry.
- Created local task worktree and branch `restore-right-shift-toggle`.
- Saved the approved plan and validation contract before source edits.

Decisions:
- Implement in the task worktree only, preserving the clean main checkout.
- Treat `--hotkey` as the only manual hotkey public interface.
- Treat Right Option + Right Shift as ignored input, not a Send Chunk request and not a toggle.

Next step:
- Inspect CLI, hotkey routing, worker loop, focused tests, and docs for the current F10/end-hotkey and manual Send Chunk behavior.

Verification:
- Pending.

Implementation commits:
- Pending.

## 2026-06-11 Implementation Checkpoint

Status: implemented and independently validated in task worktree

Done:
- Replaced the manual hotkey event model with a single `HOTKEY_TOGGLE_EVENT`.
- Updated `HotkeyRouter` so the configured `--hotkey` emits a toggle event, while Right Option + Right Shift emits no event when Right Shift is the configured toggle key.
- Removed `--end-hotkey` from argparse and removed runtime validation, F10 routing, and macOS function-key suppression for the old end hotkey.
- Updated manual hotkey behavior so idle/transcribing plus toggle starts recording, recording plus toggle stops/finalizes, and timeout still finalizes active recordings.
- Removed manual hotkey Send Chunk/restart paths while preserving hands-free wake-as-chunk Send Chunk and deferred delivery behavior.
- Updated focused tests in `tests/test_main_cli.py`.
- Updated README, current-state wiki, wiki log, and project memory to describe Right Shift start/stop, removed F10/end-hotkey support, and ignored Right Option + Right Shift.

Decisions:
- Historical `.agents/memory` and `wiki/log.md` entries were kept append-only, with superseding notes added for the short-lived Right Shift/F10 model.
- Current-state docs (`README.md` and `wiki/pages/hands-free-keyword-detection.md`) no longer describe F10 or manual Send Chunk chord support.

Verification:
- `uv run --with pytest python -m pytest tests/test_main_cli.py` passed: 52 tests.
- `uv run --with pytest python -m pytest` passed: 290 tests.
- `git diff --check` passed.
- Static stale-reference review:
  - Code/tests only retain `--end-hotkey` in rejection/help-omission tests.
  - Current-state docs only retain Send Chunk references for hands-free voice wake-as-chunk behavior.
  - Historical log/memory entries retain old references with superseding 2026-06-11 notes.
- Independent validator `019eb4e4-f0b3-7763-8bd2-3ede670dccc8` reported no findings and `APPROVE`.

Validation contract:
- VC-001 critical: passed. Plain Right Shift routes to toggle, and toggle starts/stops by state.
- VC-002 critical: passed. Right Option + Right Shift emits no event and manual Send Chunk actions are gone.
- VC-003 critical: passed. F10 no longer routes as an end key, and `--end-hotkey` is rejected as unknown.
- VC-004 important: passed. Hands-free wake-as-chunk and deferred final flush behavior remain covered and passing.
- VC-005 important: passed. Current-state docs no longer claim F10 or manual Send Chunk chord support.

Immediate next step:
- Commit checkpoint bookkeeping, then close out by merging back to local `main` under the repo mutex if available.

Implementation commits:
- `c94dae7` Restore Right Shift recording toggle.

## 2026-06-11 Closeout Checkpoint

Status: complete and archived on local `main`

Done:
- Fast-forward merged `restore-right-shift-toggle` into local `main` at `21fdbc9`.
- Removed task worktree `.agents/worktrees/restore-right-shift-toggle`.
- Deleted local branch `restore-right-shift-toggle`.
- Added the closeout note to the plan and moved it to `.agents/plans/archive/2026-06-11-restore-right-shift-toggle.md`.

Decisions:
- No merge commit was created because `main` fast-forwarded cleanly.
- No archive index update was needed; this project's visible plan archive is file-based and no separate index file was present.

Verification:
- Closeout bookkeeping occurred while the repo main-branch mutex was held.
- Post-merge verification from the task branch remains the validation record:
  - `uv run --with pytest python -m pytest tests/test_main_cli.py`: 52 passed.
  - `uv run --with pytest python -m pytest`: 290 passed.
  - `git diff --check`: passed.
  - Independent validator: `APPROVE`.

Implementation commits:
- `c94dae7` Restore Right Shift recording toggle.
- `21fdbc9` Record Right Shift toggle validation.

Closeout commit:
- Pending.
