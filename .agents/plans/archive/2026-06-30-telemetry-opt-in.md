# Make Telemetry Opt-In

Closeout note, 2026-06-30:
- Final status: complete.
- Related checkpoint: `.agents/checkpoints/2026-06-30-telemetry-opt-in-checkpoints.md`.
- Implementation commit: `ea63aeb` Make local telemetry opt-in.
- Merge result: fast-forwarded local `main` to `ea63aeb`; no merge commit.
- Verification performed: targeted `uv run --with pytest python -m pytest tests/test_telemetry.py tests/test_main_cli.py tests/test_enroll.py tests/test_calibrate.py` passed with 103 tests; full `uv run --with pytest python -m pytest` passed with 303 tests; `git diff --check` passed; `uv run whiscode --help` and `uv run whiscode-enroll --help` passed; independent validator `019f16af-b379-71c2-a656-abd4cd704839` approved all validation contract assertions.
- Worktree/branch cleanup: removed `.agents/worktrees/telemetry-opt-in`; deleted local branch `telemetry-opt-in`.
- Shipped summary: made WhisCode runtime and guided-enrollment telemetry opt-in only through `--telemetry` or `--telemetry-path`, kept `--no-telemetry` as the overriding disable flag, and updated tests, README, wiki, and durable telemetry memory.

Date: 2026-06-30
Branch: `telemetry-opt-in`
Worktree: `.agents/worktrees/telemetry-opt-in`
Status: archived


## Objective

Change WhisCode so it performs no app-owned telemetry writes by default across runtime and enrollment commands. Keep local JSONL diagnostics available only when explicitly requested, and do not automatically touch the existing local telemetry log.

## Design / Implementation Strategy

- Add an explicit `--telemetry` CLI flag to both `whiscode` and `whiscode-enroll`.
- Update telemetry enablement rules for both commands:
  - default: disabled
  - `--telemetry`: enabled at the default path
  - `--telemetry-path PATH`: enabled and writes to `PATH`
  - `--no-telemetry`: wins over both `--telemetry` and `--telemetry-path`
- Preserve the `Telemetry` writer implementation so opted-in local JSONL diagnostics continue to work.
- Change runtime and enrollment wiring so no `~/Library/Logs/WhisCode/events.jsonl` file is created or appended unless opted in.
- Do not change overlay pipe traffic, OS/framework cache behavior, or unrelated diagnostics.
- Update README telemetry docs and CLI option tables to state that telemetry is disabled by default and calibration can only use recent runtime telemetry if the user opted in.
- Update durable telemetry memory to supersede the previous enabled-by-default decision.

## Test Strategy

- Update CLI tests to assert:
  - default runtime telemetry is disabled
  - `--telemetry` enables telemetry
  - `--telemetry-path PATH` enables telemetry and sets the custom path
  - `--no-telemetry` overrides `--telemetry` and `--telemetry-path`
  - enrollment follows the same default-off/opt-in behavior
- Keep existing `Telemetry` unit tests proving enabled writes JSONL and disabled creates no file.
- Run targeted tests: `uv run pytest tests/test_telemetry.py tests/test_main_cli.py tests/test_enroll.py tests/test_calibrate.py`.
- Run full suite if targeted tests pass: `uv run pytest`.

## Telemetry / Debuggability

- Debuggability remains available through explicit local opt-in only.
- No raw audio, transcripts, prompts, or provider payloads should be written by default.
- CrispASR raw response debug logging remains gated behind enabled telemetry, so it is also off by default.
- No production telemetry or external reporting is introduced.

## Validation Contract

- `VC-001` | P0 | CLI/runtime | Required truth: a default `whiscode` invocation creates a disabled telemetry object and does not create or append the default telemetry path. Required evidence: updated unit tests and passing targeted/full pytest. Validator mode: scrutiny. Blocker/waiver path: fix failures, rebut with evidence, or user waiver.
- `VC-002` | P0 | CLI/runtime | Required truth: `--telemetry`, `--telemetry-path`, and `--no-telemetry` follow the precedence rules above. Required evidence: updated CLI tests and passing targeted/full pytest. Validator mode: scrutiny. Blocker/waiver path: fix failures, rebut with evidence, or user waiver.
- `VC-003` | P1 | docs/current-state | Required truth: README no longer claims telemetry is written by default and documents opt-in diagnostics accurately. Required evidence: doc diff review. Validator mode: scrutiny. Blocker/waiver path: fix documentation, rebut with evidence, or user waiver.
- `VC-004` | P1 | regression | Required truth: existing telemetry emit call sites remain safe no-ops when disabled. Required evidence: targeted and full pytest results. Validator mode: scrutiny. Blocker/waiver path: fix failures, rebut with evidence, or user waiver.

## Assumptions

- Keep diagnostics available, but disabled by default.
- Do not delete or archive the existing `~/Library/Logs/WhisCode/events.jsonl` during implementation.
- Local main closeout is required after implementation, validation, and commit.

