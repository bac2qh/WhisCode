# Repository Hygiene

## 2026-05-14
- `.agents/worktree/`, `.agents/worktrees/`, and `.agents/locks/` are ignored as local runtime/coordination state.
- Durable project state under `.agents/plans`, `.agents/checkpoints`, and `.agents/memory` remains tracked by design.
