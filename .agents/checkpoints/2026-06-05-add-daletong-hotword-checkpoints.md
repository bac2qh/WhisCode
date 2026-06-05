# Add Daletong Hotword Checkpoints

Date: 2026-06-05
Plan: `.agents/plans/2026-06-05-add-daletong-hotword.md`

## Initial Checkpoint

- Main project root: `/Users/xin/Documents/repos/WhisCode`.
- Task worktree: `/Users/xin/Documents/repos/WhisCode/.agents/worktrees/add-daletong-hotword`.
- Branch: `task/add-daletong-hotword`.
- Scope: add `达乐通` to hotwords without changing parser behavior.
- Validation contract:
  - VC-001: `达乐通` is present as a plain hotword entry.
  - VC-002: focused hotword tests still pass.
- Telemetry/debuggability: not applicable because this is a static hotword entry change.
- Immediate next step: edit `hotwords.example.txt`, update the local default hotwords file if permitted, then run focused verification.

## Implementation Checkpoint

- Added `达乐通` as a plain hotword entry in `hotwords.example.txt`.
- Added `达乐通` to the default runtime hotwords file at `~/.config/whiscode/hotwords.txt` after permission was granted.
- Verification:
  - `uv run pytest tests/test_hotwords.py` failed because `pytest` is not installed in the default project runtime environment.
  - `uv run --with pytest python -m pytest tests/test_hotwords.py` passed: 6 tests.
  - Parser check confirmed `达乐通` appears in the words list and not the replacements map for both `hotwords.example.txt` and `~/.config/whiscode/hotwords.txt`.
  - `git diff --check` passed.
- VC-001 passed.
- VC-002 passed.
- Implementation commit: `46dd6d6` (`Add Daletong hotword`).
- Immediate next step: commit checkpoint bookkeeping, then close out to local `main`.
