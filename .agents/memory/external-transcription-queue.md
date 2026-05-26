# External Transcription Queue

## 2026-05-26
- WhisCode added an external NAS-style transcription queue for MLX VibeVoice only. External publishers write audio into a watched top-level inbox, and WhisCode emits `.txt` plus `.json` result sidecars into an outbox.
- The external queue is intentionally separate from manual dictation. It starts work only when no local recording is reserved, queued, or actively transcribing, and external jobs bypass hotwords, prompts, replacements, postprocessing, refinement, typing, and manual stats.
- External audio is decoded through MLX-Audio audio I/O and normalized to mono 16 kHz float32 before transcription. OGG/Opus and M4A support relies on an ffmpeg-capable MLX-Audio decode path being available on the host.
- Manual dictation keeps priority during long external VibeVoice jobs. If manual work arrives while the primary MLX VibeVoice engine is occupied by an external job, WhisCode starts one rescue engine, uses it for manual work, then promotes it and retires the old external engine after the external job completes. This caps the process at two in-process VibeVoice engines.
- Routine telemetry uses bounded external queue and engine lifecycle events and excludes transcript text, raw audio, prompts, hotwords, and full file paths. Outbox result files intentionally include transcript content as the delivery artifact.

## 2026-05-26 Native SMB
- WhisCode extended the external queue to accept native `smb://` inbox/outbox URLs without mounting the NAS locally. The initial target shape is `smb://192.168.4.21/NAS_1/whiscode/inbox`, with sibling `outbox` as the default result folder.
- SMB credentials are read from `WHISCODE_EXTERNAL_SMB_USERNAME`, `WHISCODE_EXTERNAL_SMB_PASSWORD`, and optional `WHISCODE_EXTERNAL_SMB_DOMAIN`, intended to be supplied by `op run`. Credentials embedded in SMB URLs are rejected.
- SMB audio files are streamed to a temporary local file with the original suffix before MLX-Audio decoding. SMB result sidecars are written to temporary remote files and then published with SMB replace/rename.
- Routine telemetry records only bounded storage scheme and file/job metadata; it must not include SMB credentials, full SMB URLs, transcript text, or raw audio.
