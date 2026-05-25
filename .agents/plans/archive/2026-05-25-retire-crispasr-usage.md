## Closeout
- Final status: implemented.
- Related checkpoint file: .agents/checkpoints/2026-05-25-retire-crispasr-usage-checkpoints.md.
- Implementation commits: be057b2, 5b034b2, 5f46455.
- Merge commit: none; local main was fast-forwarded.
- Verification performed: uv run --with pytest pytest tests/test_main_cli.py tests/test_benchmark_asr.py; uv run --with pytest pytest; uv run python -m compileall whiscode; fixed mutex verified with bash -x .agents/scripts/main-branch-lock.sh run --owner test --timeout-seconds 2 -- true.
- Worktree and branch cleanup result: removed .agents/worktrees/retire-crispasr-usage and deleted feature/retire-crispasr-usage.
- Summary: Retired CrispASR/VibeVoice from recommended use, preserved it as a legacy GGUF compatibility backend, made MLX VibeVoice the recommended local VibeVoice path, and repaired the main-branch lock helper discovered during closeout.

# Retire CrispASR Usage In Favor Of MLX VibeVoice

## Summary
Retire CrispASR as the recommended VibeVoice path now that MLX VibeVoice is noticeably faster locally. Keep the `crispasr` backend available as a legacy compatibility option, but move docs and CLI wording toward `mlx-vibevoice`.

## Key Changes
- Mark `crispasr` as legacy/deprecated in CLI help and runtime startup output.
- Update README and wiki docs so `mlx-vibevoice` is the recommended VibeVoice backend.
- Move CrispASR documentation out of the main recommended path and frame it as legacy GGUF compatibility only.
- Keep existing CrispASR code/tests intact to avoid breaking old local setups.

## Telemetry / Debuggability
- No new telemetry events are needed. Existing `asr.backend_selected` and CrispASR telemetry remain sufficient to identify legacy backend usage.
- Do not change telemetry payload content.

## Tests
- Update CLI tests for legacy help wording if needed.
- Run `uv run --with pytest pytest tests/test_main_cli.py tests/test_benchmark_asr.py`.
- Run `uv run --with pytest pytest`.

## Assumptions
- "Retire usage" means deprecate and de-emphasize CrispASR rather than deleting backend code in this pass.
- Do not push; commit locally only.
