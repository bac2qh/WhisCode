# Wake Phrase Send Chunk

## Closeout
- Final status: implemented, validated, merged to local `main`, and archived.
- Related checkpoint: `.agents/checkpoints/2026-06-08-wake-phrase-send-chunk-checkpoints.md`.
- Implementation commits:
  - `6cc3369` (`Reuse wake phrase for hands-free send chunk`)
  - `9e75277` (`Record wake phrase send chunk validation`)
- Merge commit: none; local `main` was fast-forwarded from `b3bf370` to `9e75277`.
- Verification performed:
  - `uv run --with pytest pytest tests/test_main_cli.py tests/test_handsfree.py tests/test_enroll.py tests/test_transcription_queue.py tests/test_injector.py tests/test_telemetry.py` -> 102 passed.
  - `uv run --with pytest pytest` -> 268 passed.
  - `git diff --check` -> clean.
  - Removed API/doc `rg` checks for retired chunk flags, enrollment commands, and `wake/chunk` -> no runtime/current-doc matches.
  - `mission_validator` verdict: `APPROVE`.
- Worktree/branch cleanup result: removed `.agents/worktrees/wake-phrase-send-chunk`; deleted local branch `task/2026-06-08-wake-phrase-send-chunk`.
- Shipped summary: Hands-free Send Chunk now reuses the wake phrase while recording, trims the chunk tail from wake references plus the configured extra buffer, removes the separate chunk CLI/enrollment/docs surface, and preserves manual Send Chunk plus end/manual/timeout stop behavior.

## Status
Closed and archived.


## Workflow
- Use Validator Workflow with Goal Mode active.
- Implement in the main thread.
- Use `mission_validator` for independent validation before closeout.
- Task branch/worktree: `task/2026-06-08-wake-phrase-send-chunk` at `.agents/worktrees/wake-phrase-send-chunk`.

## Summary
Replace the separate hands-free Send Chunk phrase with reuse of the wake/start phrase while recording. Idle wake behavior should still start recording; the same confirmed wake phrase during recording should queue the current chunk with a blank-line suffix and immediately restart recording.

## Key Changes
- Public CLI/docs:
  - Remove `--hands-free-chunk`, `--hands-free-chunk-dir`, `whiscode-enroll chunk ...`, `--include-chunk`, `--chunk-dir`, and guidance for `~/.config/whiscode/wake/chunk`.
  - Do not keep hidden compatibility aliases for the removed chunk CLI/enrollment flags.
- Runtime behavior:
  - When hands-free is enabled, create the recording-time `chunk_detector` from `args.hands_free_wake_dir` using `args.hands_free_threshold`.
  - Keep idle wake behavior unchanged.
  - Use wake confirmations for recording-time Send Chunk detection through a new `chunk_confirmations` session field defaulting to wake confirmations.
- Tail trim:
  - Resolve Send Chunk tail from wake references plus `--hands-free-tail-extra-seconds`.
  - Keep end-tail behavior and timeout/manual-stop behavior unchanged.
- Existing Send Chunk behavior:
  - Preserve manual Right Option + Right Shift Send Chunk.
  - Preserve queuing with `"\n\n"` and immediate recording restart.
- Existing user files:
  - Ignore existing user chunk sample folders.
  - Do not delete or modify user files under `~/.config/whiscode/wake/chunk`.

## Telemetry / Debuggability
- Preserve bounded event names such as `handsfree.chunk_detected`, `handsfree.chunk_tail_seconds_resolved`, and `send_chunk.*`.
- Update source/threshold semantics so events reflect wake-as-chunk behavior.
- Continue excluding full paths, raw audio, transcripts, prompts, hotword text, typed text, secrets, credentials, and provider payloads from telemetry.
- Verification must include static review or tests for changed telemetry payloads.

## Validation Contract
- `VC-001` critical behavior/user-flow: idle + confirmed wake phrase starts hands-free recording. Evidence: focused `HandsFreeSession` test and unchanged wake-start path review. Validator mode: scrutiny.
- `VC-002` critical behavior/user-flow: recording + confirmed wake phrase emits `chunk.detected`, queues audio with `\n\n`, and immediately restarts recording. Evidence: unit tests plus handler review. Validator mode: scrutiny.
- `VC-003` critical regression: manual Right Option + Right Shift Send Chunk remains unchanged. Evidence: existing hotkey/router and queue tests. Validator mode: scrutiny.
- `VC-004` critical regression: end phrase stop, manual stop, and timeout keep their existing trim/include-pending behavior. Evidence: focused hands-free tests. Validator mode: scrutiny.
- `VC-005` important data/state: Send Chunk tail is inferred from wake references plus tail extra, not end references and not a chunk directory. Evidence: tail-resolution tests. Validator mode: scrutiny.
- `VC-006` important negative/docs/API: no separate chunk enrollment/config/docs remain. Evidence: tests and `rg` for removed flags/paths. Validator mode: scrutiny.
- `VC-007` important telemetry/privacy: new or changed telemetry remains bounded and path/content-free. Evidence: telemetry payload tests/static review. Validator mode: scrutiny.
- `VC-008` advisory compatibility: existing user chunk sample folders are ignored but not deleted. Evidence: code review and no destructive commands. Validator mode: scrutiny.

## Test Plan
- Update focused tests in `tests/test_handsfree.py`, `tests/test_main_cli.py`, and `tests/test_enroll.py` for wake-as-chunk behavior and removed chunk enrollment flags.
- Run targeted suite:

```bash
uv run --with pytest pytest tests/test_main_cli.py tests/test_handsfree.py tests/test_enroll.py tests/test_transcription_queue.py tests/test_injector.py tests/test_telemetry.py
```

- Run full suite:

```bash
uv run --with pytest pytest
```

- Send implementation summary, diff, validation contract, and command results to `mission_validator`; repair any blocking findings before closeout.

## Assumptions
- No backward-compatible hidden aliases for removed chunk CLI/enrollment flags.
- Do not delete any existing user files under `~/.config/whiscode/wake/chunk`; WhisCode simply stops referencing them.
- No HTML report is planned; saved plan, checkpoint, memory/wiki updates, commit messages, and validator report are sufficient for this change.
- Closeout will merge back to local `main` using the repo mutex helper if present, archive the plan, clean the task worktree/branch, and leave the goal complete only after validation passes.
