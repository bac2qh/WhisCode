# CrispASR VibeVoice Backend Checkpoints

## 2026-05-24 Start
- Main project root: `/Users/xin/Documents/repos/WhisCode`.
- Task worktree: `/Users/xin/Documents/repos/WhisCode/.agents/worktrees/crispasr-vibevoice`.
- Branch: `feature/crispasr-vibevoice`.
- User-approved direction: integrate source-built sibling `../CrispASR` as an optional WhisCode ASR backend for VibeVoice ASR GGUF, with MLX Whisper remaining default and llama.cpp/Qwen unchanged.
- Key implementation decision: use CrispASR server mode and OpenAI-compatible `/v1/audio/transcriptions`; keep the model warm for the WhisCode process and terminate only a child process started by WhisCode.
- Telemetry decision: add bounded backend lifecycle and transcription diagnostics without raw audio, prompt, hotwords, transcript text, full request payloads, secrets, or full model paths.
- Build discovery: in the current CrispASR checkout, `cmake --build build --target crispasr` builds the library target, while the CLI executable at `build/bin/crispasr` is produced by `cmake --build build --target crispasr-cli`. Plan/docs were corrected to use `crispasr-cli`.
- Immediate next step: implement the backend, CLI wiring, docs, memory, benchmark command, and tests.
- Verification: pending.
- Implementation commits: pending.
