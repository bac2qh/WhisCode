# Optional llama.cpp ASR Backend Checkpoints

## 2026-05-24 - Initial checkpoint

Done:
- Created task worktree at `.agents/worktrees/llama-cpp-asr-backend` on branch `feature/llama-cpp-asr-backend`.
- Saved the approved implementation plan in `.agents/plans/2026-05-24-llama-cpp-asr-backend.md`.
- Confirmed existing project memory index and model-loading history before implementation.

Immediate next step:
- Implement the backend boundary and optional llama.cpp mode while preserving the default MLX Whisper path.

Key decisions and reasoning:
- Default `uv run whiscode` must remain backward-compatible and keep MLX Whisper.
- llama.cpp/Qwen3-ASR is opt-in via `--asr-backend llama-cpp`.
- Hands-free mode stays intact; only the final transcription backend changes.
- Use source-built llama.cpp and local LM Studio Qwen3-ASR GGUF files; no package-manager llama.cpp dependency.
- Telemetry must expose backend/server/transcription operational status without raw audio, transcript text, full payloads, or secrets.

Verification:
- No implementation verification yet; checkpoint created before source edits as required.

Backtracks:
- Earlier plan considered making llama.cpp the new default; user clarified it must remain optional for compatibility.

## 2026-05-24 - Implementation checkpoint

Done:
- Added `--asr-backend {mlx-whisper,llama-cpp}` with `mlx-whisper` as the default.
- Added the optional llama.cpp/Qwen3-ASR backend with server health checks, source-built server autostart, child-process cleanup, WAV serialization, OpenAI-compatible audio request construction, Qwen ASR response parsing, and bounded telemetry.
- Preserved the existing hotkey and hands-free recording flows by changing only the transcription call site to use the selected backend.
- Documented optional llama.cpp mode in README and `wiki/pages/asr-backends.md`.
- Rebuilt llama.cpp from source at `/Users/xin/Documents/repos/llama.cpp`, producing `build/bin/llama-server` version `9307 (549b9d843)`.
- Confirmed the Qwen3-ASR LM Studio files are present and used for the smoke path.

Implementation commit:
- `ab3e2fe` (`Add optional llama.cpp ASR backend`).

Immediate next step:
- Commit this checkpoint hash update, then run closeout into local `main`.

Key decisions and reasoning:
- Default install and `uv run whiscode` stay MLX Whisper to avoid imposing llama.cpp or Qwen3-ASR on existing users.
- llama.cpp mode binds to `127.0.0.1:8091` by default to avoid colliding with the existing local LLM/Pi setup on `8080`.
- The backend sends prompt/hotword context to Qwen3-ASR as system context but does not include raw audio, transcript text, or full payloads in telemetry.
- The live smoke used silence rather than dictated speech to validate server startup, multimodal request handling, parser behavior, and cleanup without requiring interactive microphone input.

Verification:
- `uv run --with pytest pytest tests/test_llama_cpp_asr.py tests/test_main_cli.py tests/test_transcriber.py` passed: 37 tests.
- `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release` passed in `/Users/xin/Documents/repos/llama.cpp`.
- `cmake --build build --config Release -j 8` passed in `/Users/xin/Documents/repos/llama.cpp`.
- `/Users/xin/Documents/repos/llama.cpp/build/bin/llama-server --version` reported `version: 9307 (549b9d843)`.
- Source-built `llama-server --help` includes `--mmproj`, `--alias`, `--jinja`, and `-fa`.
- Live backend smoke with one second of silence started the llama.cpp server, returned `TRANSCRIPT ''`, and cleaned up the child process.
- `uv run --with pytest pytest` passed: 164 tests.
- `uv run python -m compileall whiscode` passed.
- Confirmed no llama.cpp server remains running on port `8091` after the smoke.

Backtracks:
- None after implementation began.

## 2026-05-24 - Closeout checkpoint

Done:
- Fast-forward merged `feature/llama-cpp-asr-backend` into local `main`.
- Removed task worktree `.agents/worktrees/llama-cpp-asr-backend`.
- Deleted local branch `feature/llama-cpp-asr-backend`.
- Added the closeout note to the plan and archived it under `.agents/plans/archive/`.

Implementation commits:
- `ab3e2fe` (`Add optional llama.cpp ASR backend`).
- `1ccde1a` (`Record llama.cpp ASR implementation checkpoint`).

Merge:
- Fast-forward to `1ccde1a`; no merge commit was created.

Immediate next step:
- None. Work is implemented and closed out.

Key decisions and reasoning:
- Closed out with a fast-forward merge because local `main` had not advanced independently.
- No repo main-branch lock helper exists; closeout was performed directly because no concurrent local closeout activity was observed.

Verification:
- Reused implementation verification recorded above.
- Confirmed worktree and branch cleanup completed.

Backtracks:
- None.
