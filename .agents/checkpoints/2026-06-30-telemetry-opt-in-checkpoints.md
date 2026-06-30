# Make Telemetry Opt-In Checkpoints

## Initial State - 2026-06-30

- Main project root: `/Users/xin/Documents/repos/WhisCode`.
- Task worktree: `/Users/xin/Documents/repos/WhisCode/.agents/worktrees/telemetry-opt-in`.
- Branch: `telemetry-opt-in`.
- No repo-local `AGENTS.md` exists; global user instructions are active.
- Memory index exists at `.agents/memory/MEMORY.md`.
- Telemetry memory currently records the older 2026-05-24 decision that runtime telemetry is enabled by default; this task will supersede that entry.
- Approved saved plan: `.agents/plans/archive/2026-06-30-telemetry-opt-in.md`.
- Validation contract: `VC-001` through `VC-004` in the saved plan.

## Evidence Log

- Implementation diff updates:
  - `whiscode.telemetry.telemetry_from_args` now defaults disabled and enables telemetry only through `default_enabled`, `--telemetry`, or `--telemetry-path`; `--no-telemetry` overrides all enablement paths.
  - `whiscode.main` and `whiscode.enroll` expose `--telemetry`, revise help text, and no longer enable enrollment telemetry just because `--record` is used.
  - README, wiki, and telemetry memory now document opt-in-only app-owned telemetry.
  - CLI tests cover default-disabled runtime/enrollment telemetry, no-file emit behavior, opt-in default path, custom path, and `--no-telemetry` precedence.
- Initial planned command `uv run pytest tests/test_telemetry.py tests/test_main_cli.py tests/test_enroll.py tests/test_calibrate.py` failed before collection because this repo's uv environment does not include a bare `pytest` executable. This matches prior repo checkpoint guidance that tests should be run as `uv run --with pytest python -m pytest`.
- Targeted pytest: `uv run --with pytest python -m pytest tests/test_telemetry.py tests/test_main_cli.py tests/test_enroll.py tests/test_calibrate.py` passed, 103 tests.
- Full pytest: `uv run --with pytest python -m pytest` passed, 303 tests.
- Static check: `git diff --check` passed.
- CLI help smoke: `uv run whiscode --help` passed and shows `--telemetry`, `--telemetry-path`, and `--no-telemetry`.
- CLI help smoke: `uv run whiscode-enroll --help` passed and shows `--telemetry`, `--telemetry-path`, and `--no-telemetry`.
- Validator review: independent validator returned `APPROVE`.
  - `VC-001` passed: default runtime telemetry is disabled and tests assert no default file creation.
  - `VC-002` passed: `--telemetry`, `--telemetry-path`, and `--no-telemetry` precedence is implemented in `whiscode.telemetry.telemetry_from_args` and covered for runtime and enrollment.
  - `VC-003` passed: README and current-state wiki document opt-in diagnostics and no default app-owned telemetry writes.
  - `VC-004` passed: disabled `Telemetry.emit()` remains a no-op and targeted/full pytest passed.
  - Residual risk noted by validator: dated memory/log entries still mention the older default-on decision, but telemetry memory explicitly supersedes it.

## 2026-06-30 Closeout Checkpoint

Status: complete and archived on local `main`; worktree/branch cleanup pending final cleanup command.

Done:
- Fast-forward merged `telemetry-opt-in` into local `main` at `ea63aeb`.
- Added the closeout note to the plan and moved it to `.agents/plans/archive/2026-06-30-telemetry-opt-in.md`.

Decisions:
- No merge commit was created because `main` fast-forwarded cleanly.
- No existing local telemetry log file was deleted, archived, opened, or appended as part of this task.
- Bare `uv run pytest ...` remains unsupported in this repo environment because `pytest` is not part of the base uv environment; the verified command uses `uv run --with pytest python -m pytest`, matching prior repo convention.

Verification:
- Closeout merge and archive bookkeeping occurred while the repo main-branch mutex was held.
- Targeted pytest: `uv run --with pytest python -m pytest tests/test_telemetry.py tests/test_main_cli.py tests/test_enroll.py tests/test_calibrate.py`: 103 passed.
- Full pytest: `uv run --with pytest python -m pytest`: 303 passed.
- Static check: `git diff --check`: passed.
- CLI help: `uv run whiscode --help`: passed and showed telemetry flags.
- CLI help: `uv run whiscode-enroll --help`: passed and showed telemetry flags.
- Independent validator: `APPROVE`.

Implementation commit:
- `ea63aeb` Make local telemetry opt-in.

Closeout commit:
- Pending.
