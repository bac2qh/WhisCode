# Fix Overlay Process Table Decode

## Closeout Note
- Final status: completed and merged into local `main` on 2026-06-06.
- Related checkpoint: `.agents/checkpoints/2026-06-06-fix-overlay-ps-decode-checkpoints.md`
- Implementation commit: `a532d71` (`Harden overlay process table decoding`).
- Checkpoint/bookkeeping commit: `4ac4419` (`Record overlay decode checkpoint`).
- Merge result: fast-forward merge into local `main` from `5e8ede2` to `4ac4419`; no merge commit.
- Verification performed: `uv run --with pytest python -m pytest tests/test_recording_overlay.py` (`20 passed`), `git diff --check`, sanitized live `overlay_helper_processes()` smoke check with helper count/PID/PPID output only, and independent `mission_validator` approval with `VC-001` through `VC-005` passed.
- Worktree/branch cleanup: removed `.agents/worktrees/fix-overlay-ps-decode` and deleted local branch `task/fix-overlay-ps-decode` under the main-branch mutex.
- Shipped summary: overlay helper discovery now reads live `ps` output as bytes and decodes with UTF-8 replacement semantics, so malformed non-helper process command bytes cannot crash orphan cleanup before hands-free overlay startup. Helper detection and `--cleanup-orphans` filtering remain unchanged.

## Status
- Created: 2026-06-06
- Branch: `task/fix-overlay-ps-decode`
- Worktree: `.agents/worktrees/fix-overlay-ps-decode`
- Related checkpoint: `.agents/checkpoints/2026-06-06-fix-overlay-ps-decode-checkpoints.md`

## Objective
Prevent hands-free overlay startup from crashing when the system `ps` output contains malformed non-UTF-8 command bytes, while preserving overlay helper discovery and orphan cleanup behavior.

## User Intent / Prior Investigation
- Roll back only the uncommitted partial work in `.agents/worktrees/fix-overlay-ps-decode`; leave pushed `main` commits intact.
- Investigation found this was not introduced by the `达乐通` hotword change.
- The crash comes from overlay orphan cleanup reading `ps -axo pid=,ppid=,command=` with strict UTF-8 decoding.
- A prior sanitized probe found one malformed non-helper process-table line: `INVALID_LINE_COUNT=1`, `whiscode_helper=False`.

## Validation Contract
- `VC-001` critical, behavior/negative, scrutiny and user-testing: malformed non-helper `ps` command bytes cannot crash hands-free overlay startup. Evidence: a regression test that feeds invalid process-table bytes through `overlay_helper_processes()` and a live sanitized smoke check when practical.
- `VC-002` important, behavior/regression, scrutiny: valid overlay helper process lines are still detected. Evidence: existing/focused tests covering helper parsing and the new malformed-bytes regression preserving a valid helper.
- `VC-003` important, behavior/regression, scrutiny: cleanup-only commands are still ignored. Evidence: focused tests continue to assert `--cleanup-orphans` is excluded from helper discovery.
- `VC-004` important, regression, scrutiny: the focused recording overlay test suite passes. Evidence: `uv run --with pytest python -m pytest tests/test_recording_overlay.py`.
- `VC-005` advisory, privacy/security/user-flow, user-testing: a live sanitized process-table smoke check completes without printing command lines. Evidence: smoke command prints only bounded helper metadata, such as helper count and PID/PPID pairs.

## Implementation Plan
1. Remove the stale uncommitted task worktree and branch, then create a fresh task worktree from clean local `main`.
2. Patch `whiscode/recording_overlay.py` so live `ps` output is decoded with UTF-8 replacement semantics instead of strict decoding.
3. Add a focused regression test in `tests/test_recording_overlay.py` simulating invalid process-table bytes while preserving valid helper detection and cleanup-command filtering.
4. Run the focused pytest suite, `git diff --check`, and a sanitized live smoke check of `overlay_helper_processes()`.
5. Send the implementation to `mission_validator` with this contract, diff, and command evidence.

## Telemetry / Debuggability
No telemetry schema change is planned. This is a defensive decode fix before helper cleanup classification, and existing bounded telemetry remains sufficient:
- `recording_overlay.orphan_cleanup` still records found/terminated/failed counts.
- `recording_overlay.disabled` still records bounded helper launch/pipe/exit failures.

The new regression test covers the ambiguous failure mode directly. The live smoke check must not print command lines or raw process-table content.
