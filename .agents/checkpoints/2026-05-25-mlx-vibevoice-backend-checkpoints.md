# MLX VibeVoice Backend Checkpoints

## 2026-05-25 Start
- Saved the implementation plan before product edits.
- Branch/worktree: `feature/mlx-vibevoice-backend` at `.agents/worktrees/mlx-vibevoice-backend`.
- Immediate next step: implement the in-process MLX VibeVoice backend and wire it into the app and benchmark CLIs.
- Key decisions:
  - Keep `mlx-whisper` as the default backend.
  - Add `mlx-vibevoice` as a separate backend because VibeVoice uses MLX-Audio with different generation parameters and structured output.
  - Default VibeVoice model path to `~/Documents/models/mlx-community/VibeVoice-ASR-8bit`, overridable with `WHISCODE_MLX_VIBEVOICE_MODEL` or `--mlx-vibevoice-model`.
  - Preserve the existing hotwords file format and pass hotwords via VibeVoice `context`.
- Verification: pending.

## 2026-05-25 Implementation
- Added `whiscode/mlx_vibevoice_asr.py` with an in-process MLX-Audio VibeVoice backend, default model path resolution, context builder, segment/raw-output transcript extraction, and bounded telemetry.
- Wired `--asr-backend mlx-vibevoice` into `whiscode` and `whiscode-benchmark-asr` with `--mlx-vibevoice-model`, `--mlx-vibevoice-max-tokens`, `--mlx-vibevoice-temperature`, and `--mlx-vibevoice-prefill-step-size`.
- Updated README and ASR backend wiki docs with the default 8-bit model path, BF16 override, hotword/context behavior, and CrispASR prompt limitation.
- Added tests for backend behavior, CLI options, benchmark parsing, telemetry safety, and VibeVoice output normalization.
- Verification passed:
  - `uv run --with pytest pytest tests/test_mlx_vibevoice_asr.py tests/test_main_cli.py tests/test_benchmark_asr.py`
  - `uv run --with pytest pytest`
  - `uv run python -m compileall whiscode`
  - `uv run whiscode --help`
- Implementation commit: `f412d41` (`Add MLX VibeVoice ASR backend`).
- Immediate next step: commit this checkpoint update and close out to local `main`.
