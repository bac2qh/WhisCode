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
- Immediate next step: commit the implementation and checkpoint/memory updates.
