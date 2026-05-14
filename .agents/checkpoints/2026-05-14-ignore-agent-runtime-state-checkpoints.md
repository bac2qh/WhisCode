# Ignore Agent Runtime State Checkpoints

## 2026-05-14
- Created task branch/worktree `ignore-agent-runtime-state` from local `main`.
- Saved plan before editing.
- Added scoped `.gitignore` entries for `.agents/worktree/`, `.agents/worktrees/`, and `.agents/locks/`.
- Verified the new patterns ignore runtime locations but do not ignore tracked durable `.agents/plans`, `.agents/checkpoints`, or `.agents/memory` files.
- Updated project memory with the repository hygiene decision.
- Implemented in commit `f23fd6f`.
- Fast-forward merged into local `main` at `f23fd6f`; no merge commit was created.
- Archived the plan to `.agents/plans/archive/2026-05-14-ignore-agent-runtime-state.md`.
- Removed task worktree `.agents/worktrees/ignore-agent-runtime-state` and deleted local branch `ignore-agent-runtime-state`.
- Immediate next step: none for this plan.
