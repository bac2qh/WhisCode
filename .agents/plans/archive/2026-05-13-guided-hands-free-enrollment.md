# Guided Hands-Free Enrollment

## Closeout
- Final status: implemented.
- Related checkpoint: `.agents/checkpoints/2026-05-13-guided-hands-free-enrollment-checkpoints.md`.
- Implementation commits: `5fcbb3d`, `34336dd`.
- Merge commit: none; local `main` was fast-forwarded to `34336dd`.
- Verification performed: `uv run --with pytest python -m pytest` passed with 73 tests; `uv run whiscode --help` passed; `uv run whiscode-enroll --help` passed; missing-reference `--no-enroll-prompt` path exited with expected instructions.
- Worktree and branch cleanup: removed `.agents/worktrees/guided-hands-free-enrollment`; deleted local branch `guided-hands-free-enrollment`.
- Shipped: guided Python microphone enrollment through `whiscode-enroll --record`, automatic `--hands-free` setup prompt, non-interactive fail-fast option, docs, tests, and memory.

## Summary
- Add an in-app enrollment wizard so Voice Memos are no longer needed.
- Keep the existing file-import path for advanced/manual use.
- When `uv run whiscode --hands-free` finds missing or insufficient wake/end samples, it will offer to run the guided recorder before starting hands-free mode.
- Default enrollment records 3 samples per phrase, 2 seconds each, with Enter-to-record prompts.

## Key Changes
- Create branch/worktree `.agents/worktrees/guided-hands-free-enrollment` from current local `main`, then save plan/checkpoint before edits.
- Extend `whiscode-enroll`:
  - Existing mode remains: `whiscode-enroll wake file1.m4a file2.m4a file3.m4a`.
  - New guided mode:
    - `uv run whiscode-enroll --record`
    - Records wake samples, then end samples.
    - Prompt pattern: "Press Enter, say your wake phrase, recording for 2.0 seconds..."
    - Writes WAVs directly to `~/.config/whiscode/wake/wake/` and `~/.config/whiscode/wake/end/`.
  - Optional flags: `--samples 3`, `--seconds 2.0`, `--wake-dir`, `--end-dir`.
- Add reusable enrollment recording code using the existing `sounddevice`/resampling path:
  - Capture mic audio for fixed duration.
  - Save 16 kHz mono WAV via Python stdlib `wave`.
  - Avoid `afconvert` for guided recording because audio is already captured in the correct format.
- Update `uv run whiscode --hands-free` startup:
  - Validate wake/end reference folders before loading `local-wake`.
  - If either folder has fewer than 3 WAVs, print what is missing and prompt: `Run guided enrollment now? [Y/n]`.
  - If accepted, run the same guided enrollment flow inline, then continue startup.
  - If declined, exit with the explicit `whiscode-enroll --record` command to run later.
- Keep non-interactive behavior available with `--no-enroll-prompt`, which exits immediately if samples are missing.

## Diagnostics And UX
- Emit bounded setup messages only: sample kind, sample number, duration, output path, and validation counts.
- Do not log raw audio content or transcripts during enrollment.
- Existing macOS notifications may be reused for "Recording now" / "Recording completed" during guided sample capture, but terminal prompts remain the primary UX.
- If microphone open/recording fails, show a concise error and do not write a partial sample.

## Test Plan
- Unit-test guided enrollment:
  - records exactly 3 wake and 3 end samples by default.
  - writes valid WAV paths under the expected folders.
  - honors `--samples`, `--seconds`, `--wake-dir`, and `--end-dir`.
  - refuses invalid sample count or duration.
- Unit-test hands-free startup validation:
  - missing samples triggers enrollment prompt.
  - accepting prompt runs enrollment and proceeds.
  - declining prompt exits cleanly with instructions.
  - `--no-enroll-prompt` exits without prompting.
- Unit-test CLI parsing for new flags.
- Verification commands:
  - `uv run --with pytest python -m pytest`
  - `uv run whiscode --help`
  - `uv run whiscode-enroll --help`

## Assumptions
- V1 uses fixed-duration sample recording, not manual stop.
- Default guided setup is 3 samples per phrase, 2 seconds each.
- `--hands-free` may be interactive by default when enrollment is missing.
- Existing Voice Memo/file import behavior remains supported.
