# Trim Hands-Free Samples And Prepare Calibration

## Summary
- Fix guided/imported hands-free reference samples so speech is VAD-trimmed before saving.
- Add a local calibration report command that summarizes reference-set distances and telemetry trigger distances.
- Keep runtime wake/end thresholds unchanged until trimmed samples are re-enrolled and observed.

## Key Changes
- Reuse `local-wake` Silero VAD trimming and minimum padding behavior for enrollment output.
- Add `whiscode-calibrate` as a read-only report CLI for wake/end reference folders and telemetry JSONL.
- Report wake-within, end-within, wake-vs-end, confirmed trigger, and detector-summary distance distributions with advisory threshold candidates.
- Update docs, wiki, and memory to describe re-enrollment and calibration workflow.

## Telemetry And Diagnostics
- Calibration reads local telemetry but does not emit telemetry.
- Report only aggregate distances, counts, and file basenames; do not include raw audio, transcripts, or typed text.

## Test Plan
- Unit-test VAD trim/pad behavior during enrollment.
- Unit-test fallback behavior when VAD finds no speech.
- Unit-test calibration report generation from fake distance and telemetry inputs.
- Run `PYTHONPATH=. uv run --with pytest python -m pytest`.
- Run `uv run whiscode-enroll --help` and `uv run whiscode-calibrate --help`.
