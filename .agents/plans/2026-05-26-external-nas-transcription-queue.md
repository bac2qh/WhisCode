# External NAS Transcription Queue

## Status
Active implementation plan saved before source edits.

## Summary
- Add a WhisCode-owned NAS watch wrapper for external agents: publishers place audio files in an inbox, WhisCode transcribes them, then writes `.txt` and `.json` results into an outbox.
- Keep manual recording first-class: manual recordings retain FIFO typing behavior and take priority over external jobs.
- For in-process MLX backends, allow at most two engines when an external job is running and manual work arrives: the running external job keeps the old engine, manual work lazily starts a rescue engine, and the rescue engine becomes primary after the external job finishes.
- External intake is v1 only for `mlx-vibevoice`; existing Whisper support remains in the app but is not part of the external NAS queue work.

## Configuration
- Add `WHISCODE_EXTERNAL_AUDIO_INBOX` / `--external-audio-inbox`, disabled when unset.
- Add `WHISCODE_EXTERNAL_TRANSCRIPT_OUTBOX` / `--external-transcript-outbox`, defaulting to a sibling outbox when inbox is set.
- Add `WHISCODE_EXTERNAL_EXTENSIONS`, default `.wav,.mp3,.flac,.ogg,.opus,.m4a,.aac`.
- Add `WHISCODE_EXTERNAL_POLL_SECONDS` and `WHISCODE_EXTERNAL_STABLE_SECONDS`.
- `pyproject.toml` dependency changes are in scope where they support the external queue/audio decode path.

## Implementation Plan
1. Inspect existing CLI, transcription queue, ASR backend, telemetry, stats, and tests.
2. Add reusable MLX engine manager behavior with fake-engine unit coverage.
3. Add external audio loading and watcher/worker modules:
   - top-level scan only.
   - hidden and unsupported files ignored.
   - size/mtime quiet-period stability check.
   - duplicate/result skipping based on source metadata.
   - result sidecars with bounded success/error metadata.
4. Wire external intake into main startup and scheduling:
   - external work starts only when no local recording is active/reserved/queued.
   - external jobs bypass typing, postprocess, replacements, refine, and manual stats.
   - manual jobs during external MLX transcription use rescue engine behavior.
   - fail fast if external intake is enabled with any backend other than `mlx-vibevoice`.
5. Add bounded telemetry events:
   - `external.watcher_started`
   - `external.file_seen`
   - `external.file_queued`
   - `external.transcription_started`
   - `external.transcription_completed`
   - `external.transcription_failed`
   - `asr.engine_rescue_started`
   - `asr.engine_promoted`
   - `asr.engine_retired`
6. Document inbox/outbox contract, supported formats, ffmpeg requirement, and priority/two-engine behavior in README/wiki.
7. Run targeted tests and repair failures.

## Telemetry / Debuggability
- External queue telemetry must be bounded and privacy-preserving.
- Routine telemetry must not include raw audio, transcript text, prompts, full file paths, hotword contents, secrets, provider payloads, or high-cardinality identifiers.
- Result files intentionally contain transcript content because they are the external delivery channel.
- Verification must include tests or static review proving external jobs use plain backend transcript output without typing/postprocess/refine/manual stats updates.

## Assumptions
- Publishers may write directly into the inbox; a quiet-period stability check is the readiness mechanism.
- Publishers should prefer unique filenames; result IDs include source metadata to reduce collisions.
- v1 watches only the top-level inbox folder.
- Existing local manual workflow semantics should remain unchanged when external intake is disabled.
