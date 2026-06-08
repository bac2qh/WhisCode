# Fix Recording Overlay Timer Freeze

## Closeout
- Final status: implemented, validated, merged to local , and archived.
- Related checkpoint: .
- Implementation commits:
  -  ()
  -  ()
- Merge commit: none; local  was fast-forwarded from  to .
- Verification performed:
  - ============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/xin/Documents/repos/WhisCode
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 22 items

tests/test_recording_overlay.py ......................                   [100%]

============================== 22 passed in 0.06s ============================== -> 22 passed.
  - ============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/xin/Documents/repos/WhisCode
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 92 items

tests/test_recording_overlay.py ......................                   [ 23%]
tests/test_main_cli.py ........................................          [ 67%]
tests/test_recorder.py ..                                                [ 69%]
tests/test_handsfree.py ............................                     [100%]

============================== 92 passed in 0.29s ============================== -> 92 passed.
  -  -> clean.
  -  verdict: .
- Worktree/branch cleanup result: removed ; deleted local branch .
- Shipped summary: Recording overlay level ticks now follow the active recording item id, so a new recording card keeps animating while older queued/transcribing cards remain visible.

## Status
Closed and archived.

## Status
- Active implementation plan.
- Branch/worktree: `fix-overlay-recording-ticks` at `.agents/worktrees/fix-overlay-recording-ticks`.
- Related checkpoint: `.agents/checkpoints/2026-06-08-overlay-recording-ticks-checkpoints.md`.

## Objective
Fix the stacked overlay bug where a new recording card can freeze while an older transcription card is still active.

## Problem Summary
`RecordingOverlayClient` uses one global client `_mode`, but the helper UI supports multiple item modes. When another item is shown as transcribing, the client's sender thread can stop sending level ticks even though a separate recording item is still active.

## Implementation Plan
1. Inspect `RecordingOverlayClient` and current recording overlay tests.
2. Make the sender thread decide whether to emit periodic level commands from `_active_recording_item_id`, not the global `_mode`.
3. Preserve existing helper JSON command shapes and public CLI/API behavior.
4. Preserve queued/transcribing stacked-card behavior.
5. Add a focused regression test that shows a recording item, shows a different transcribing item, and verifies periodic level commands still target the recording item.
6. Run focused and relevant pytest coverage.
7. Send the diff and validation contract to `mission_validator` for independent Validator Workflow review.

## Validation Contract
- `VC-001 critical`: A recording card continues receiving level tick commands after another item is shown as transcribing.
- `VC-002 critical`: Removing or queueing the active recording item stops level ticks for that item.
- `VC-003 important`: Legacy single-item overlay commands still behave as before.
- `VC-004 important`: Existing overlay lifecycle, orphan cleanup, and transcription progress tests still pass.
- `VC-005 advisory`: No transcript, audio, prompt, hotword, provider payload, or typed text is added to diagnostics.

## Telemetry / Debuggability
No new telemetry event is planned. This is a local UI state bug in the overlay client tick loop; existing `recording_overlay.disabled` diagnostics still cover helper launch/write failures. Static validation plus focused regression tests are sufficient. No diagnostics may include transcript, audio, prompt, hotword, provider payload, or typed text.

## Test Plan
- Run the focused regression test in `tests/test_recording_overlay.py`.
- Run the full overlay test file with the repo's pytest command, expected shape: `uv run pytest tests/test_recording_overlay.py`.
- If practical, run the broader relevant suite: `uv run pytest tests/test_recording_overlay.py tests/test_main_cli.py tests/test_recorder.py tests/test_handsfree.py`.

## Assumptions
- Recording stopwatch and waveform should keep animating while older queued/transcribing cards remain visible.
- The implementation should be minimal and preserve the current helper process architecture.
- Independent AppKit repaint timers are out of scope unless focused tests reveal level ticks still cannot drive repaint reliably.