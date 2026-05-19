# Closeout

- Final status: implemented.
- Related checkpoint file: `.agents/checkpoints/2026-05-19-revert-default-large-v3-checkpoints.md`.
- Implementation commits: `c8c200d`, `1614809`.
- Merge commit: none, fast-forwarded local `main` from `604e5ec` to `1614809`.
- Verification performed: `uv run --with pytest pytest tests/test_main_cli.py` (15 passed) and `uv run --with pytest pytest` (133 passed).
- Worktree and branch cleanup result: removed `.agents/worktrees/revert-default-large-v3` and deleted local branch `revert-default-large-v3`.
- Summary: restored the default Whisper model to `mlx-community/whisper-large-v3-mlx`, added a regression assertion, and kept explicit turbo fallback support for users who opt into the turbo model.

# Revert Default Whisper Model To Large V3

## Goal

Restore the default WhisCode Whisper model from `mlx-community/whisper-large-v3-turbo` to the large-v3 MLX model that the installer already downloads.

## Scope

- Change the CLI `--model` default back to `mlx-community/whisper-large-v3-mlx`.
- Add or update focused tests so the default model does not drift back to turbo unnoticed.
- Keep unrelated recent behavior, including recording notifications and explicit turbo processor fallback support, unless verification shows it conflicts with the restored default.
- Update project memory/checkpoints with the durable model-default decision.

## Telemetry And Diagnostics

No new telemetry is required for this default-only change. Existing `model.load_started`, `model.load_completed`, and `model.load_failed` signals still expose model loading outcomes, and the explicit turbo fallback telemetry remains available when users opt into the turbo model.

## Verification

- Run the focused CLI tests that cover argument defaults and model processor behavior.
- Run the broader test suite if the focused tests pass and the local environment has required dependencies.
