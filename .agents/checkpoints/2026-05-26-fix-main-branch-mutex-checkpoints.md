# Fix Main Branch Mutex Checkpoints

## 2026-05-26 Start

### Done
- Created task worktree `fix-main-branch-mutex` at `.agents/worktrees/fix-main-branch-mutex`.
- Saved implementation plan and matching checkpoint before source edits.
- Confirmed main was clean before branching.

### Immediate Next Step
- Port the Nix-style lock helper, add shell tests, verify behavior, then commit and close out.

### Decisions And Reasoning
- The observed mutex problem was lock acquisition misdiagnosing sandbox/permission failure as anonymous contention.
- The implementation will use the Nix helper design plus an explicit lock-create failure check.

### Verification
- Not run yet.

## 2026-05-26 Implementation Milestone

### Done
- Replaced `.agents/scripts/main-branch-lock.sh` with a Nix-style POSIX `sh` helper.
- Added `status`, `--retry-seconds`, environment defaults, task-worktree main-root resolution, richer lock holder metadata, and safer lock release.
- Added explicit diagnostics for lock parent/directory creation failure so sandbox or permission failures do not spin as unknown lock contention.
- Added pytest coverage for status, acquire/release, task-worktree root resolution, stale lock cleanup, live lock timeout metadata, and permission/create failure behavior.
- Updated repository hygiene memory.

### Immediate Next Step
- Commit the implementation, then close out through the updated mutex helper.

### Decisions And Reasoning
- Used the Nix helper as the baseline because it has the workflow behavior WhisCode expected during closeout.
- Added one WhisCode-specific improvement over Nix: distinguish lock-create failures from real lock contention when no lock directory exists.
- Product telemetry is not applicable; debug output is shell command output and lock metadata.

### Verification
- `uv run --with pytest pytest tests/test_main_branch_lock.py` passed: 7 tests.
- `.agents/scripts/main-branch-lock.sh status` and `.agents/scripts/main-branch-lock.sh run --owner smoke --timeout-seconds 5 --retry-seconds 1 -- /bin/echo hi` passed with escalation against the real WhisCode lock path.
- `sh -n .agents/scripts/main-branch-lock.sh` passed.
- `git diff --check` passed.
- `uv run --with pytest pytest` passed: 237 tests.
