# Revert Low Mic Normalization Checkpoints

## 2026-05-21

### Current State

- User clarified that the overlay bars themselves are very flat on the current input device.
- Since overlay bars are driven directly from raw captured audio RMS, pre-transcription normalization does not address the observed root issue.
- The normalization work is present on local `main` in commits `6fb4556`, `c9f826d`, and `f95a7cd`.

### Plan

- Revert active code/docs/memory for the normalization behavior.
- Verify the rollback.
- Commit and close out through local `main`.

### Next Step

- Commit the rollback, then close out to local `main`.

### Verification

- `uv run --with pytest pytest tests/test_recorder.py tests/test_main_cli.py tests/test_handsfree.py` passed: 38 tests.
- `uv run --with pytest pytest` passed: 138 tests.
- `git diff --check` passed.

### Implemented

- Removed `normalize_for_transcription`, `prepare_transcription_audio`, and the `audio.normalization_applied` runtime path.
- Removed normalization-specific tests.
- Removed active README/wiki documentation that described normalization as current behavior.
- Updated memory and logs to record that the normalization hypothesis was reverted because flat overlay bars indicate a raw input/device-level issue.

### Commits

- Pending.
