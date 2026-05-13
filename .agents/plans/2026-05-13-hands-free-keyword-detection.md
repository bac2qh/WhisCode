# Hands-Free Keyword Trigger V1

## Summary
- Add optional hands-free mode that replaces Right Shift as the primary trigger while keeping Right Shift as a fallback.
- Use `local-wake` for local, speaker-dependent start/end phrase detection from reference samples.
- Keep Whisper only for the final captured utterance, not for wake/end detection.
- Add an enrollment/import command so Voice Memo `.m4a` samples can be converted into 16 kHz mono WAV reference folders.

## Key Changes
- Create branch/worktree `.agents/worktrees/hands-free-keyword-detection` from current local `main`, then save the plan/checkpoint there before implementation.
- Add `local-wake==0.1.2` as the V1 detector dependency.
- Add `whiscode-enroll` console script:
  - `whiscode-enroll wake sample1.m4a sample2.m4a sample3.m4a`
  - `whiscode-enroll end sample1.m4a sample2.m4a sample3.m4a`
  - Convert inputs with macOS `afconvert` into `~/.config/whiscode/wake/wake/` and `~/.config/whiscode/wake/end/`.
- Add `uv run whiscode --hands-free` mode:
  - Defaults: wake refs at `~/.config/whiscode/wake/wake`, end refs at `~/.config/whiscode/wake/end`, threshold `0.1`, 2.0s detector window, 0.25s slide.
  - `IDLE`: always-open mic feeds only the wake detector.
  - `RECORDING`: captures audio and feeds the end detector.
  - `TRANSCRIBING`: ignores new voice triggers until the current transcription finishes.
- Exclude trigger phrases from final transcription:
  - Start capturing after wake detection.
  - Keep a short pending tail while recording and discard it when the end phrase is detected, so the end phrase is not sent to Whisper.
- Keep current hotkey mode unchanged unless `--hands-free` is set; in hands-free mode, Right Shift manually starts/stops using the same state transitions.

## Safety And Diagnostics
- Add bounded terminal/debug events for `handsfree.started`, `wake.detected`, `end.detected`, `timeout`, `detector.error`, and sample-folder validation.
- Do not log raw audio, transcripts before normal transcription output, file contents, prompts, or high-cardinality audio metadata.
- Add `--hands-free-debug` to print detector distances for tuning thresholds.
- Add `--hands-free-max-seconds 180` default safety stop; on timeout, stop and transcribe captured audio. Allow `0` to disable.

## Test Plan
- Unit-test enrollment conversion:
  - `.m4a` inputs call `afconvert` with 16 kHz mono WAV output.
  - missing input files and too-few samples produce clear errors.
- Unit-test hands-free state transitions with fake detectors and fake audio frames:
  - wake starts capture.
  - end stops capture and dispatches audio.
  - end phrase tail is excluded.
  - hotkey fallback still starts/stops in hands-free mode.
  - timeout stops recording.
- Unit-test CLI parsing for default mode, `--hands-free`, detector paths/thresholds, and `whiscode-enroll`.
- Verification commands:
  - `uv run --with pytest python -m pytest`
  - `uv run whiscode --help`
  - `uv run whiscode-enroll --help`
  - `uv run --with local-wake python -c "import lwake"`

## Assumptions
- V1 uses Voice Memo recordings imported through `whiscode-enroll`; it does not need an in-app sample recorder yet.
- Start/end phrase words are defined by the user's reference recordings, not by text strings in the app.
- `local-wake` is selected because its docs describe custom phrases from 3-4 user reference recordings without model training; Porcupine and LiveKit/OpenWakeWord remain V2 alternatives if V1 accuracy is insufficient.
