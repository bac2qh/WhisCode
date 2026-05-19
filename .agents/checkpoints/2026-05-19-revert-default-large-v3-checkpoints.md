# Revert Default Whisper Model To Large V3 Checkpoints

## 2026-05-19

### Started

- Created task worktree `.agents/worktrees/revert-default-large-v3` on branch `revert-default-large-v3`.
- Reviewed recent history and found commit `108fcee` changed the CLI default from `mlx-community/whisper-large-v3-mlx` to `mlx-community/whisper-large-v3-turbo` while also adding unrelated notification behavior.
- Decision: restore only the model default and preserve unrelated changes. Keep explicit turbo fallback behavior unless it conflicts with the restored default.

### Immediate Next Step

- Update the CLI default, add a regression test for the default model, run focused verification, then update memory and commit.

### Implementation

- Restored `parse_args()` default `--model` to `mlx-community/whisper-large-v3-mlx`.
- Added a default-argument regression assertion in `tests/test_main_cli.py`.
- Kept explicit turbo processor fallback behavior so users who pass `--model mlx-community/whisper-large-v3-turbo` still get the load-time processor repair.
- Implementation commit: `c8c200d`.

### Verification

- `uv run --with pytest pytest tests/test_main_cli.py`: 15 passed.
- `uv run --with pytest pytest`: 133 passed.

### Immediate Next Step

- Commit this checkpoint update, then run closeout by merging the task branch back to local `main`.
