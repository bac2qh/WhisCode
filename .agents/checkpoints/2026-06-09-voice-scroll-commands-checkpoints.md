# Voice Scroll Commands Checkpoints

## 2026-06-09 Initial Checkpoint

Status: implementation starting in task worktree `.agents/worktrees/voice-scroll-commands` on branch `feature/voice-scroll-commands`.

Objective: add default-on hands-free `scroll-up` and `scroll-down` command slots that inject native macOS Quartz pixel scroll-wheel events, with docs, tests, and bounded telemetry.

Validation contract: recorded in `.agents/plans/2026-06-09-voice-scroll-commands.md`.

Current state:
- Main project root confirmed as `/Users/xin/Documents/repos/WhisCode`.
- Source checkout was clean on `main` before creating the task worktree.
- Existing unrelated worktree `feature/env-llama-paths` was left untouched.
- Project memory index was present and read before implementation.

Immediate next step: inspect the existing command-slot pipeline, injector, calibration/enrollment code, docs, and focused tests before editing source files.

Decisions:
- Use the approved plan as the source of user intent.
- Implement in the main thread, with Validator Workflow validation after local verification when practical.

## 2026-06-09 Implementation Checkpoint

Status: implementation and local validation completed in task worktree `.agents/worktrees/voice-scroll-commands`.

Completed work:
- Added `scroll-up` and `scroll-down` to `COMMAND_SLOTS`, so missing `commands.ini` defaults them on and the existing config, enrollment, reference-check, detector, and calibration paths see them with the other slots.
- Implemented scroll command injection in `whiscode/injector.py` using lazy-loaded Quartz pixel scroll-wheel events. `scroll-up` posts a positive half-display-height vertical wheel delta for older terminal output; `scroll-down` posts the inverse for newer output.
- Kept existing key-command mappings unchanged and returned action metadata from `press_key_command` so runtime can distinguish key versus scroll injection.
- Added bounded `scroll_command.injected` and `scroll_command.failed` telemetry with command name, older/newer direction, pixel amount, outcome, and error type on failure. No transcript, spoken phrase, raw audio, prompt, provider payload, app/window name, or user content is emitted.
- Updated README, wiki current-state docs, wiki log, hands-free memory, telemetry memory, and memory log.

Validation evidence:
- Focused suite passed: `uv run --with pytest python -m pytest tests/test_command_config.py tests/test_injector.py tests/test_enroll.py tests/test_main_cli.py tests/test_calibrate.py tests/test_handsfree.py` -> 112 passed.
- Full suite passed after source/docs/memory updates: `uv run --with pytest python -m pytest` -> 278 passed.
- `.venv/bin/python -m pytest ...` could not run initially because `.venv/bin/python` did not exist in the fresh task worktree. `uv run` created the local `.venv`; `pytest` is not a project dependency, so validation used `uv run --with pytest`.

Validation contract mapping:
- `VC-001` passed: config, enrollment/import, reference checks, and calibration tests cover the new slots.
- `VC-002` passed: existing key-command injector test still asserts the same physical key taps and modifier order.
- `VC-003` passed by unit coverage: mocked Quartz injector tests assert `scroll-up` uses `+half_height` and `scroll-down` uses `-half_height`. Live UI smoke was not run because it would post native scroll input into the operator's active frontmost app.
- `VC-004` passed: existing hands-free tests still pass, and command detection remains in the idle branch of `HandsFreeSession.feed`.
- `VC-005` passed: scroll telemetry tests assert bounded success/failure payloads, and static review found no transcript/audio/prompt/provider/user-content logging.
- `VC-006` passed: README and `wiki/pages/hands-free-keyword-detection.md` describe enrollment/import, config, semantics, calibration, and telemetry.

Deviation:
- `mission_validator` was not spawned because the available subagent tool is restricted to explicit user delegation requests. Validation was performed in the main thread against the saved validation contract.

Immediate next step: commit the implementation branch, then perform local-main closeout/archival under the repo mutex if available.
