# Revert Low Mic Normalization

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
