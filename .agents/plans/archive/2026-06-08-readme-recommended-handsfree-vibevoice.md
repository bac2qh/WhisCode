# README Recommended Hands-Free VibeVoice Update

## Closeout Note

- Final status: complete.
- Related checkpoint: `.agents/checkpoints/2026-06-08-readme-recommended-handsfree-vibevoice-checkpoints.md`.
- Implementation commits: `c0c9f54` (`Document recommended hands-free VibeVoice workflow`) and `9952e0b` (`Record README workflow checkpoint commit`).
- Merge commit hash: none expected; the task branch is prepared for a fast-forward merge into local `main`.
- Verification performed: `git diff --check`; exact recommended-command count in `README.md`; retired chunk-flag README search; `mlx-whisper` default row search; opt-in/recommended VibeVoice wording search.
- Worktree/branch cleanup result: pending the final non-interactive mutex closeout command. The interactive lock-shell approach was rejected by the escalation reviewer as too broad, so cleanup is recorded here as pending and the final command result is reported in chat after it runs.
- Shipped summary: README Usage now recommends `uv run whiscode --hands-free --asr-backend mlx-vibevoice` for regular dictation, explains wake/end and Send Chunk behavior, and keeps hands-free mode and MLX VibeVoice documented as opt-in rather than CLI defaults.

## Summary

Update `README.md` to make the current recommended daily-driver command clear:

```bash
uv run whiscode --hands-free --asr-backend mlx-vibevoice
```

Describe this as the best current way to run WhisCode for regular dictation: `uv` manages the app environment, hands-free mode keeps interaction natural, and `mlx-vibevoice` is the preferred local VibeVoice ASR backend.

## Scope

- Add a short "Recommended daily workflow" section near the top of Usage, before the plain `uv run whiscode` hotkey flow.
- Explain the behavior plainly:
  - wake phrase starts recording;
  - wake phrase during recording sends a chunk;
  - end phrase finishes the message;
  - Right Shift remains available as fallback;
  - queued chunks/transcriptions type in order.
- Reframe Send Chunk as the preferred mechanism for long messages because it reduces per-transcription latency, keeps the queue moving, and creates a useful pause for breathing, recollection, and organizing the next thought.
- Keep existing defaults accurate: do not claim `mlx-vibevoice` or hands-free are CLI defaults; describe them as the recommended current workflow.
- Leave public CLI/API/options unchanged.

## Telemetry / Debuggability

Not applicable. This is a documentation-only change and does not alter runtime behavior, logs, telemetry events, backend calls, typed text, storage, or provider payload handling.

## Validation Contract

- `VC-001 critical`: README shows the recommended command exactly as `uv run whiscode --hands-free --asr-backend mlx-vibevoice`.
- `VC-002 critical`: README accurately describes hands-free wake/end behavior and wake-as-Send-Chunk behavior without inventing new flags.
- `VC-003 important`: README explains Send Chunk as recommended for long messages due to faster chunked transcription and as a natural pause/breather.
- `VC-004 important`: Existing backend docs still state `mlx-whisper` is the default and `mlx-vibevoice` is the preferred VibeVoice backend, not the hard default.
- `VC-005 advisory`: No transcript, audio, prompt, hotword, provider payload, typed text, secrets, or credentials are added to docs.

## Test Plan

- Run `git diff --check`.
- Run a targeted README sanity search:
  - verify recommended command appears once in the new workflow section;
  - verify no removed/retired chunk flags are introduced;
  - verify `mlx-whisper` default wording remains accurate.
- No pytest required unless implementation touches code, config, or CLI behavior.

## Assumptions

- "UV with code" means running WhisCode through `uv`, specifically `uv run whiscode`.
- "AISR backend" means the ASR backend flag, specifically `--asr-backend mlx-vibevoice`.
- This is a documentation-only update to README, not a change to runtime defaults.
