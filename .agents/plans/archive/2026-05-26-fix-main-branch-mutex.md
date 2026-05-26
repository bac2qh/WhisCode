> Closeout: implemented
>
> Related checkpoint: `.agents/checkpoints/2026-05-26-fix-main-branch-mutex-checkpoints.md`
> Implementation commits: `babba97`, `e7ac4c7`
> Merge commit: none (fast-forward)
> Verification: `sh -n .agents/scripts/main-branch-lock.sh`; `git diff --check`; `uv run --with pytest pytest` (237 passed); mutex smoke `status` and `run -- /bin/echo hi`
> Worktree and branch cleanup: remove `.agents/worktrees/fix-main-branch-mutex`; delete local branch `fix-main-branch-mutex`
> Summary: ported the main-branch mutex to the Nix-style helper, added status/metadata/retry/root-resolution behavior, safer release, and explicit lock creation failure diagnostics.

# Fix Main Branch Mutex

## Summary
- Replace WhisCode's older main-branch lock helper with the Nix-style helper behavior.
- Fix the observed failure mode where sandbox permission errors during lock creation are treated as anonymous lock contention.
- Preserve the global closeout contract: main-write windows use `.agents/scripts/main-branch-lock.sh run`.

## Key Changes
- Add `run` and `status` modes.
- Add `--owner`, `--timeout-seconds`, and `--retry-seconds`, with environment defaults.
- Resolve the main root correctly when invoked from `.agents/worktrees/<task>`.
- Store lock metadata in `.agents/locks/main-branch.lock/info`.
- Release locks with `rm -f info` plus `rmdir` rather than broad recursive deletion.
- Fail fast when lock directory creation fails and no lock directory exists, because that means permission/sandbox failure rather than real contention.

## Telemetry / Debuggability
- Telemetry not applicable: this is a local shell workflow helper, not app runtime behavior.
- Debuggability applies through clearer lock `status`, holder metadata, stale lock messages, wait messages, and explicit permission/sandbox failure output.

## Test Plan
- Add shell-helper tests in a temporary Git repo for:
  - status when unlocked.
  - successful run acquire/release.
  - invocation from a task worktree resolving the main root lock path.
  - same-host stale PID cleanup.
  - live lock timeout reporting holder metadata.
  - simulated lock-create permission failure exiting quickly instead of waiting as unknown contention.
- Run targeted tests for the mutex helper.
- Smoke the helper locally with `status` and a harmless `run -- /bin/echo hi`.

## Assumptions
- Port the Nix helper behavior rather than minimally patching the old bash helper.
- Use POSIX `sh` to match the Nix helper.
- Do not change product runtime code.
