# Configurable Hands-Free Commands Checkpoints

## 2026-05-15 Start

- Created branch/worktree `configurable-handsfree-commands` from local `main` at `5227033`.
- Saved the implementation plan for configurable hands-free command enablement.
- Immediate next step: inspect the existing command slot wiring in runtime, enrollment, calibration, tests, and docs, then implement the config helpers and CLI integration.
- Verification: pending.

## 2026-05-15 Implementation

- Implemented `~/.config/whiscode/commands.ini` command allowlist parsing with backward-compatible all-enabled behavior when the config file is absent.
- Added CLI config overrides for runtime (`--hands-free-command-config`), guided enrollment (`--command-config`), and calibration (`--command-config`).
- Updated runtime reference checks, detector loading, guided enrollment, and calibration to use only enabled command slots.
- Added bounded `handsfree.command_config_loaded` telemetry with config existence, enabled command names/counts, and disabled count.
- Updated README documentation with sample config and behavior notes.
- Verification: `PYTHONPATH=. uv run --with pytest python -m pytest` passed with 129 tests.
- Implementation commit: `c212bc9`.
- Checkpoint commit: `428dd47`.
- Immediate next step: merge the task branch back to local `main` and remove the task worktree/branch.

## 2026-05-15 Closeout

- Archived the active plan to `.agents/plans/archive/2026-05-15-configurable-handsfree-commands.md`.
- Closeout verification before merge: `git diff --check` and `PYTHONPATH=. uv run --with pytest python -m pytest` passed.
- Closeout commit: pending.
- Immediate next step: commit closeout bookkeeping, fast-forward local `main`, then clean up the worktree and branch.
