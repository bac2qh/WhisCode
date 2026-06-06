# Closeout Note

- Final status: complete.
- Related checkpoint: .agents/checkpoints/2026-06-06-auto-trim-handsfree-tail-checkpoints.md.
- Implementation commits: 6624420 (implementation, tests, docs, memory, plan/checkpoint), de109f4 (checkpoint bookkeeping).
- Merge result: fast-forward local main to de109f4; no merge commit.
- Verification performed: git diff --check passed; uv run --with pytest pytest tests/test_handsfree.py tests/test_main_cli.py passed with 56 tests; mission_validator 019e9b5c-6240-7b53-ad0f-33c500906a38 approved all validation assertions and ran an ad hoc resolver/session probe.
- Worktree/branch cleanup: removed task worktree .agents/worktrees/auto-trim-handsfree-tail; deleted local branch feature/auto-trim-handsfree-tail.
- Shipped summary: omitted --hands-free-tail-seconds now infers end-tail trim from enrolled end reference WAV active spans, preserves explicit overrides, falls back to 1.0s when needed, and emits bounded setup telemetry.

# Auto-Trim Hands-Free End Phrase Tail

## Status
Active implementation plan. Created 2026-06-06 in task worktree `feature/auto-trim-handsfree-tail`.

## Objective
Use the meaningful active length inside enrolled hands-free end-phrase WAV references as the default tail trim length for end-phrase stops. Keep the existing explicit `--hands-free-tail-seconds FLOAT` override and keep manual/timeout stops preserving the full buffered recording.

## Scope
- Update `whiscode/main.py` CLI parsing/help and hands-free session construction.
- Add active-span inference helpers in the hands-free runtime module or another local module following existing patterns.
- Update README option docs.
- Add or update focused unit tests in `tests/test_handsfree.py` and `tests/test_main_cli.py`.
- Update durable memory only if implementation creates useful future context.

## Out Of Scope
- No change to hotkey behavior, command detection, enrollment format, detector thresholds, transcription queue behavior, or per-detection dynamic trimming.
- No raw audio, transcript, prompt, phrase text, or provider payload logging.
- No remote push.

## Implementation Approach
1. Make `--hands-free-tail-seconds` optional in parsing so omission can be distinguished from an explicit override.
2. Add a helper that reads end reference WAVs and computes active spans from first to last sample whose absolute normalized level is at least `hands_free_active_level`.
3. Resolve the session tail length as:
   - explicit CLI value when supplied,
   - median valid active span from end references when available,
   - `DEFAULT_TAIL_SECONDS` fallback otherwise.
4. Emit bounded telemetry for tail resolution with source (`explicit`, `inferred`, `fallback`), resolved seconds, valid/reference counts, and no raw audio.
5. Pass the resolved seconds to `HandsFreeSession`.
6. Update docs and tests.

## Telemetry / Debuggability
This change affects a hands-free workflow and ambiguous failures can look like clipped dictation, excess end-phrase audio in transcripts, or unexpected default behavior. Add a stable bounded telemetry event for tail resolution with:
- Source: `explicit`, `inferred`, or `fallback`.
- Resolved seconds rounded/bounded.
- Reference count and valid active-span count.
- Fallback reason when applicable, bounded to a small enum.

Telemetry must not include raw audio, paths, phrase text, transcripts, or per-sample details. Static test verification is sufficient because the signal is emitted at setup time, not in a high-frequency live capture loop.

## Validation Contract
- VC-001 (`critical`, behavior): When `--hands-free-tail-seconds` is omitted and readable end references contain active samples, runtime resolves the hands-free tail trim length to the median active span across valid end references. Evidence: unit test with multiple synthetic padded WAVs and direct helper/runtime assertion.
- VC-002 (`critical`, behavior): An explicit `--hands-free-tail-seconds FLOAT` value wins exactly over any reference-derived value. Evidence: CLI/runtime unit test asserting explicit source and value.
- VC-003 (`critical`, negative): If references are unreadable, malformed, missing, or contain no samples meeting `hands_free_active_level`, runtime falls back to `DEFAULT_TAIL_SECONDS` without crashing. Evidence: unit test covering invalid/no-active references and focused test run.
- VC-004 (`important`, regression): Existing stop behavior remains split: end-phrase stops exclude pending tail, while manual/Right Shift and timeout stops include pending recording audio. Evidence: existing or updated hands-free event tests continue to pass.
- VC-005 (`important`, docs/API): Public CLI flag name remains `--hands-free-tail-seconds FLOAT`, but help/docs describe auto-inference with `1.0s` fallback. Evidence: CLI help or parser tests and README diff.
- VC-006 (`important`, privacy/security telemetry): Tail-resolution telemetry is bounded and does not include raw audio, transcript text, phrase text, full paths, or sample data. Evidence: unit test or static review of telemetry payload keys.
- VC-007 (`advisory`, regression): Focused suites `tests/test_handsfree.py` and `tests/test_main_cli.py` pass. Evidence: command output.

## Verification Plan
- Run `pytest tests/test_handsfree.py tests/test_main_cli.py`.
- If test runner/dependency setup differs, use the repo’s configured equivalent from `pyproject.toml` and record the exact command/outcome.
- Perform static review of telemetry payload keys and README option row.

