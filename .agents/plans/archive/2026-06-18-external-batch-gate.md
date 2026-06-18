# External Transcription Batch Gate

Closeout note, 2026-06-18:
- Final status: complete, validated, merged to local main, and archived.
- Related checkpoint: `.agents/checkpoints/2026-06-18-external-batch-gate-checkpoints.md`.
- Implementation commit: `ddf54ec` Gate external transcription during local delivery batches.
- Merge result: fast-forwarded local `main` from `cdd307b` to `ddf54ec`; no merge commit.
- Verification performed: `git diff --check` passed; `uv run --with pytest pytest tests/test_main_cli.py tests/test_transcription_queue.py tests/test_external_transcription.py tests/test_asr_engine_manager.py -q` passed with 77 tests in the main thread; `mission_validator` reran the focused suite successfully and returned `APPROVE` with all validation contract assertions passed.
- Worktree/branch cleanup: removed `.agents/worktrees/external-batch-gate`; deleted local branch `codex/external-batch-gate`.
- Shipped summary: external NAS transcription jobs now wait while a local Send Chunk delivery batch is open, still wait for reserved/queued/active local transcription work, requeue if local work appears after dequeue, and emit bounded `external.start_deferred` diagnostics without content or paths.

Date: 2026-06-18
Status: archived
Related checkpoint: `.agents/checkpoints/2026-06-18-external-batch-gate-checkpoints.md`

## Objective
Add a small explicit gate before external transcription starts: external jobs must wait while any local Send Chunk delivery batch is open. Keep the existing separate external queue and ASR lane; do not route external requests through the local `TranscriptionJobQueue` or deferred delivery buffer.

Goal Mode is active for this implementation. Use Validator Workflow after the main-thread implementation, with the validation contract below.

## Key Changes
- In `main.py`, add a small external-start gate used by `external_worker()`:
  - Block when `active_delivery_batch_id is not None`.
  - Continue blocking when local transcription queue is not idle, preserving existing behavior.
  - Recheck the gate after popping an external job; if blocked, requeue it.
- Keep external transcription behavior unchanged once started: VibeVoice-only, no hotwords/prompt/postprocess/refine/typing/stats/deferred delivery.
- Add bounded telemetry for pending external work deferred by the new gate, emitted only when a pending external job is blocked and the block reason changes:
  - Event: `external.start_deferred`
  - Properties: `reason`, `external_queue_depth`, `local_queue_depth`
  - No transcript text, audio, file paths, prompts, credentials, or provider payloads.

## Validation Contract
- `VC-001` critical, behavior, scrutiny: external jobs do not start while `active_delivery_batch_id` is set. Evidence: focused unit test plus code review of `external_worker()`.
- `VC-002` critical, regression, scrutiny: existing local priority still holds for reserved, queued, or active local transcription work. Evidence: existing queue/external tests pass.
- `VC-003` important, regression, scrutiny: external jobs remain outside local deferred delivery, typing, postprocess, refinement, and stats. Evidence: static review plus existing external sidecar tests.
- `VC-004` important, telemetry/privacy, scrutiny: new telemetry is bounded and content-free. Evidence: test or static review of emitted fields.
- `VC-005` important, docs/API, scrutiny: no CLI or public API changes. Evidence: parse-args tests pass.

## Telemetry / Debuggability
- Emit `external.start_deferred` only when an external job is pending and the scheduler block reason changes.
- The payload is limited to `reason`, `external_queue_depth`, and `local_queue_depth`.
- Accepted reasons must be bounded enums, not user content.
- Do not emit transcript text, raw audio, file paths, prompts, credentials, provider payloads, or external request contents.
- Verification must include a focused test or static review confirming the emitted fields.

## Test Plan
- Add tests for the external-start gate:
  - idle queue plus open delivery batch => blocked with `local_delivery_batch`.
  - busy local queue plus no batch => blocked with existing local-work reason.
  - idle queue plus no batch => allowed.
- Add or adjust telemetry test to confirm `external.start_deferred` contains only bounded queue/reason metadata.
- Run focused suite:
  - `uv run pytest tests/test_main_cli.py tests/test_transcription_queue.py tests/test_external_transcription.py tests/test_asr_engine_manager.py -q`

## Assumptions
- Strict policy chosen: external jobs wait until the local Send Chunk batch is finalized and flushed.
- No new external API surface is added in this pass; this only hardens the existing external queue scheduler.
- No push or commit is required unless requested during implementation closeout.
