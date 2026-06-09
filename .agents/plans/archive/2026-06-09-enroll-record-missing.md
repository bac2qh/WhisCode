## Closeout Note - 2026-06-09

Final status: complete; fast-forward merged to local `main` at `52acc10` (no merge commit).
Related checkpoint: `.agents/checkpoints/2026-06-09-enroll-record-missing-checkpoints.md`.
Implementation commits: `195f807`, `52acc10`.
Verification performed: focused pytest command passed with 80 tests; full pytest suite passed with 283 tests. Direct `python -m compileall whiscode tests` was blocked by pyenv because Python 3.13 was unavailable outside `uv`.
Worktree/branch cleanup result: task worktree `.agents/worktrees/enroll-record-missing` removed and local branch `feature/enroll-record-missing` deleted.
Shipped summary: `whiscode-enroll --record --record-missing` now tops up incomplete wake, end, and enabled command reference sets without overwriting existing WAVs; startup/docs recommend the top-up command.

# Add `whiscode-enroll --record-missing`

Date: 2026-06-09
Status: archived
Related checkpoint: `.agents/checkpoints/2026-06-09-enroll-record-missing-checkpoints.md`

## Objective
Add a guided enrollment mode that records only incomplete hands-free reference sets. The target scroll setup command becomes:

```bash
uv run whiscode-enroll --record --record-missing
```

The command must inspect existing wake/end references and enabled command slots from `commands.ini`; if only `scroll-up` and `scroll-down` are missing, it records only those sets.

## Validation Contract

VC-001 (`critical`, behavior, scrutiny): `whiscode-enroll --record --record-missing` parses successfully. Evidence: focused CLI parse test.

VC-002 (`critical`, negative, scrutiny): `--record-missing` without `--record` exits through argparse with a clear invalid-usage error and does not run manual import. Evidence: focused CLI parse/main test.

VC-003 (`critical`, behavior, scrutiny/user-testing): normal `--record` enrollment keeps existing behavior and records every selected wake, end, and command phrase set rather than skipping complete sets. Evidence: existing tests plus focused regression review.

VC-004 (`critical`, behavior, scrutiny): `--record --record-missing` skips any selected phrase set that already has at least `--sample-count` `.wav` files. Evidence: test with complete wake/end/command folders and recorded call log.

VC-005 (`critical`, data/state, scrutiny): `--record --record-missing` tops up partial folders only to `--sample-count` and never overwrites existing `.wav` files; new filenames use the next unused numbered slot. Evidence: test with sparse/partial existing files and filesystem assertions.

VC-006 (`critical`, behavior, scrutiny): enabled command selection follows existing `commands.ini` semantics: missing config means all known command slots are selected; present config acts as an allowlist for `true` slots only. Evidence: command config/enroll tests covering missing config and disabled slots.

VC-007 (`important`, user-flow, scrutiny): missing-reference startup guidance recommends `uv run whiscode-enroll --record --record-missing`. Evidence: `tests/test_main_cli.py` assertion.

VC-008 (`important`, docs/API, scrutiny): README and hands-free wiki docs describe the scroll-only/top-up workflow and command. Evidence: documentation diff review.

VC-009 (`important`, regression, scrutiny): focused test command passes: `uv run --with pytest python -m pytest tests/test_enroll.py tests/test_main_cli.py tests/test_command_config.py`. Evidence: command exit code.

VC-010 (`advisory`, regression, scrutiny): full test suite passes when environment supports it. Evidence: `uv run --with pytest python -m pytest` exit code or recorded blocker.

## Implementation Plan

1. Inspect `whiscode/enroll.py`, command enablement helpers, startup missing-reference messaging, README/wiki docs, and related tests.
2. Refactor guided enrollment phrase-set selection so wake, end, and enabled command phrase sets are built once.
3. Add `--record-missing` to `whiscode-enroll`, restricted to `--record`.
4. Implement missing-only recording:
   - count existing `.wav` samples for each selected phrase set;
   - skip sets with at least `sample_count`;
   - record only the number needed for incomplete sets;
   - choose the next unused numbered filename to avoid overwriting existing samples;
   - print a concise skipped/recorded summary.
5. Preserve current full `--record` behavior.
6. Update the startup prompt, README, and `wiki/pages/hands-free-keyword-detection.md`.
7. Add/adjust focused tests.
8. Run focused and full validation.

## Telemetry / Debuggability

No telemetry events or structured logs are planned for this change. Enrollment is a local interactive CLI workflow, and the meaningful diagnostic surface is stdout/stderr plus filesystem results. Verification will cover user-visible messages and sample-file state; the implementation should avoid logging raw audio content or any sensitive payloads.

## Scope Notes

- Completeness target is `--sample-count`, defaulting to `3`.
- Missing `commands.ini` keeps existing behavior: all command slots are considered enabled.
- Existing `commands.ini` remains an allowlist: only `true` command slots are checked/recorded.
- No new config value is added.
