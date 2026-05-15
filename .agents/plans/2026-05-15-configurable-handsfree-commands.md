# Configurable Hands-Free Commands

## Summary

Add a command enablement config so hands-free mode only loads selected voice keyboard commands. Wake/end detection remains unchanged. Command slots are enabled only when the config allows them and their reference samples are present.

## Key Changes

- Add `~/.config/whiscode/commands.ini` as the default command config.
- Keep no-config behavior backward-compatible by considering all known command slots enabled when the config file is absent.
- If the config file exists, treat `[commands]` as an allowlist: `true` enables a command; `false` or omitted disables it; unknown command names fail with a clear error.
- Add CLI overrides: `whiscode --hands-free-command-config PATH`, `whiscode-enroll --command-config PATH`, and `whiscode-calibrate --command-config PATH`.

## Runtime Behavior

- Startup/reference checks only require enabled commands.
- Disabled commands do not need sample folders and do not block startup.
- Enabled commands still need the existing minimum reference samples; if missing, the setup/enrollment prompt handles them.
- Runtime only builds detectors for enabled commands with valid sample folders.
- Zero enabled commands is valid: wake/end recording still works, but no voice keypress commands are active.
- Guided enrollment records only enabled command slots when a config file exists; manual import can still target any known command slot.

## Telemetry And Diagnostics

- Add or update bounded telemetry for command config loading with config existence, enabled count, disabled count, and bounded command names only.
- Existing reference-check and detector-load telemetry should report counts for the active command set so logs explain why disabled commands are ignored.

## Tests

- Config parser tests for missing config, true/false values, omitted commands, invalid command names, and invalid booleans.
- Startup/reference tests proving disabled missing commands do not block hands-free mode.
- Runtime detector-load tests proving only enabled commands are loaded.
- Enrollment/calibration tests proving they respect the configured active command set.
- README update with the config path, sample config, and behavior notes.

## Assumptions

- Use INI via Python stdlib `configparser` to avoid adding dependencies.
- Keep no-config behavior backward-compatible so existing users are not forced to create config immediately.
