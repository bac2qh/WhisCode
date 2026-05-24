# CrispASR VibeVoice Backend Checkpoints

## 2026-05-24 Start
- Main project root: `/Users/xin/Documents/repos/WhisCode`.
- Task worktree: `/Users/xin/Documents/repos/WhisCode/.agents/worktrees/crispasr-vibevoice`.
- Branch: `feature/crispasr-vibevoice`.
- User-approved direction: integrate source-built sibling `../CrispASR` as an optional WhisCode ASR backend for VibeVoice ASR GGUF, with MLX Whisper remaining default and llama.cpp/Qwen unchanged.
- Key implementation decision: use CrispASR server mode and OpenAI-compatible `/v1/audio/transcriptions`; keep the model warm for the WhisCode process and terminate only a child process started by WhisCode.
- Telemetry decision: add bounded backend lifecycle and transcription diagnostics without raw audio, prompt, hotwords, transcript text, full request payloads, secrets, or full model paths.
- Build discovery: in the current CrispASR checkout, `cmake --build build --target crispasr` builds the library target, while the CLI executable at `build/bin/crispasr` is produced by `cmake --build build --target crispasr-cli`. Plan/docs were corrected to use `crispasr-cli`.
- Implementation commit: `002d070` (`Add optional CrispASR ASR backend`).
- Completed:
  - Added optional `--asr-backend crispasr` with source-built CrispASR defaults, env default support, warm-server ownership, multipart `/v1/audio/transcriptions`, and coding prompt reuse.
  - Added `whiscode-benchmark-asr` for file-based backend latency checks.
  - Updated README, wiki, model-loading memory, and tests.
- Verification:
  - `uv run --with pytest pytest tests/test_crispasr_asr.py tests/test_main_cli.py` passed: 30 tests.
  - `uv run python -m compileall whiscode` passed.
  - `uv run --with pytest pytest` passed: 177 tests.
  - `uv run whiscode --help` passed and shows `crispasr` options.
  - `uv run whiscode-benchmark-asr --help` passed.
  - CrispASR source build passed in `/Users/xin/Documents/repos/CrispASR`: `cmake -B build -DCMAKE_BUILD_TYPE=Release -DGGML_METAL=ON` and `cmake --build build --target crispasr-cli`.
  - `/Users/xin/Documents/repos/CrispASR/build/bin/crispasr --list-backends` passed and lists `vibevoice`.
  - Live VibeVoice transcription smoke was not run because `vibevoice-asr-f16.gguf` was not found under `/Users/xin/Documents`.
- Immediate next step: commit this checkpoint update, then close out by merging into local `main`, archiving the plan, and cleaning the task worktree/branch.
