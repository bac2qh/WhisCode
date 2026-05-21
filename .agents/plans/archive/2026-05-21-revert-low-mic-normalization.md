# Revert Low Mic Normalization

## Closeout

- Final status: implemented.
- Related checkpoint: `.agents/checkpoints/2026-05-21-revert-low-mic-normalization-checkpoints.md`.
- Implementation commits: `129643a` (rollback), `ab4fb21` (checkpoint hash update).
- Merge commit: none; local `main` fast-forwarded to `ab4fb21`.
- Verification performed: `uv run --with pytest pytest tests/test_recorder.py tests/test_main_cli.py tests/test_handsfree.py`, `uv run --with pytest pytest`, and `git diff --check`.
- Worktree and branch cleanup: removed `.agents/worktrees/revert-low-mic-normalization`; deleted local branch `revert-low-mic-normalization`.
- Summary: removed pre-transcription gain normalization and restored the raw capture-to-transcription path. Project memory records that flat overlay bars point to raw input/device-level investigation.

## Goal

Revert the pre-transcription gain normalization change because the low overlay bars indicate the problem is likely upstream at the current input device or raw capture level, not Whisper input scaling.

## Scope

- Remove bounded pre-transcription normalization code and its call sites.
- Remove tests, docs, wiki notes, and project memory that described normalization as implemented behavior.
- Keep existing recorder, overlay, and hands-free behavior otherwise unchanged.
- Preserve historical archived checkpoint/plan files for the reverted work unless they are active behavior documentation.

## Telemetry And Diagnostics

- This rollback removes `audio.normalization_applied` because normalization will no longer run.
- No new telemetry is required for the revert itself; it restores prior behavior.
- Follow-up investigation should target raw input diagnostics: selected input device, channel mapping, raw RMS/peak, and CoreAudio/device gain settings.

## Verification

- Run focused recorder/main tests after rollback.
- Run the full test suite if practical.
