# Recording Duration Limit Checkpoints

## 2026-05-15 Initial
- Done: Created the task worktree `recording-duration-limit` from local `main` at `f2b1ea7`.
- Immediate next step: Implement the shared max recording duration CLI and recorder cap.
- Decisions: Use a shared default of `600.0` seconds; keep `--hands-free-max-seconds` as a compatibility override; auto-finalize capped manual recordings.
- Verification: Not yet run.

## 2026-05-15 Implementation
- Done: Implemented in commit `140a21d` (`Bound recording duration by default`).
- Immediate next step: Close out by merging the task branch back into local `main`, then remove the task worktree and branch.
- Decisions: The preferred CLI is `--max-recording-seconds`; legacy `--hands-free-max-seconds` remains a hands-free-specific override. Manual recording uses a callback-safe queue notification so the audio callback only caps chunks and signals the main loop, while stream shutdown and transcription stay in normal app control flow.
- Verification:
  - `uv run pytest tests/test_recorder.py tests/test_main_cli.py tests/test_handsfree.py` failed during collection because the repo's known global `pytest` path could not import `whiscode`.
  - `uv run --with pytest python -m pytest tests/test_recorder.py tests/test_main_cli.py tests/test_handsfree.py` passed with 28 tests.
  - `uv run --with pytest python -m pytest` passed with 114 tests.
  - `uv run whiscode --help` passed and showed `--max-recording-seconds`.
  - `git diff --check` passed.
