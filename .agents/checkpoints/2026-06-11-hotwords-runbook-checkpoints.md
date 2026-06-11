# Hotwords Runbook Update Checkpoints

Date: 2026-06-11
Plan: `.agents/plans/2026-06-11-hotwords-runbook.md`
Branch: `task/hotwords-runbook`
Worktree: `.agents/worktrees/hotwords-runbook`

## Initial State

- User requested: remove long autonomous run from hotwords and add runbook to hotwords.
- User approved implementation with: "yeah go do it".
- Main project root confirmed: `/Users/xin/Documents/repos/WhisCode`.
- Live hotwords file inspected at `~/.config/whiscode/hotwords.txt`; it contains `long-autonomous-run skill` and does not contain `runbook`.
- Main worktree was clean before creating the task worktree.

## Validation Contract

- VC-001 (critical): live hotwords file contains standalone `runbook`.
- VC-002 (critical): live hotwords file no longer contains `long-autonomous-run skill`.
- VC-003 (important): repo source/docs behavior remains unchanged for this user-config-only update.

## Progress

- Created task worktree and branch.
- Saved plan and checkpoint before editing.
- Edited `~/.config/whiscode/hotwords.txt`:
  - removed `long-autonomous-run skill`
  - added standalone `runbook`
- Committed initial task bookkeeping: `63b8e0d` (`Record runbook hotword update`).

## Verification

- VC-001 passed: `rg -n "long-autonomous-run skill|runbook" ~/.config/whiscode/hotwords.txt -S` returned `9:runbook`.
- VC-002 passed: the same targeted search returned no `long-autonomous-run skill` line.
- VC-003 passed so far: `git status --short` shows only the saved plan/checkpoint files in this task worktree.

## Next Step

- Commit checkpoint commit-hash update, then close out the task branch into local `main`.
