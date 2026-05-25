# Copy-Friendly Stdout Transcripts

## Summary
Remove the temporary last-transcripts file and make successful transcript output in stdout easy to copy: left-aligned, single-line, no leading marker, with blank spacing between transcript blocks.

## Key Changes
- Remove the `/tmp/whiscode-last-transcripts.txt` recovery feature and its related telemetry event.
- Replace the current transcript print format (`  > ...`) with a small stdout formatter that strips surrounding whitespace, collapses internal whitespace to single spaces, prints flush-left, and adds blank lines before and after each transcript.
- Keep clipboard/paste behavior unchanged; this change only affects terminal output.
- Keep recording queue, overlay stacking, and existing queue telemetry unchanged.
- Update README, wiki, and memory references so docs no longer mention the temporary recovery file.

## Telemetry / Debuggability
- Remove `transcript_recovery_file_written`; stdout is now the local debug/copy surface.
- Do not add transcript text to telemetry. Existing queue/job telemetry remains content-free.

## Test Plan
- Update queue tests to remove `TranscriptRecoveryLog` coverage.
- Add focused tests for the stdout transcript formatter:
  - removes prefix/indent by construction.
  - collapses multiline transcript text to one line.
  - preserves mixed English/Chinese text while normalizing spacing.
  - emits blank-line separation around transcript output.
- Run:
  - `uv run --with pytest pytest tests/test_transcription_queue.py`
  - `uv run --with pytest pytest`
  - `uv run python -m compileall whiscode`

## Assumptions
- Only successful transcript output gets the copy-friendly block format.
- Error, queue, and status messages keep their existing terminal style.
- The pasted/refined/hands-free transcript text path should not be changed by this stdout formatting cleanup.
