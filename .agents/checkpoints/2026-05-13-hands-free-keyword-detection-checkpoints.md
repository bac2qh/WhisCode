# Hands-Free Keyword Trigger V1 Checkpoints

## 2026-05-13
- Saved the finalized plan before implementation in branch `hands-free-keyword-detection` at worktree `.agents/worktrees/hands-free-keyword-detection`.
- Source branch is local `main` at `ecab2aebfdb2d7a46cf02f2d985eb3d269ac84cb`.
- Current repo memory index exists and currently lists recording status notifications.
- Immediate next step: inspect `local-wake` package API, then implement enrollment import, hands-free detector loop, CLI flags, tests, and diagnostics.

## Implementation
- Added `local-wake==0.1.2` and the `whiscode-enroll` console script.
- Added `whiscode.enroll` for importing Voice Memo `.m4a` or other audio samples into wake/end reference WAV folders using `afconvert`.
- Added `whiscode.handsfree` with:
  - `LocalWakeDetector` wrapping `local-wake` support-set loading and distance scoring.
  - `HandsFreeSession` for testable wake/end/manual/timeout state transitions.
  - `HandsFreeAudioLoop` for the always-open microphone reader.
- Updated `whiscode.main` with `--hands-free` and detector tuning flags while keeping hotkey-only mode unchanged by default.
- Kept Right Shift as a fallback in hands-free mode.
- Added README and wiki documentation for enrollment and runtime usage.
- Key implementation choice: added `--hands-free-tail-seconds` with a 1.0s default so end phrase audio is trimmed without discarding the full 2.0s detector window of dictated content.
- Diagnostics:
  - Emits bounded events/status lines for `handsfree.started`, `handsfree.wake.detected`, `handsfree.end.detected`, `handsfree.timeout`, detector errors, audio overflow, and optional detector distances.
  - Does not log raw audio, prompts, sample contents, or additional transcript text beyond the existing transcription output.
- Verification:
  - `uv run --with pytest python -m pytest` passed: 64 tests.
  - `uv run whiscode --help` passed.
  - `uv run whiscode-enroll --help` passed.
  - `uv run --with local-wake python -c "import lwake; print('local-wake ok')"` passed.
- Implementation commit: `bfd9aa8` (`Add hands-free keyword detection mode`).
- Bookkeeping commit: `3c006d2` (`Record hands-free keyword implementation checkpoint`).
- Closeout:
  - Fast-forwarded local `main` to `3c006d2`.
  - Added closeout note to the plan before archival.
  - Archived the plan under `.agents/plans/archive/`.
  - Removed `.agents/worktrees/hands-free-keyword-detection`.
  - Deleted local branch `hands-free-keyword-detection`.
- Immediate next step: commit closeout bookkeeping on local `main`.
