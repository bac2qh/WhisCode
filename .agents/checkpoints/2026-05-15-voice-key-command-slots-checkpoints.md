# Voice Key Command Slots Checkpoints

## 2026-05-15 Start

- Created task branch/worktree `add-voice-key-commands` from local `main` at `6bf5377`.
- Saved the implementation plan before source edits.
- Immediate next step: add command slot constants, enrollment support, runtime detection, key injection, telemetry, and tests.
- Verification: pending implementation.

## 2026-05-15 Implementation

- Implementation commit: `7996220` (`Add trained hands-free key commands`).
- Added configurable command reference folders under `~/.config/whiscode/wake/commands/{page-up,page-down,enter}`.
- Extended guided enrollment and sample import to support wake, end, and the three key command slots.
- Extended hands-free runtime with idle-only command detectors. Commands use the same detector window, speech-energy gate, distance telemetry, and confirmation behavior as wake detection, then reset the idle buffer after a command event to avoid repeated key taps from one utterance.
- Added physical key injection for Page Up, Page Down, and Enter through `pynput`.
- Added command threshold/confirmation CLI flags, command detector loading, command detection/key-injection telemetry, and calibration report visibility for command reference/telemetry distances.
- Updated README, wiki, tests, and project memory.
- Verification:
  - `uv run --with pytest python -m pytest` passed: 104 tests.
  - `uv run whiscode --help` passed.
  - `uv run whiscode-enroll --help` passed.
  - `uv run whiscode-calibrate --help` passed.
- Immediate next step: commit this checkpoint update, then close out and merge to local `main`.

## 2026-05-15 Closeout

- Merged `add-voice-key-commands` into local `main` with a fast-forward from `6bf5377` to `cbb6e35`; no merge commit was created.
- Archived the plan to `.agents/plans/archive/2026-05-15-voice-key-command-slots.md` with a closeout note.
- Removed `.agents/worktrees/add-voice-key-commands` and deleted local branch `add-voice-key-commands`.
- Verification carried forward from implementation: `uv run --with pytest python -m pytest` passed with 104 tests; CLI help checks passed for `whiscode`, `whiscode-enroll`, and `whiscode-calibrate`.
- Immediate next step: none for this plan.
