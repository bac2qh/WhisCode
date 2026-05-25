# Default Telemetry And CrispASR Shape Diagnostics Checkpoints

## 2026-05-24 Start
- Main project root: `/Users/xin/Documents/repos/WhisCode`.
- Task worktree: `/Users/xin/Documents/repos/WhisCode/.agents/worktrees/default-telemetry-crispasr-shape`.
- Branch: `default-telemetry-crispasr-shape`.
- User context: after the VibeVoice chunk normalizer shipped, one recording failed with `CrispASR VibeVoice chunks were malformed`, while a short message later worked. This points to model-generated chunk-shape variance rather than a server-wide failure.
- Decision: enable local runtime telemetry by default and add bounded CrispASR response-shape diagnostics so future malformed chunk failures are explainable without recording transcript text or raw provider payloads.
- Telemetry boundaries: do not log raw audio, transcript text, prompts, hotwords, chunk `Content`, provider payloads, secrets, or full paths.
- Implemented:
  - `uv run whiscode` now enables local JSONL telemetry by default unless `--no-telemetry` is passed.
  - Added `crispasr.response_shape_invalid` for malformed VibeVoice chunk output with bounded shape metadata only.
  - Updated README, wiki docs, wiki log, model-loading memory, and added a telemetry memory topic.
  - Added tests for default runtime telemetry, opt-out behavior, safe shape diagnostics, and backend wiring.
- Verification:
  - `uv run --with pytest pytest tests/test_crispasr_asr.py tests/test_main_cli.py tests/test_telemetry.py` passed: 45 tests.
  - `uv run python -m compileall whiscode` passed.
- Implementation commit: `7732529` (`Enable default runtime telemetry`).
- Checkpoint hash commit: `a711e51` (`Record default telemetry implementation checkpoint`).
- Closeout:
  - Merged into local `main` by fast-forward at `a711e51`; no merge commit was created.
  - Removed task worktree `.agents/worktrees/default-telemetry-crispasr-shape`.
  - Deleted local branch `default-telemetry-crispasr-shape`.
  - Left unrelated worktree `.agents/worktrees/env-llama-paths` untouched.
  - Archived the plan to `.agents/plans/archive/2026-05-24-default-telemetry-crispasr-shape.md`.
- Immediate next step: none for this plan.
