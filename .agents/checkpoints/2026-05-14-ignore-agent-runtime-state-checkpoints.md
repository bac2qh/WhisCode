# Ignore Agent Runtime State Checkpoints

## 2026-05-14
- Created task branch/worktree `ignore-agent-runtime-state` from local `main`.
- Saved plan before editing.
- Added scoped `.gitignore` entries for `.agents/worktree/`, `.agents/worktrees/`, and `.agents/locks/`.
- Verified the new patterns ignore runtime locations but do not ignore tracked durable `.agents/plans`, `.agents/checkpoints`, or `.agents/memory` files.
- Updated project memory with the repository hygiene decision.
- Immediate next step: commit and merge back into local `main`.
