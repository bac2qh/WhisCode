# Trim Hands-Free Samples And Prepare Calibration

## Closeout
- Final status: implemented.
- Related checkpoint: `.agents/checkpoints/2026-05-14-trim-calibrate-handsfree-checkpoints.md`.
- Implementation commits: `55046e6`, `4af1178`.
- Merge: fast-forward to local `main`; no merge commit.
- Verification: `PYTHONPATH=. uv run --with pytest python -m pytest`, `uv run whiscode-enroll --help`, `uv run whiscode-calibrate --help`, `uv run whiscode-calibrate`, `PYTHONPATH=. uv run python -m py_compile whiscode/enroll.py whiscode/calibrate.py`, `uv lock --check`, and `git diff --check`.
- Cleanup: task worktree `.agents/worktrees/trim-calibrate-handsfree` removed; local branch `trim-calibrate-handsfree` deleted.
- Shipped VAD-trimmed reference sample preprocessing and the read-only `whiscode-calibrate` distance report.

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
