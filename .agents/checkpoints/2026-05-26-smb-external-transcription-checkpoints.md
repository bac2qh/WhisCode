# Native SMB External Transcription Queue Checkpoints

## 2026-05-26 Start

### Done
- Created task worktree `smb-external-transcription` at `.agents/worktrees/smb-external-transcription`.
- Saved implementation plan and matching checkpoint before source edits.
- Confirmed scope: native SMB access for `smb://192.168.4.21/NAS_1`, no local mount, credentials via `op run` environment variables.

### Immediate Next Step
- Refactor external transcription storage, add SMB adapter/config/tests, update docs/memory, verify, commit, and close out.

### Decisions And Reasoning
- Current external queue is path-based; SMB support requires a storage abstraction rather than passing `smb://` through `Path`.
- Use `smbprotocol` high-level `smbclient` APIs based on official docs for list/stat/open/write/replace.
- Do not handle Tailscale specially; SMB host can later be a Tailscale IP/name with the same URL parser.

### Verification
- Not run yet.

## 2026-05-26 Implementation

### Done
- Added a storage abstraction for external transcription intake with local filesystem and native SMB implementations.
- Added SMB URL parsing for `smb://host/share/path`, sibling outbox derivation, credential validation, and rejection of embedded URL credentials.
- Added `smbprotocol` as a runtime dependency and updated the lockfile.
- Updated external watcher/job processing to operate through storage entries and sidecar writers instead of raw `Path` objects.
- Added native SMB streaming through a temporary local file before MLX-Audio decode and atomic-style remote sidecar publishing through SMB temporary files plus replace.
- Cached SMB readiness after the first successful session registration and directory check so idle polling does not repeatedly register sessions.
- Updated CLI/env handling so `WHISCODE_EXTERNAL_AUDIO_INBOX` and `--external-audio-inbox` can be local paths or SMB URLs, with SMB credentials supplied by `WHISCODE_EXTERNAL_SMB_USERNAME`, `WHISCODE_EXTERNAL_SMB_PASSWORD`, and optional `WHISCODE_EXTERNAL_SMB_DOMAIN`.
- Updated README, ASR wiki docs, wiki log, and external transcription memory for the native SMB contract.
- Implementation commit: `7fa6af4`.

### Immediate Next Step
- Close out by merging the task branch to local `main` under the main-branch mutex.

### Decisions And Reasoning
- SMB credentials stay out of URLs and routine telemetry; docs show 1Password `op run --env-file` as the intended injection path.
- `WHISCODE_EXTERNAL_SMB_DOMAIN` is folded into the SMB username as `DOMAIN\username` because the installed `smbclient.register_session` API accepts `username` and `password` but no separate `domain` parameter.
- SMB inbox and outbox must be on the same host/share for v1 to keep authentication/session behavior simple and predictable.
- The watcher remains top-level-only and polling-based; native SMB changes the storage transport, not the queue semantics.
- Telemetry adds bounded `storage_scheme` fields and still avoids raw paths, URLs, transcripts, credentials, prompts, and audio bytes.

### Verification
- `uv run --with pytest pytest tests/test_external_transcription.py tests/test_main_cli.py` passed: 43 tests.
- `uv run --with pytest pytest` passed: 244 tests.
- `git diff --check` passed.

## 2026-05-26 Closeout

### Done
- Fast-forward merged `smb-external-transcription` into local `main`.
- Archived the plan to `.agents/plans/archive/2026-05-26-smb-external-transcription.md`.
- Removed task worktree `.agents/worktrees/smb-external-transcription`.
- Deleted local branch `smb-external-transcription`.
- Closeout bookkeeping commit: this commit.

### Immediate Next Step
- None; task is closed.

### Decisions And Reasoning
- Used a fast-forward merge because local `main` could advance directly to the task branch tip.
- Kept closeout metadata in a separate main commit so archived plan/checkpoint state records final cleanup.

### Verification
- Closeout ran under `.agents/scripts/main-branch-lock.sh`.
- The implementation had already passed targeted external/CLI tests, the full test suite, and `git diff --check` before merge.
