# README Recommended Hands-Free VibeVoice Update Checkpoints

## 2026-06-08 Initial Checkpoint

### Plan

- Saved matching plan at `.agents/plans/2026-06-08-readme-recommended-handsfree-vibevoice.md`.
- Task branch/worktree: `readme-recommended-handsfree-vibevoice` at `.agents/worktrees/readme-recommended-handsfree-vibevoice`.
- Scope: documentation-only README update that recommends `uv run whiscode --hands-free --asr-backend mlx-vibevoice` for daily dictation while preserving existing runtime defaults.

### Validation Contract

- `VC-001 critical`: README shows the recommended command exactly as `uv run whiscode --hands-free --asr-backend mlx-vibevoice`.
- `VC-002 critical`: README accurately describes hands-free wake/end behavior and wake-as-Send-Chunk behavior without inventing new flags.
- `VC-003 important`: README explains Send Chunk as recommended for long messages due to faster chunked transcription and as a natural pause/breather.
- `VC-004 important`: Existing backend docs still state `mlx-whisper` is the default and `mlx-vibevoice` is the preferred VibeVoice backend, not the hard default.
- `VC-005 advisory`: No transcript, audio, prompt, hotword, provider payload, typed text, secrets, or credentials are added to docs.

### Current State

- Main checkout was clean on `main` before creating the task worktree.
- Project memory index exists at `.agents/memory/MEMORY.md`.
- README currently documents `uv run whiscode`, optional `uv run whiscode --hands-free`, `mlx-whisper` as the ASR default, and `mlx-vibevoice` as the recommended VibeVoice backend.

### Next Step

- Edit `README.md` Usage section.
- Update durable project memory for the new recommended user-facing workflow.
- Run the targeted README validation checks and `git diff --check`.

## 2026-06-08 Implementation Checkpoint

### Done

- Updated `README.md` Usage with a new "Recommended daily workflow" section before the hotkey flow.
- Documented the exact recommended command: `uv run whiscode --hands-free --asr-backend mlx-vibevoice`.
- Described wake phrase start, wake-as-Send-Chunk while recording, end phrase finish, Right Shift fallback, manual Send Chunk fallback, and FIFO typing order.
- Framed Send Chunk as preferred for long messages because chunks transcribe sooner, keep the queue moving, and provide a natural pause.
- Updated `.agents/memory/hands-free-keyword-detection.md` and `.agents/memory/log.md` with durable README guidance history.
- Implementation commit: `c0c9f54` (`Document recommended hands-free VibeVoice workflow`).

### Verification

- `git diff --check` passed.
- `rg --count-matches "uv run whiscode --hands-free --asr-backend mlx-vibevoice" README.md` returned `1`.
- `rg -n "hands-free-chunk|include-chunk|whiscode-enroll chunk|chunk samples|chunk phrase" README.md` returned no matches, confirming the README did not gain retired chunk-specific flags or sample guidance.
- `rg -n --fixed-strings '| \`--asr-backend BACKEND\` | \`mlx-whisper\` |' README.md` confirmed the options table still documents `mlx-whisper` as the ASR default.
- `rg -n 'recommended VibeVoice backend|opt-in MLX-Audio|not a change to the CLI defaults|preferred local VibeVoice ASR backend' README.md` confirmed the recommended workflow is described as opt-in guidance, while the MLX VibeVoice section still calls it the recommended VibeVoice backend.

### Validation Contract Status

- `VC-001 critical`: passed.
- `VC-002 critical`: passed.
- `VC-003 important`: passed.
- `VC-004 important`: passed.
- `VC-005 advisory`: passed by static diff review; no transcript, audio, prompt, hotword, provider payload, typed text, secrets, or credentials were added.

### Next Step

- Commit this checkpoint hash update.
- Run closeout: merge to local `main`, archive the active plan, remove the task worktree, and delete the local task branch under the main-branch mutex.

## 2026-06-08 Closeout Preparation

### Done

- Moved the completed plan to `.agents/plans/archive/2026-06-08-readme-recommended-handsfree-vibevoice.md`.
- Added a closeout note to the archived plan with final status, checkpoint link, implementation commits, verification, and the closeout-command deviation.

### Deviation

- Attempted to start an interactive shell under `.agents/scripts/main-branch-lock.sh` to keep the mutex held while editing main closeout bookkeeping. The escalation reviewer rejected that as too broad.
- Safer fallback: archive plan/checkpoint state on the task branch, then run a single concrete non-interactive mutex command to fast-forward local `main`, remove the task worktree, and delete the merged branch.

### Next Step

- Commit the closeout-preparation archive move.
- Run the non-interactive mutex closeout command from the main checkout.
