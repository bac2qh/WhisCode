# Low Mic Gain Handling

## Closeout

- Final status: implemented.
- Related checkpoint: `.agents/checkpoints/2026-05-21-low-mic-gain-checkpoints.md`.
- Implementation commits: `6fb4556` (normalization implementation, tests, docs, memory), `c9f826d` (checkpoint hash update).
- Merge commit: none; local `main` fast-forwarded to `c9f826d`.
- Verification performed: `uv run --with pytest pytest tests/test_recorder.py tests/test_main_cli.py tests/test_handsfree.py`, `uv run --with pytest pytest`, and `git diff --check`.
- Worktree and branch cleanup: removed `.agents/worktrees/fix-low-mic-gain`; deleted local branch `fix-low-mic-gain`.
- Summary: quiet hotkey and hands-free recordings now receive bounded pre-transcription gain normalization without changing raw hands-free detector audio. Telemetry emits bounded before/after level metadata only when gain is applied.

## Goal

Investigate why microphone input sounds/appears very low and add a conservative app-side gain correction so quiet captures are easier for transcription without changing wake/end detector calibration.

## Scope

- Add shared audio peak/RMS measurement and normalization helpers for recorded speech.
- Apply normalization after hotkey recording stops and after hands-free capture completes, before Whisper transcription.
- Keep raw microphone audio for hands-free wake/end/command detection and reference enrollment preprocessing so existing detector thresholds remain meaningful.
- Add focused tests for quiet audio boost, clipping limits, silence handling, and integration with recorder/hands-free output.
- Update durable docs/memory if the behavior change is implemented.

## Telemetry And Diagnostics

What can fail or become ambiguous:
- Quiet captures may still be too low if they are near silence or mostly noise.
- Aggressive boosting could clip speech or amplify background noise.
- Operators need to know whether a transcription used app-side gain correction without recording raw audio or transcript text.

Signals:
- Emit bounded `audio.normalization_applied` telemetry before transcription when gain changes the audio.
- Include mode/source, gain, input/output RMS, input/output peak, audio sample count, and audio duration rounded to bounded numeric values.
- Do not include raw audio, transcript text, prompts, hotwords, device names, or user content.

Verification:
- Unit tests for normalization math and call sites.
- Run targeted recorder/hands-free/main tests, then the full test suite if practical.
