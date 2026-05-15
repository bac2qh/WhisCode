# Tab And Arrow Command Slots Checkpoints

## 2026-05-15 Initial
- Done: Created the task worktree `tab-arrow-command-slots` from local `main` at `592c9af`.
- Immediate next step: Add `tab`, `arrow-up`, and `arrow-down` command slots, update key injection, tests, docs, and memory.
- Decisions: Reuse the existing idle-only `COMMAND_SLOTS` pipeline and bounded command telemetry; use exact command names `tab`, `arrow-up`, and `arrow-down`.
- Verification: Not yet run.

## 2026-05-15 Implementation
- Done: Implemented in commit `b356283` (`Add Tab and arrow voice command slots`).
- Immediate next step: Close out by merging the task branch back into local `main`, archive the plan, and remove the task worktree and branch.
- Decisions: Added the slots to `COMMAND_SLOTS` so guided enrollment, manual import choices, startup reference checks, runtime detector loading, calibration, and telemetry use the existing command-slot path. `press_key_command` maps the new slots directly to `Key.tab`, `Key.up`, and `Key.down`.
- Verification:
  - `uv run --with pytest python -m pytest tests/test_injector.py tests/test_enroll.py tests/test_main_cli.py tests/test_calibrate.py tests/test_handsfree.py` passed with 56 tests.
  - `uv run --with pytest python -m pytest` passed with 118 tests.
  - `uv run whiscode --help` passed.
  - `uv run whiscode-enroll --help` passed and listed `tab`, `arrow-up`, and `arrow-down`.
  - `git diff --check` passed.
