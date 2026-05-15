# Fix Recording Overlay Crash Checkpoints

## 2026-05-15 Start

- Created task branch/worktree `fix-recording-overlay-crash` from local `main` at `870a643`.
- Saved the implementation plan before source edits.
- Root cause from live probe and macOS logs: overlay helper exits with SIGTRAP while drawing timer text because `drawRect_` calls `drawAtPoint_withAttributes_` on a Python `str`.
- Immediate next step: fix text drawing, add helper crash diagnostics, and verify with tests plus a live overlay probe.
- Verification: pending implementation.

## 2026-05-15 Implementation

- Implementation commit: `c7b1242` (`Fix recording overlay helper crash`).
- Fixed timer text rendering by drawing an `NSAttributedString` instead of calling AppKit drawing selectors on a Python `str`.
- Added overlay helper failure diagnostics. `RecordingOverlayClient` now disables itself, emits `recording_overlay.disabled`, and prints a bounded stderr warning when launch, pipe, or helper-exit failures occur.
- Passed telemetry into the overlay client from normal runtime and guided enrollment.
- Updated tests, wiki, and project memory.
- Verification:
  - `uv run --with pytest python -m pytest` passed: 111 tests.
  - `uv run whiscode --help` passed.
  - `uv run whiscode-enroll --help` passed.
  - `git diff --check` passed.
  - Live overlay helper probe passed: `poll_after_start None`, `poll_after_show None`, `returncode 0`, no stderr.
- Immediate next step: commit this checkpoint update, then close out to local `main`.
