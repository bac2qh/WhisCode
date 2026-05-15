# Closeout
- Final status: implemented.
- Related checkpoint: `.agents/checkpoints/2026-05-15-shift-key-command-slots-checkpoints.md`.
- Implementation commits: `00aee07`, `859929f`.
- Merge commit: none; local `main` fast-forwarded to `859929f`.
- Verification: `uv run --with pytest python -m pytest` passed with 114 tests; focused command/enrollment/main CLI/calibration/hands-free tests passed with 52 tests; `uv run whiscode --help`, `uv run whiscode-enroll --help`, and `git diff --check` passed.
- Worktree and branch cleanup: removed `.agents/worktrees/shift-key-command-slots` and deleted local branch `shift-key-command-slots`.
- Summary: Shipped `shift-enter` and `shift-tab` trained hands-free command slots, mapped them to Shift+Enter and Shift+Tab key combos, and updated enrollment, startup checks, calibration visibility, tests, docs, and memory.

# Add Shift Key Command Slots

## Summary
Extend the existing trained hands-free command system from three slots to five: `page-up`, `page-down`, `enter`, `shift-enter`, and `shift-tab`. The new slots will be enrolled and detected the same way as the existing commands, then mapped to physical Shift+Enter and Shift+Tab key combos.

## Key Changes
- Add `shift-enter` and `shift-tab` to the command slot list, with reference folders under `~/.config/whiscode/wake/commands/`.
- Update key injection so `shift-enter` taps Enter while holding Shift, and `shift-tab` taps Tab while holding Shift.
- Ensure guided enrollment records samples for the two new command slots, and manual import accepts:
  - `uv run whiscode-enroll shift-enter ...`
  - `uv run whiscode-enroll shift-tab ...`
- Reuse existing command telemetry: `handsfree.command_detected`, `keyboard_command.injected`, and `keyboard_command.failed`, with the new bounded command names.

## Tests
- Update injector tests for Shift+Enter and Shift+Tab combo behavior.
- Update enrollment tests so guided enrollment writes samples for all five command slots.
- Update CLI/reference-check tests so missing sample counts and command directories include the new slots.
- Update command detection/calibration tests and docs to reflect five command slots.
- Verify with `uv run --with pytest python -m pytest`, `uv run whiscode --help`, `uv run whiscode-enroll --help`, and `git diff --check`.

## Assumptions
- Command slot names will be exactly `shift-enter` and `shift-tab`.
- These are idle-only voice commands like the existing three slots; they remain disabled while recording or transcribing.
- Implementation should use a task worktree from current local `main`, leave the pre-existing untracked April `.agents` files untouched, commit locally, and not push unless separately requested.
