> Closeout Note (2026-05-27)
>
> - Final status: implemented.
> - Related checkpoint file: `.agents/checkpoints/2026-05-27-repo-local-op-env-checkpoints.md`.
> - Implementation commit: `ce3fb35`.
> - Checkpoint bookkeeping commit: `2ee04b6`.
> - Merge commit: none (fast-forward merge to local `main`).
> - Verification performed: ignored real env file check, unignored example check, `tests/test_main_cli.py` (29 passed), `git diff --check`.
> - Worktree and branch cleanup result: removed `.agents/worktrees/repo-local-op-env`; deleted local branch `repo-local-op-env`.
> - Summary: shipped tracked `.env.1password.whiscode-smb.example`, ignored real repo-local env files, and documented `op run --env-file .env.1password.whiscode-smb` instead of `~/.zshrc` exports.
>

# Repo-Local 1Password Env Pointer File

## Summary
- Current code already supports repo-local env-file launch through `op run --env-file`; no WhisCode runtime code change is needed.
- Add repo hygiene and docs so SMB NAS config lives in a repo-local 1Password reference file, not `~/.zshrc`.
- Standardize the real local filename as `.env.1password.whiscode-smb`; it is intentionally untracked and contains only `op://...` references, not plaintext secrets.

## Key Changes
- Add `.env.1password.whiscode-smb.example` as the tracked template.
- Update `.gitignore` to ignore real repo-local env files while allowing example templates:
  - ignore `.env` and `.env.*`
  - allow `.env*.example`
- Update README/wiki launch instructions to use:
  ```bash
  op run --env-file .env.1password.whiscode-smb -- \
    uv run whiscode --asr-backend mlx-vibevoice
  ```
- Make docs explicit that the real file contains 1Password reference pointers like `op://...`, not resolved passwords, and nothing belongs in `~/.zshrc`.

## Template Contents
- Include NAS and polling defaults:
  ```bash
  WHISCODE_EXTERNAL_AUDIO_INBOX=smb://192.168.4.21/NAS_1/whiscode/inbox
  WHISCODE_EXTERNAL_TRANSCRIPT_OUTBOX=smb://192.168.4.21/NAS_1/whiscode/outbox
  WHISCODE_EXTERNAL_EXTENSIONS=.wav,.mp3,.flac,.ogg,.opus,.m4a,.aac
  WHISCODE_EXTERNAL_POLL_SECONDS=2
  WHISCODE_EXTERNAL_STABLE_SECONDS=5
  WHISCODE_EXTERNAL_SMB_USERNAME="op://<vault>/<item>/username"
  WHISCODE_EXTERNAL_SMB_PASSWORD="op://<vault>/<item>/password"
  WHISCODE_EXTERNAL_SMB_DOMAIN=WORKGROUP
  ```

## Telemetry / Debuggability
- Telemetry not applicable: this change only adds repo-local configuration hygiene and documentation; it does not change runtime behavior or emitted diagnostic signals.

## Test Plan
- Verify `.env.1password.whiscode-smb` is ignored by Git.
- Verify `.env.1password.whiscode-smb.example` remains trackable.
- Run the existing CLI tests that cover env parsing:
  ```bash
  uv run --with pytest pytest tests/test_main_cli.py
  ```
- Run `git diff --check`.

## Assumptions
- The implementation will not create the real `.env.1password.whiscode-smb` file, because it is user-local and untracked.
- The tracked example will use placeholder `op://<vault>/<item>/...` references rather than real vault/item names.
- No global shell startup files such as `~/.zshrc` will be edited.
