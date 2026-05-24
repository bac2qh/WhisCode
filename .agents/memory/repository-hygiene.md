# Repository Hygiene

## 2026-05-14
- `.agents/worktree/`, `.agents/worktrees/`, and `.agents/locks/` are ignored as local runtime/coordination state.
- Durable project state under `.agents/plans`, `.agents/checkpoints`, and `.agents/memory` remains tracked by design.

## 2026-05-24
- WhisCode added `.agents/scripts/main-branch-lock.sh` as the standard local `main` closeout mutex helper. The helper records lock metadata under ignored `.agents/locks/`, waits with a default 3600-second timeout, and removes stale locks only when the recorded PID is dead on the same host.
