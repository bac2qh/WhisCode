# Hotwords Runbook Update

Date: 2026-06-11
Status: active
Checkpoint: `.agents/checkpoints/2026-06-11-hotwords-runbook-checkpoints.md`

## Summary

Update the live WhisCode hotwords file at `~/.config/whiscode/hotwords.txt` so dictation no longer biases toward the retired long autonomous run skill phrase and does bias toward `runbook`.

## Implementation

- Remove the live hotword entry `long-autonomous-run skill`.
- Add `runbook` as a plain hotword if it is not already present.
- Leave repo README examples unchanged because the user asked for the active hotwords list, not documentation.

## Validation Contract

- VC-001 (critical, behavior, scrutiny): `~/.config/whiscode/hotwords.txt` contains a standalone `runbook` entry. Evidence: re-read the file or targeted search.
- VC-002 (critical, behavior, scrutiny): `~/.config/whiscode/hotwords.txt` no longer contains `long-autonomous-run skill`. Evidence: targeted search returns no matching line.
- VC-003 (important, regression, scrutiny): no source or README behavior is changed for this user-config-only update. Evidence: `git status --short` reviewed before closeout.

## Telemetry / Debuggability

Not applicable. This changes a local ASR hint configuration file only; it does not alter app workflows, backend routes, provider calls, storage, telemetry, or production recovery behavior.

## Assumptions

- The intended hotwords file is the default file used by WhisCode: `~/.config/whiscode/hotwords.txt`.
- `runbook` should be a plain ASR hint, not a deterministic replacement rule.
