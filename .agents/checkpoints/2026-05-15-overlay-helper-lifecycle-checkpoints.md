# Overlay Helper Lifecycle Checkpoints

## 2026-05-15 Initial
- Done: Created the task worktree `overlay-helper-lifecycle` from local `main` at `228d833`.
- Done: Confirmed two orphan helper processes were running and killed them: PIDs `73059` and `2713`.
- Immediate next step: Patch helper EOF handling and client stop cleanup.
- Decisions: Treat stdin EOF as helper shutdown; do not change overlay layout or appearance.
- Verification: Not yet run.
