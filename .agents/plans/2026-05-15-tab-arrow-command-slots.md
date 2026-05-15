# Add Tab And Arrow Voice Command Slots

## Summary
Extend the trained hands-free key command system from five slots to eight by adding `tab`, `arrow-up`, and `arrow-down`. These use the same enrollment, detection, telemetry, and idle-only behavior as the existing command slots.

## Key Changes
- Add command slots:
  - `tab` -> physical Tab key.
  - `arrow-up` -> physical Up Arrow key.
  - `arrow-down` -> physical Down Arrow key.
- Guided enrollment records samples for all eight command slots.
- Manual import accepts:
  - `uv run whiscode-enroll tab ...`
  - `uv run whiscode-enroll arrow-up ...`
  - `uv run whiscode-enroll arrow-down ...`
- Runtime detection, calibration, and startup reference checks pick up the new slots through the existing `COMMAND_SLOTS` pipeline.
- Reuse existing bounded command telemetry: `handsfree.command_detected`, `keyboard_command.injected`, and `keyboard_command.failed`.

## Tests
- Update injector tests for Tab, Arrow Up, and Arrow Down mappings.
- Update enrollment tests for eight command slots; guided enrollment should write 30 total samples with the default count.
- Update reference-check tests so missing setup reports 10 missing groups: wake, end, plus eight commands.
- Update calibration/docs tests to include the new command slots.
- Verify with `uv run --with pytest python -m pytest`, `uv run whiscode --help`, `uv run whiscode-enroll --help`, and `git diff --check`.

## Assumptions
- Command names are exactly `tab`, `arrow-up`, and `arrow-down`.
- These commands are idle-only like the existing command slots and remain disabled while recording or transcribing.
- Implementation uses a task worktree from current local `main`, leaves the existing untracked April `.agents` files untouched, commits locally, merges back to local `main`, and does not push unless separately requested.
