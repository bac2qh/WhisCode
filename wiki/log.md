# WhisCode Maintenance Log

## 2026-05-13
- Added hands-free keyword detection documentation for local start/end phrase triggering.
- Updated hands-free documentation for guided Python microphone enrollment.

## 2026-05-14
- Documented local JSONL telemetry for hands-free diagnostics and guided enrollment.
- Documented hands-free detector speech-energy gating for suppressing silence and partial-window false positives.
- Documented stricter end-threshold tuning for hands-free mode.
- Documented the floating recording overlay with stopwatch and live microphone levels.
- Documented stricter wake defaults and wake confirmation tuning to reduce hands-free false starts from incidental sound.
- Documented VAD-trimmed hands-free enrollment and the local calibration report for threshold tuning.
- Documented trained hands-free key command slots for Page Up, Page Down, and Enter.
- Documented the guided enrollment recording overlay replacing enrollment notification banners.
- Documented recording overlay helper crash diagnostics.
- Documented padding VAD-trimmed reference samples to the detector window length.

## 2026-05-15
- Documented the shared 10-minute recording duration cap and clarified PortAudio overflow telemetry.
- Documented Shift+Enter and Shift+Tab trained hands-free command slots.
- Documented the hands-free audio queue that decouples microphone capture from detector processing.
- Documented Tab, Arrow Up, and Arrow Down trained hands-free command slots.
- Documented overlay helper EOF shutdown to prevent orphaned floating panels.
- Documented the transcription progress state in the floating overlay.

## 2026-05-21
- Documented bounded pre-transcription gain normalization for quiet microphone recordings and its telemetry.
- Removed bounded pre-transcription gain normalization documentation after reverting the feature; flat overlay bars point to raw input capture or device configuration instead.
- Documented overlay helper parent monitoring and orphan cleanup.

## 2026-05-24
- Documented the optional llama.cpp/Qwen3-ASR backend and clarified that MLX Whisper remains the default compatibility backend.
- Documented the optional CrispASR/VibeVoice GGUF backend and benchmark command for local ASR latency comparison.
- Documented default local runtime telemetry and bounded CrispASR malformed response shape diagnostics.
- Documented the macOS telemetry default path under `~/Library/Logs/WhisCode/events.jsonl`.

## 2026-05-25
- Documented that the current CrispASR/VibeVoice warm-server transcription path cannot expose concrete in-flight progress to the recording overlay.
- Documented the optional MLX VibeVoice backend, its default local 8-bit model path, BF16 override, and hotword/context behavior.
- Documented that CrispASR/VibeVoice is now a legacy compatibility path and MLX VibeVoice is the recommended local VibeVoice backend.

## 2026-05-26
- Documented the MLX VibeVoice-only external NAS transcription queue, inbox/outbox contract, supported formats, ffmpeg-backed decode requirement, and two-engine manual-priority behavior.
- Documented native SMB URL support for the external NAS transcription queue, including `op run` credential environment variables and unmounted NAS operation.

## 2026-05-27
- Added repo-local 1Password env pointer file guidance for SMB NAS launch config. The tracked template is `.env.1password.whiscode-smb.example`; the real `.env.1password.whiscode-smb` remains ignored and is used with `op run --env-file`.

## 2026-06-06
- Documented hands-free end-tail auto-inference from enrolled end-phrase WAV active spans, the explicit `--hands-free-tail-seconds` override, the `1.0` second fallback, and bounded tail-resolution telemetry.
- Documented that recording overlay orphan-helper scanning tolerates malformed process-table command bytes while keeping helper filtering unchanged.

## 2026-06-08
- Documented the extra hands-free end-detection lag buffer, its `1.0` second default, and `--hands-free-tail-extra-seconds 0` as the previous base-only trim behavior.
- Documented Send Chunk support: the Right Option + Right Shift recording chord, optional hands-free chunk phrase, chunk enrollment/import paths, chunk-specific tail trimming, blank-line transcript suffix, and bounded telemetry.
- Documented that hands-free Send Chunk now reuses the wake phrase during recording, with tail trimming inferred from wake references instead of a separate chunk phrase.

## 2026-06-09
- Documented deferred Send Chunk delivery: chunk transcripts print to stdout as they finish, but clipboard copy/paste waits until the final stop/end/timeout flushes the in-memory batch.
- Documented idle-only `scroll-up` and `scroll-down` hands-free command slots, including guided/manual enrollment, `commands.ini` enablement, scroll direction semantics, and bounded scroll injection telemetry.
