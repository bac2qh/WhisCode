# Overlay Helper Lifecycle Checkpoints

## 2026-05-15 Initial
- Done: Created the task worktree `overlay-helper-lifecycle` from local `main` at `228d833`.
- Done: Confirmed two orphan helper processes were running and killed them: PIDs `73059` and `2713`.
- Immediate next step: Patch helper EOF handling and client stop cleanup.
- Decisions: Treat stdin EOF as helper shutdown; do not change overlay layout or appearance.
- Verification: Not yet run.

## 2026-05-15 Implementation
- Done: Implemented in commit `3db3760` (`Fix orphan recording overlay helper`).
- Immediate next step: Close out by merging the task branch back into local `main`, archive the plan, and remove the task worktree and branch.
- Decisions: `_read_helper_commands` now schedules a `stop` command after stdin EOF, including after ignored malformed JSON. `RecordingOverlayClient.stop()` now waits briefly after `terminate()` and force-kills if the helper does not exit.
- Verification:
  - `uv run --with pytest python -m pytest tests/test_recording_overlay.py` passed with 9 tests.
  - `uv run --with pytest python -m pytest` passed with 121 tests.
  - `uv run whiscode --help` passed.
  - `uv run whiscode-enroll --help` passed.
  - `git diff --check` passed.
