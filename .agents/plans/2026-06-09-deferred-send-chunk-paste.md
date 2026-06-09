# Deferred Send Chunk Paste

## Summary
- Current Send Chunk delivery transcribes each chunk independently and immediately sends the processed text through `type_text()`, which copies to the clipboard and pastes with Cmd+V.
- Change Send Chunk sessions so intermediate chunk transcripts stay in process memory and paste once when the final non-chunk stop/end/timeout job completes.
- Apply this to all Send Chunk modes: hotkey-only Send Chunk, hands-free voice Send Chunk, and hands-free manual fallback Send Chunk.
- Preserve ordinary single-recording behavior: recordings that do not use Send Chunk still paste immediately.

## Key Changes
- Add queue delivery metadata to reservations/jobs:
  - `delivery_batch_id`: shared id for a Send Chunk session.
  - `defer_text`: true for jobs whose transcript should be buffered instead of immediately pasted.
  - `is_delivery_final`: true for the final job that should flush and close the batch.
- Create a batch id on the first Send Chunk request in a session, carry it through restarted recordings, and enqueue the final stop/end/timeout job as the batch-final job.
- Add an in-memory deferred transcript buffer keyed by batch id. Successful processed text is appended in FIFO transcription order, including existing chunk suffixes, and final flush joins the stored strings and calls `type_text()` once.
- Empty or failed jobs contribute no text. A final empty/failed job still closes the batch and pastes any successful earlier chunks. If the batch has no successful text, paste nothing.
- Keep stdout transcript printing immediate per successful job, keep stats based on processed text before suffixes, and leave external transcription plus hands-free key commands untouched.

## Telemetry / Debuggability
- Add bounded delivery telemetry for buffered, flushed, and empty final batches.
- Payloads may include job id, local batch id, chunk count, text character count, skipped count, source, outcome, and queue depth.
- Payloads must not include transcript text, typed text, prompts, audio, provider payloads, secrets, credentials, full paths, or raw user content.

## Validation Contract
- `VC-001` critical behavior: hotkey Send Chunk does not paste intermediate chunks; final hotkey stop pastes ordered chunk plus final text. Evidence: focused unit tests with mocked `type_text`. Mode: scrutiny.
- `VC-002` critical behavior: hands-free voice and manual Send Chunk defer paste until end phrase, manual stop, or timeout. Evidence: focused queue/delivery tests. Mode: scrutiny.
- `VC-003` critical regression: single recordings without Send Chunk paste immediately as before. Evidence: existing and new delivery tests. Mode: scrutiny.
- `VC-004` important failure handling: failed or empty chunks are skipped; final close still flushes successful text. Evidence: buffer tests. Mode: scrutiny.
- `VC-005` important state isolation: separate Send Chunk sessions do not mix buffered text, even if a new recording starts while prior transcription work is draining. Evidence: batch-id tests. Mode: scrutiny.
- `VC-006` important privacy/security: telemetry and docs remain transcript-free and content-free. Evidence: static review and telemetry assertions. Mode: scrutiny.

## Test Plan
- Add unit tests for deferred buffer behavior and queue metadata defaults/carrying.
- Add focused delivery tests that mock text injection and verify immediate versus deferred paste behavior.
- Update README/wiki/current-state docs for Send Chunk delayed paste behavior.
- Run focused tests:
  - `uv run --with pytest pytest tests/test_main_cli.py tests/test_transcription_queue.py tests/test_injector.py tests/test_telemetry.py tests/test_handsfree.py`
- Run full verification:
  - `uv run --with pytest pytest`
  - `uv run python -m compileall whiscode`
  - `git diff --check`

## Assumptions
- No new CLI flag or config setting.
- A final job is the normal stop/end/timeout after one or more Send Chunk actions.
- Buffering is process-memory only. If WhisCode exits before final flush, buffered paste is lost, while immediate stdout transcript output remains available.
- Validator Workflow: implementation stays in the main thread and `mission_validator` performs independent validation before closeout.
