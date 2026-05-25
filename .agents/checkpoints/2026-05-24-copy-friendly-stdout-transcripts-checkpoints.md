# Copy-Friendly Stdout Transcripts Checkpoints

## 2026-05-24 - Plan Saved
- Done: Saved the implementation plan before changing source files.
- Immediate next step: Remove transcript recovery file code and replace the transcript print path with copy-friendly stdout formatting.
- Key decisions: Use stdout as the local copy/debug surface, avoid clipboard changes, and keep telemetry content-free.
- Verification: Pending.
- Commits: Implementation later recorded as `8585b1b`.

## 2026-05-24 - Implementation Ready
- Done: Removed `TranscriptRecoveryLog`, the `/tmp/whiscode-last-transcripts.txt` write path, and `transcript_recovery_file_written` telemetry. Successful transcripts now print through a stdout formatter that collapses whitespace to one line and emits a blank-line-separated flush-left block.
- Immediate next step: Commit the implementation and close out the task worktree after final verification.
- Key decisions: The typed/refine/hands-free paths keep using the existing processed transcript; only terminal presentation changes. Routine telemetry remains transcript-free, and raw CrispASR debug logging is unchanged.
- Verification: `uv run --with pytest pytest tests/test_transcription_queue.py tests/test_main_cli.py` passed; `uv run --with pytest pytest` passed; `uv run python -m compileall whiscode` passed; `git diff --check` passed.
- Commits: `8585b1b` (`Make transcript stdout copy friendly`).
