> Closeout Note (2026-05-26)
>
> - Final status: implemented.
> - Related checkpoint file: `.agents/checkpoints/2026-05-26-smb-external-transcription-checkpoints.md`.
> - Implementation commit: `7fa6af4`.
> - Checkpoint bookkeeping commit: `44f924f`.
> - Merge commit: none (fast-forward merge to local `main`).
> - Verification performed: targeted external/CLI tests (43 passed), full test suite (244 passed), `git diff --check`.
> - Worktree and branch cleanup result: removed `.agents/worktrees/smb-external-transcription`; deleted local branch `smb-external-transcription`.
> - Summary: shipped native SMB external transcription intake for `smb://` NAS inbox/outbox URLs, SMB credential env handling, `smbprotocol` dependency, SMB sidecar publishing, docs, memory, and tests.
>

# Native SMB External Transcription Queue

## Summary
- Update external transcription so `--external-audio-inbox` accepts both local paths and SMB URLs like `smb://192.168.4.21/NAS_1/whiscode/inbox`.
- Keep the current polling model, queue priority, VibeVoice-only backend, sidecar result shape, and low idle overhead.
- Do not mount the NAS locally. Use Python SMB client APIs directly.
- Credentials come from environment variables loaded by `op run`, not from the SMB URL.

## Key Changes
- Add dependency `smbprotocol` and use its high-level `smbclient` API for SMB list/stat/read/write operations.
- Add a storage abstraction behind the existing external watcher:
  - local storage keeps current `Path` behavior.
  - SMB storage maps `smb://host/share/path` to UNC paths like `\\host\share\path`.
  - SMB outbox defaults to sibling `outbox` if omitted, so `.../whiscode/inbox` defaults to `.../whiscode/outbox`.
- Add config:
  - `WHISCODE_EXTERNAL_AUDIO_INBOX=smb://192.168.4.21/NAS_1/whiscode/inbox`
  - `WHISCODE_EXTERNAL_TRANSCRIPT_OUTBOX=smb://192.168.4.21/NAS_1/whiscode/outbox`
  - `WHISCODE_EXTERNAL_SMB_USERNAME`
  - `WHISCODE_EXTERNAL_SMB_PASSWORD`
  - optional `WHISCODE_EXTERNAL_SMB_DOMAIN`
- Recommended launch uses `op run --env-file .env.whiscode-smb -- uv run whiscode --asr-backend mlx-vibevoice`.
- For SMB audio decoding, download remote bytes to a temporary local file with the original suffix, then pass that temp file through the existing MLX-Audio decode/normalization path.
- For SMB sidecars, write `.txt` and `.json` to temporary remote filenames in the outbox, then publish with SMB `replace`/rename so readers do not see partial files.
- Telemetry stays bounded: record storage scheme, extension, size, duration, file id, status, and error type; never record credentials, full SMB URLs, transcript text, or raw audio.

## Telemetry / Debuggability
- Add or preserve bounded external queue events with `storage_scheme` and safe file metadata only.
- Routine telemetry must not include SMB username/password/domain, full SMB URLs, transcript text, raw audio, or provider payloads.
- Outbox files intentionally include transcript content because they are the delivery channel.

## Test Plan
- Unit test SMB URL parsing and UNC conversion.
- Unit test config parsing for local path, SMB URL, sibling default outbox, and SMB credential requirements.
- Unit test watcher behavior through fake storage: stability, extension filtering, duplicate/result skipping.
- Unit test SMB storage with mocked `smbclient`: listdir/stat/read/open_file/makedirs/replace use UNC paths.
- Unit test SMB audio temp-file decode path.
- Run full test suite.

## Assumptions
- Default SMB folders are `smb://192.168.4.21/NAS_1/whiscode/inbox` and sibling `.../whiscode/outbox`.
- WhisCode will not invoke `op` directly; it only reads env vars. The user starts WhisCode under `op run`.
- Tailscale is out of scope for this pass. The same SMB URL shape can work later if hostname/IP changes to a Tailscale address.
- No SMB credentials are accepted inline in URLs.
