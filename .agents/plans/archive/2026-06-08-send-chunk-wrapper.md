# Send Chunk Wrapper

## Closeout
- Final status: implemented, validated, merged to local `main`, and archived.
- Related checkpoint: `.agents/checkpoints/2026-06-08-send-chunk-wrapper-checkpoints.md`.
- Implementation commits:
  - `638b980` (`Implement send chunk recording wrapper`)
  - `7e79ed2` (`Record send chunk implementation checkpoint`)
- Merge commit: none; local `main` was fast-forwarded from `a278e3a` to `7e79ed2`.
- Verification performed:
  - `uv run --with pytest pytest tests/test_main_cli.py tests/test_handsfree.py tests/test_enroll.py tests/test_transcription_queue.py tests/test_injector.py tests/test_telemetry.py` -> 101 passed.
  - `uv run --with pytest pytest` -> 267 passed.
  - `git diff --check` -> clean.
  - `mission_validator` final verdict: `APPROVE`.
- Worktree/branch cleanup result: removed `.agents/worktrees/send-chunk-wrapper`; deleted local branch `feature/send-chunk-wrapper`.
- Shipped summary: Send Chunk now works as a manual Right Option + Right Shift chord and as an optional hands-free chunk phrase; chunk recordings queue with a typed blank-line suffix and immediately restart recording, with chunk enrollment, docs, tests, and bounded telemetry.

## Status
Closed and archived.

## Workflow
- Use Validator Workflow with Goal Mode active.
- Implement in the main thread.
- Use `mission_validator` for independent validation before closeout.
- Task branch/worktree: `feature/send-chunk-wrapper` at `.agents/worktrees/send-chunk-wrapper`.

## Summary
Implement Send Chunk as a small wrapper around existing behavior: stop the current recording, queue it so the eventual typed transcript has `\n\n` appended, then immediately start a new recording.

## Key Changes
- Add a manual Send Chunk control using default chord `alt_r+shift_r` (Right Option held, then Right Shift). If that chord fires, suppress the normal Right Shift toggle for that press.
- Add a shared `send_chunk()` runtime path:
  - In manual/hotkey mode, stop using existing manual stop behavior; no audio trim.
  - Enqueue the just-finished recording with a `text_suffix="\n\n"` marker.
  - Immediately reserve/start the next recording using the existing start path.
- Apply the suffix after ASR/postprocess/refine, before `type_text()`: `processed + "\n\n"`. Keep stats based on `processed`, not the added newlines.
- Add voice Send Chunk only while recording:
  - New chunk reference dir: `~/.config/whiscode/wake/chunk`.
  - Auto-enable when samples exist; `--hands-free-chunk` forces setup/prompting.
  - Detect `chunk.detected`, trim the chunk command tail from the completed chunk using inferred chunk phrase length plus the existing `--hands-free-tail-extra-seconds`, then start the next recording immediately.
- Add `whiscode-enroll chunk ...` and guided `--include-chunk` support for recording chunk samples.
- Keep overlay changes out of scope.

## Telemetry / Debuggability
Add bounded events for:
- `send_chunk.requested`
- `send_chunk.queued`
- `send_chunk.restarted`
- `send_chunk.rejected`
- `handsfree.chunk_detected`
- chunk tail resolution

Telemetry must not log audio, transcripts, prompts, hotword text, typed content, secrets, provider payloads, or full file paths.

## Validation Contract
- `VC-001` critical behavior: manual Send Chunk stops, queues with suffix, and restarts recording without trimming. Evidence: focused tests. Mode: scrutiny.
- `VC-002` critical behavior: voice Send Chunk trims the new chunk phrase tail, not the end phrase tail. Evidence: hands-free session tests. Mode: scrutiny.
- `VC-003` critical regression: existing Right Shift start/stop, end phrase, timeout, queue FIFO, and typing behavior remain unchanged. Evidence: existing tests pass. Mode: scrutiny.
- `VC-004` important behavior: `\n\n` is appended to successful chunk transcripts after postprocessing/refinement and before paste. Evidence: transcription processing tests. Mode: scrutiny.
- `VC-005` important behavior: `alt_r+shift_r` triggers Send Chunk without also firing the plain Right Shift toggle. Evidence: chord tests. Mode: scrutiny.
- `VC-006` important docs/API: chunk phrase is opt-in by samples or `--hands-free-chunk`; existing users are not forced into chunk enrollment. Evidence: CLI/reference tests and docs review. Mode: scrutiny.
- `VC-007` important privacy/security: new telemetry is bounded and content-free. Evidence: static review and telemetry assertions. Mode: scrutiny.

## Test Plan
Run focused tests for `main_cli`, `handsfree`, `enroll`, `transcription_queue`, `injector`, and telemetry behavior, then run full pytest if the local environment supports it.

## Assumptions
- Right Option maps to `pynput.keyboard.Key.alt_r`.
- The detection-delay buffer is the current resolved `--hands-free-tail-extra-seconds` value, not a hard-coded duration.
- Validator Workflow means no `mission_worker`; implementation stays in the main thread and `mission_validator` verifies independently.
