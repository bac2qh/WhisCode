# Add Daletong Hotword

Date: 2026-06-05
Status: active
Related checkpoint: `.agents/checkpoints/2026-06-05-add-daletong-hotword-checkpoints.md`

## Objective

Add `达乐通` as a WhisCode hotword so ASR can bias toward the phrase and the tracked hotwords example reflects the available entry.

## Scope

- Update `hotwords.example.txt` with `达乐通` as a plain hotword entry.
- Update the default local runtime hotwords file at `~/.config/whiscode/hotwords.txt` if permission is granted.
- Preserve existing hotword parser behavior.

## Validation Contract

- VC-001 (`critical`, behavior, scrutiny): `达乐通` is present as a plain hotword entry, not a replacement rule. Evidence: file inspection and parser output include `达乐通` in the words list.
- VC-002 (`important`, regression, scrutiny): Existing hotword parsing and replacement tests still pass. Evidence: focused hotwords tests complete successfully.

## Telemetry / Debuggability

Not applicable. This change only adds a static hotword entry and does not touch runtime workflows, backend routes, provider calls, telemetry, logging, or diagnostic signals.

## Plan

1. Add `达乐通` to the tracked hotwords example.
2. Add `达乐通` to the local default runtime hotwords file when allowed.
3. Run focused hotwords tests and inspect the diff.
