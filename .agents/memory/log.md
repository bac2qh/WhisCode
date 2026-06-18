# Memory Log

## 2026-05-13
- Added recording status notification memory after replacing recording start/stop sounds with silent macOS banners.
- Added hands-free keyword detection memory after implementing local wake/end phrase triggering and Voice Memo sample import.
- Added guided hands-free enrollment memory after implementing Python microphone recording for wake/end reference samples.

## 2026-05-14
- Added hands-free telemetry memory after implementing local JSONL diagnostics for repeated hands-free trigger loops.
- Added signal-safe telemetry shutdown memory after fixing the Ctrl+C handler regression.
- Added hands-free speech-energy gate memory after preventing silence and partial-window false positives from reaching the keyword detector.
- Added hands-free end-threshold memory after splitting wake and end detection thresholds to reduce premature stop detections.
- Added repository hygiene memory after ignoring local `.agents` runtime/worktree/lock state while keeping durable agent project state tracked.
- Added recording overlay memory after replacing normal recording banners with a floating stopwatch and live microphone-level UI.
- Added hands-free wake confirmation memory after tightening wake defaults to reduce false starts from incidental sound.
- Added hands-free enrollment calibration memory after trimming reference samples with local VAD and adding a local distance report command.
- Added hands-free reference padding memory after fixing short VAD-trimmed references that no longer matched the runtime detector window.

## 2026-05-15
- Added hands-free key command memory after implementing trained Page Up, Page Down, and Enter voice command slots.
- Added enrollment overlay memory after replacing guided enrollment notification banners with the floating recording overlay.
- Added recording overlay crash memory after fixing AppKit timer text drawing and adding helper crash diagnostics.
- Added shared recording duration cap memory after bounding manual and hands-free recording length by default.
- Added shift key command memory after extending trained hands-free commands with Shift+Enter and Shift+Tab slots.
- Added hands-free audio queue memory after decoupling microphone capture from detector processing to reduce PortAudio input overflows.
- Added tab and arrow key command memory after extending trained hands-free commands with Tab, Arrow Up, and Arrow Down slots.
- Added overlay helper lifecycle memory after fixing orphaned floating panels on parent-process exit.
- Added configurable hands-free command memory after implementing the command allowlist config for runtime, enrollment, and calibration.

## 2026-05-16
- Added v2 beta memory after documenting `v2.0.0-beta.1` as the hands-free beta and aligning package metadata to `2.0.0b1`.

## 2026-05-19
- Added model-loading memory after fixing the default MLX Whisper model's missing Hugging Face processor fallback.
- Updated model-loading memory after restoring the CLI default to `mlx-community/whisper-large-v3-mlx` while retaining explicit turbo fallback support.

## 2026-05-20
- Updated model-loading memory after adding the processor fallback mapping for the current `mlx-community/whisper-large-v3-mlx` default.
- Updated `recording-status-notifications.md` with the transcription progress overlay behavior and its bounded tqdm progress source.

## 2026-05-21
- Added audio capture and normalization memory after implementing bounded pre-transcription gain correction for quiet microphone input.
- Updated audio capture memory after reverting pre-transcription normalization; flat overlay bars indicate the issue is upstream of transcription.
- Updated recording status notification memory after adding overlay helper parent monitoring and orphan cleanup.

## 2026-05-24
- Added optional llama.cpp/Qwen3-ASR ASR backend memory: `mlx-whisper` remains the default, while `--asr-backend llama-cpp` uses a warm local source-built `llama-server` and preserves the surrounding WhisCode app flow.
- Added optional CrispASR/VibeVoice ASR backend memory: `mlx-whisper` remains the default, while `--asr-backend crispasr` uses a warm source-built CrispASR server and the benchmark command compares backend latency on WAV files.
- Updated CrispASR/VibeVoice memory after normalizing native and stringified chunk lists into user-visible transcript text by joining non-empty `Content` values.
- Updated repository hygiene memory after adding the standard local `main` closeout mutex helper.
- Added telemetry memory after enabling local runtime telemetry by default and adding bounded CrispASR malformed response shape diagnostics.
- Updated telemetry memory after moving the default telemetry file from `~/.config` to `~/Library/Logs/WhisCode/events.jsonl` for macOS log placement.
- Verified VibeVoice-ASR output shape against Microsoft/Hugging Face docs and Transformers source: parsed output is segment dictionaries with `Start`, `End`, `Speaker`, and `Content`; raw decoded output can be `assistant`-prefixed; transcription-only output joins `Content` values with spaces.
- Added durable memory that malformed CrispASR/VibeVoice chunk output now writes original provider response bodies to local-only `crispasr-raw-responses.jsonl` for debugging after explicit user acceptance.
- Added VibeVoice Q4 GGUF tradeoff memory after downloading and benchmarking `vibevoice-asr-q4_k.gguf`: Q4 is much smaller and can be faster on longer samples, but local short-dictation latency was not meaningfully better than warm F16.
- Added recording queue and stacked overlay memory after allowing hotkey and hands-free recordings to continue while prior audio transcribes, with last-five typed transcript recovery in `/tmp/whiscode-last-transcripts.txt`.
- Updated recording and telemetry memory after replacing the `/tmp` transcript recovery file with copy-friendly stdout transcript blocks.

## 2026-05-25
- Documented the CrispASR/VibeVoice progress limitation in project memory: WhisCode's current warm-server transcription path is blocking and cannot feed concrete overlay progress until CrispASR exposes progress through a compatible API.
- Added MLX VibeVoice backend memory after implementing `--asr-backend mlx-vibevoice`, defaulting to the local 8-bit MLX model and passing existing hotwords through VibeVoice context.
- Added telemetry memory for bounded MLX VibeVoice model-load and transcription events.
- Updated model-loading memory after retiring CrispASR/VibeVoice from recommended use and keeping it only as a legacy GGUF compatibility backend.

## 2026-05-26
- Added external transcription queue memory after implementing the MLX VibeVoice-only NAS inbox/outbox watcher and two-engine manual-priority behavior.
- Updated repository hygiene memory after replacing the main-branch closeout mutex helper with the Nix-style `run`/`status` helper and explicit lock-create failure diagnostics.
- Updated external transcription queue memory after adding native SMB URL support for unmounted NAS inbox/outbox paths with credentials supplied by `op run` environment variables.

## 2026-05-27
- Standardized the external SMB launch config on an ignored repo-local `.env.1password.whiscode-smb` pointer file copied from tracked `.env.1password.whiscode-smb.example`; values should be 1Password `op://...` references and not plaintext secrets or `~/.zshrc` exports.

## 2026-06-06
- Added hands-free tail inference memory after changing omitted `--hands-free-tail-seconds` to use the median active span from enrolled end reference WAVs, with explicit override and `1.0s` fallback behavior.
- Added telemetry memory for the bounded `handsfree.tail_seconds_resolved` setup event.
- Updated recording overlay memory after hardening orphan-helper process-table scanning against malformed non-helper command bytes without changing bounded cleanup telemetry.

## 2026-06-08
- Added hands-free tail extra-buffer memory after adding the default `1.0s` `--hands-free-tail-extra-seconds` detector-lag trim on top of inferred, explicit, or fallback base tails.
- Added Send Chunk memory after implementing the Right Option + Right Shift chunk chord, optional hands-free chunk phrase, chunk-specific tail trim, queue text suffix, enrollment support, and bounded telemetry.
- Updated hands-free Send Chunk memory after replacing the separate chunk phrase with wake phrase reuse while recording. Wake references now drive recording-time chunk detection, confirmations, and chunk-tail inference; existing chunk sample folders are ignored rather than removed.
- Updated recording overlay memory after fixing active recording level ticks while older stacked cards are transcribing.
- Updated hands-free README guidance memory after documenting `uv run whiscode --hands-free --asr-backend mlx-vibevoice` as the recommended daily workflow without changing CLI defaults.

## 2026-06-09
- Updated hands-free and telemetry memory after changing Send Chunk delivery to buffer successful chunk text in memory and paste once on final stop/end/timeout.
- Updated hands-free and telemetry memory after adding idle-only voice scroll command slots and bounded scroll injection telemetry.
- Updated hands-free memory after adding the `whiscode-enroll --record --record-missing` guided top-up path for wake, end, and enabled command reference sets.

## 2026-06-10
- Updated hands-free and telemetry memory after changing manual controls to Right Shift start/chunk plus F10 end/finalize and retiring Right Option + Right Shift as a distinct shortcut.
- Updated current-state wiki for the Right Shift/F10 manual model, hands-free fallback behavior, and bounded ignored-end telemetry.

## 2026-06-11
- Updated hands-free and telemetry memory after restoring the single-key manual toggle: Right Shift starts/stops, `--end-hotkey`/F10 are no longer current controls, and Right Option + Right Shift is ignored.
- Updated current-state wiki and README to keep Send Chunk documented as hands-free wake-phrase behavior only.

## 2026-06-18
- Updated external transcription queue memory after adding `mlx-whisper` external intake, `--external-only`, and CCAB short-lane root discovery for one warm process across multiple user inboxes.
