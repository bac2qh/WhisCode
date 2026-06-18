# CCAB Warm Short-Lane External Transcription

Date: 2026-06-18
Branch: ccab-warm-short-lane
Worktree: .agents/worktrees/ccab-warm-short-lane
CCAB branch: warm-whiscode-short-lane
CCAB worktree: /Users/xinding/openclaw/ccab/.agents/worktrees/warm-whiscode-short-lane
Status: active
Related checkpoint: ../checkpoints/2026-06-18-ccab-warm-short-lane-checkpoints.md

## Objective

Extend WhisCode so one tmux-managed external-only process can warm a single `mlx-whisper` model and serially process all CCAB short transcription inboxes under a configured root.

## Scope

- Add `--external-only` and reject it unless an external inbox or CCAB root is configured.
- Permit external intake with `--asr-backend mlx-whisper`.
- Add `--external-ccab-root ROOT` discovery for `<root>/*/workspace/transcription/short/{inbox,outbox}`.
- Preserve the existing single-inbox external path and VibeVoice behavior.
- Add tests for CLI validation, discovery, and serial multi-inbox processing through one fake warmed backend.

## Validation Contract

- VC-001 [critical] `mlx-whisper` model loading remains a one-time startup operation before external jobs are processed.
- VC-002 [critical] One process can watch multiple CCAB short inboxes and route each result to the same user's short outbox.
- VC-003 [critical] Concurrent arrivals are queued and transcribed serially with one warmed backend.
- VC-006 [important] `--external-only` supports tmux/manual operation without hotkey/manual recording requirements.

## Telemetry / Debuggability

Reuse existing external queue telemetry fields and keep them privacy-safe: storage scheme, file ID, extension, size, backend, model label, duration, status, and queue depth only. Do not log transcript text, raw audio, full user paths, credentials, provider payloads, or media bytes.

## Verification

- Focused WhisCode unit tests.
- `git diff --check`.
- Live exact-model smoke test only if operator/time/resources permit.
