# External Transcription Batch Gate Checkpoints

Date: 2026-06-18
Plan: `.agents/plans/archive/2026-06-18-external-batch-gate.md`
Branch: `codex/external-batch-gate`
Worktree: `.agents/worktrees/external-batch-gate`
Status: complete, merged, archived

## Validation Contract
- `VC-001` critical, behavior, scrutiny: external jobs do not start while `active_delivery_batch_id` is set. Evidence: focused unit test plus code review of `external_worker()`.
- `VC-002` critical, regression, scrutiny: existing local priority still holds for reserved, queued, or active local transcription work. Evidence: existing queue/external tests pass.
- `VC-003` important, regression, scrutiny: external jobs remain outside local deferred delivery, typing, postprocess, refinement, and stats. Evidence: static review plus existing external sidecar tests.
- `VC-004` important, telemetry/privacy, scrutiny: new telemetry is bounded and content-free. Evidence: test or static review of emitted fields.
- `VC-005` important, docs/API, scrutiny: no CLI or public API changes. Evidence: parse-args tests pass.

## 2026-06-18 Initial State
- Created task worktree and branch from `main` at `cdd307b`.
- Confirmed project memory index exists and reviewed relevant external queue and telemetry topic memory.
- Saved active plan and matching checkpoint before source edits.
- Main worktree has unrelated local changes (`.gitignore` and two untracked April 26 plan/checkpoint files); task implementation will avoid modifying those.

## Immediate Next Step
- None. Closeout completed locally on `main`.

## Verification
- `uv run pytest tests/test_main_cli.py tests/test_transcription_queue.py tests/test_external_transcription.py tests/test_asr_engine_manager.py -q` did not run tests because this project does not declare `pytest`; `uv` fell through to a global Homebrew Python and collection failed with missing `pynput`/`whiscode` imports.
- `uv run --with pytest pytest tests/test_main_cli.py tests/test_transcription_queue.py tests/test_external_transcription.py tests/test_asr_engine_manager.py -q` passed: 77 tests in 4.56s.
- `git diff --check` passed with no whitespace errors.
- Validator Workflow: `mission_validator` reviewed the validation contract, scheduler code, queue semantics, telemetry helper, external sidecar path, parser surface, and docs/memory updates. It reran `uv run --with pytest pytest tests/test_main_cli.py tests/test_transcription_queue.py tests/test_external_transcription.py tests/test_asr_engine_manager.py -q` successfully (`77 passed in 0.52s`) and returned `APPROVE` with no findings.
- Validator assertion results:
  - `VC-001`: passed.
  - `VC-002`: passed.
  - `VC-003`: passed.
  - `VC-004`: passed.
  - `VC-005`: passed.

## Commits
- `ddf54ec` Gate external transcription during local delivery batches.

## 2026-06-18 Implementation
- Added explicit external start gate helpers in `whiscode/main.py`:
  - `local_delivery_batch` blocks when `active_delivery_batch_id` is set.
  - `local_work` preserves the existing local priority behavior for non-idle `TranscriptionJobQueue` state.
- Updated `external_worker()` to check the gate before waiting for an external job and again after popping one. If the second check blocks, the external job is requeued before the worker waits.
- Added bounded `external.start_deferred` telemetry emitted only when pending external work is blocked and the block reason changes. Payload is limited to `reason`, `external_queue_depth`, and `local_queue_depth`.
- Kept external transcription processing unchanged once started: jobs still call `process_external_file()`, use `asr_backend.transcribe_external()`, and bypass local deferred delivery, typing, postprocess, refinement, and stats.
- Added focused tests in `tests/test_main_cli.py` for open delivery batch blocking, reserved/queued/active local work blocking, idle allowance, and bounded reason-change telemetry.
- Updated current-state wiki and project memory for the new external batch gate and telemetry diagnostic.

## 2026-06-18 Closeout
- Local `main` fast-forwarded to implementation commit `ddf54ec`.
- Active plan moved to `.agents/plans/archive/2026-06-18-external-batch-gate.md` with closeout note.
- Removed task worktree `.agents/worktrees/external-batch-gate` and deleted local branch `codex/external-batch-gate`.
- No push was performed.
