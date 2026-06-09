# Add Voice Scroll Commands

## Status
Active implementation plan.

## Objective
Add two hands-free command slots, `scroll-up` and `scroll-down`, to WhisCode's existing command-slot pipeline.

## Locked Behavior
- `scroll-up` reveals older terminal output above the current view.
- `scroll-down` moves back toward newer output.
- Each command scrolls about half of the main display height.
- There is no v1 tuning flag or config value.
- New slots are default-on when `commands.ini` is missing, matching existing command behavior.
- Scroll commands are detected only while idle, preserving the existing active-recording gate.

## Implementation Scope
- Extend command slot definitions, command config parsing, enrollment/import flows, guided enrollment, calibration, and reference-distance checks to include `scroll-up` and `scroll-down`.
- Implement scroll injection as macOS Quartz pixel scroll-wheel events through the existing macOS dependency path.
- Keep existing key-command mappings and physical key actions unchanged.
- Update focused tests and docs.

## Public Interfaces
`commands.ini` accepts:

```ini
scroll-up = true
scroll-down = true
```

`whiscode-enroll` accepts manual import kinds:

```text
scroll-up
scroll-down
```

Guided enrollment records samples for both new slots when enabled. `whiscode-calibrate` includes scroll command reference-distance groups.

## Telemetry / Debuggability
Scroll injection adds bounded success/failure telemetry separate from the existing `handsfree.command_detected` event.

Required event shape:
- Bounded event name for scroll injection.
- Command name: `scroll-up` or `scroll-down`.
- Direction: older/newer or equivalent bounded value.
- Pixel amount.
- Outcome and bounded error type on failure.

Privacy/cardinality constraints:
- Do not log transcripts, spoken phrase text, raw audio, prompts, secrets, credentials, personal names, media bytes, or provider payloads.
- Do not include unbounded target app/window names or user content.

Ambiguous failures to make diagnosable:
- Quartz dependency unavailable.
- Quartz API raises during event creation or posting.
- Unexpected command passed to the injector.

## Validation Contract
- `VC-001` critical behavior: `scroll-up` and `scroll-down` are valid command slots everywhere existing command slots are valid. Evidence: unit tests for config, enrollment, reference checks, and calibration.
- `VC-002` critical behavior: existing key commands still emit the same physical key actions. Evidence: injector unit tests for all existing mappings.
- `VC-003` critical behavior: `scroll-up` emits a half-screen scroll toward older terminal history, and `scroll-down` emits the inverse. Evidence: injector tests with mocked Quartz plus manual smoke test in a scrollable terminal/Codex view when practical.
- `VC-004` important regression: command detection remains disabled during active recording. Evidence: existing hands-free command tests still pass.
- `VC-005` important telemetry/privacy: scroll success/failure telemetry is bounded and content-free. Evidence: static review plus telemetry assertions where practical.
- `VC-006` important docs/API: README and wiki describe the two new commands, enrollment, config, and semantics. Evidence: docs diff review.

## Test Plan
Focused tests:

```bash
.venv/bin/python -m pytest tests/test_command_config.py tests/test_injector.py tests/test_enroll.py tests/test_main_cli.py tests/test_calibrate.py tests/test_handsfree.py
```

Full suite after focused tests pass:

```bash
.venv/bin/python -m pytest
```

Manual smoke when practical:
- Enroll or import `scroll-up` and `scroll-down` samples.
- Start WhisCode hands-free in a long terminal/Codex session.
- Say `scroll up`; verify older output is revealed.
- Say `scroll down`; verify newer output returns.

## Assumptions
- The app remains macOS-focused.
- Scroll events target the active/frontmost scroll context without moving the mouse or clicking.
- If live smoke shows Quartz sign inversion in the target app, invert the sign while preserving the locked user-facing semantics.
