# Closeout Note - 2026-06-08

Final status: complete.
Related checkpoint: `.agents/checkpoints/2026-06-08-handsfree-tail-extra-buffer-checkpoints.md`.
Implementation commits: `9182b90` (`Add extra hands-free tail trim buffer`) and `31ebc2b` (`Record hands-free tail buffer checkpoint`).
Merge result: fast-forward from `e2a449f` to `31ebc2b`; merge commit hash: none.
Verification performed: `uv run --with pytest python -m pytest tests/test_handsfree.py tests/test_main_cli.py` passed with 59 tests; `git diff --check` passed; Validator Workflow ended `APPROVE`.
Worktree/branch cleanup result: removed task worktree `.agents/worktrees/handsfree-tail-extra-buffer`; deleted local branch `handsfree-tail-extra-buffer`.
Shipped summary: hands-free end phrase stops now trim the inferred/explicit/fallback base tail plus a default `1.0s` extra detection-lag buffer, with telemetry and docs updated.

---

# Add Extra Hands-Free End Trim Buffer

Date: 2026-06-08
Branch/worktree: `handsfree-tail-extra-buffer` / `.agents/worktrees/handsfree-tail-extra-buffer`
Related checkpoint: `.agents/checkpoints/2026-06-08-handsfree-tail-extra-buffer-checkpoints.md`
Status: closed

## Objective

Keep the existing inferred hands-free end-word trim length, add a tunable extra trim buffer on top of it, and apply the total trim only to hands-free `end.detected` stops.

## Scope

- Add CLI option `--hands-free-tail-extra-seconds FLOAT`, default `1.0`.
- Resolve total hands-free end trim as base tail seconds plus the extra tail seconds.
- Reject negative values for `--hands-free-tail-extra-seconds`.
- Update `handsfree.tail_seconds_resolved` telemetry with `base_seconds`, `extra_seconds`, and total `resolved_seconds`, while preserving existing reference/fallback fields.
- Update docs to explain the inferred end-word duration plus extra detection-lag buffer, and that `--hands-free-tail-extra-seconds 0` restores the previous behavior.
- Add or update focused tests in `tests/test_handsfree.py` and `tests/test_main_cli.py`.

## Out Of Scope

- Detector alignment changes.
- Changes to manual hotkey stop trimming.
- Changes to timeout stop trimming.
- Renaming or changing the semantics of existing `--hands-free-tail-seconds`; it remains the base trim override.

## Implementation Plan

1. Inspect existing CLI parsing, hands-free tail resolution, telemetry, and tests.
2. Add config/CLI plumbing for `hands_free_tail_extra_seconds` with a non-negative validator and default `1.0`.
3. Update tail resolution so base tail seconds are computed exactly as today, then add the extra seconds to the returned/resolved trim.
4. Update telemetry payloads to report base, extra, and total resolved seconds.
5. Update hands-free session behavior/tests so only `end.detected` stops use the larger total trim.
6. Update docs for the new option and previous-behavior restoration.
7. Run focused pytest command, `git diff --check`, and Validator Workflow.

## Telemetry / Debuggability

This change touches a user-visible recording workflow and an existing telemetry event. `handsfree.tail_seconds_resolved` must remain privacy-safe and low-cardinality: numeric durations and stable source/fallback fields only, no audio content, transcripts, prompts, personal data, or provider payloads. Verification must include static test assertions for the emitted `base_seconds`, `extra_seconds`, and total `resolved_seconds` fields.

## Validation Contract

- VC-001 (`critical`, behavior): CLI parsing exposes `--hands-free-tail-extra-seconds`, defaults it to `1.0`, accepts custom non-negative floats, and rejects negative values. Required evidence: focused CLI parser tests and/or command output. Validator mode: scrutiny.
- VC-002 (`critical`, behavior): Existing base hands-free tail resolution is preserved for inferred, explicit, and fallback sources before adding the extra buffer. Required evidence: tail resolution tests covering all three base sources. Validator mode: scrutiny.
- VC-003 (`critical`, behavior): The total resolved tail used for hands-free `end.detected` stops equals `base_seconds + extra_seconds`. Required evidence: unit/session test demonstrating a larger end trim than the base alone. Validator mode: scrutiny.
- VC-004 (`critical`, regression): Manual hotkey stops remain untrimmed by pending hands-free tail audio. Required evidence: regression test or existing test result showing manual stop includes pending tail. Validator mode: scrutiny.
- VC-005 (`critical`, regression): Timeout stops remain untrimmed by pending hands-free tail audio. Required evidence: regression test or existing test result showing timeout includes pending tail. Validator mode: scrutiny.
- VC-006 (`important`, telemetry): `handsfree.tail_seconds_resolved` includes `base_seconds`, `extra_seconds`, and total `resolved_seconds`, with existing reference/fallback fields unchanged. Required evidence: telemetry assertions in tests or static review plus test coverage. Validator mode: scrutiny.
- VC-007 (`important`, docs/API): Documentation describes the extra detection-lag buffer and states that `--hands-free-tail-extra-seconds 0` restores previous behavior. Required evidence: docs diff review. Validator mode: scrutiny.

## Verification Plan

- `uv run --with pytest python -m pytest tests/test_handsfree.py tests/test_main_cli.py`
- `git diff --check`
- Validator Workflow using `mission_validator` with the validation contract above.
