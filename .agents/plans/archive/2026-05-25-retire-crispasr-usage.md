## Closeout
- Final status: implemented.
- Related checkpoint file: .
- Implementation commits: , , .
- Merge commit: none; local  was fast-forwarded.
- Verification performed: ============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/xin/Documents/repos/WhisCode
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 26 items

tests/test_main_cli.py .........................                         [ 96%]
tests/test_benchmark_asr.py .                                            [100%]

============================== 26 passed in 0.22s ==============================; ============================= test session starts ==============================
platform darwin -- Python 3.13.13, pytest-9.0.3, pluggy-1.6.0
rootdir: /Users/xin/Documents/repos/WhisCode
configfile: pyproject.toml
plugins: anyio-4.12.1
collected 216 items

tests/test_benchmark_asr.py .                                            [  0%]
tests/test_calibrate.py .....                                            [  2%]
tests/test_command_config.py .....                                       [  5%]
tests/test_crispasr_asr.py ............................                  [ 18%]
tests/test_enroll.py ......................                              [ 28%]
tests/test_handsfree.py ....................                             [ 37%]
tests/test_hotwords.py ......                                            [ 40%]
tests/test_injector.py ..                                                [ 41%]
tests/test_llama_cpp_asr.py ..................                           [ 49%]
tests/test_main_cli.py .........................                         [ 61%]
tests/test_mlx_vibevoice_asr.py ..........                               [ 65%]
tests/test_postprocess.py .....................                          [ 75%]
tests/test_recorder.py ..                                                [ 76%]
tests/test_recording_overlay.py ...................                      [ 85%]
tests/test_refiner.py ............                                       [ 90%]
tests/test_reminders.py .....                                            [ 93%]
tests/test_stats.py ....                                                 [ 94%]
tests/test_status_notifier.py ....                                       [ 96%]
tests/test_telemetry.py ...                                              [ 98%]
tests/test_transcriber.py ..                                             [ 99%]
tests/test_transcription_queue.py ..                                     [100%]

============================= 216 passed in 0.28s ==============================; Listing 'whiscode'...; fixed mutex verified with .
- Worktree and branch cleanup result: removed  and deleted .
- Summary: Retired CrispASR/VibeVoice from recommended use, preserved it as a legacy GGUF compatibility backend, made MLX VibeVoice the recommended local VibeVoice path, and repaired the main-branch lock helper discovered during closeout.

# Retire CrispASR Usage In Favor Of MLX VibeVoice

## Summary
Retire CrispASR as the recommended VibeVoice path now that MLX VibeVoice is noticeably faster locally. Keep the `crispasr` backend available as a legacy compatibility option, but move docs and CLI wording toward `mlx-vibevoice`.

## Key Changes
- Mark `crispasr` as legacy/deprecated in CLI help and runtime startup output.
- Update README and wiki docs so `mlx-vibevoice` is the recommended VibeVoice backend.
- Move CrispASR documentation out of the main recommended path and frame it as legacy GGUF compatibility only.
- Keep existing CrispASR code/tests intact to avoid breaking old local setups.

## Telemetry / Debuggability
- No new telemetry events are needed. Existing `asr.backend_selected` and CrispASR telemetry remain sufficient to identify legacy backend usage.
- Do not change telemetry payload content.

## Tests
- Update CLI tests for legacy help wording if needed.
- Run `uv run --with pytest pytest tests/test_main_cli.py tests/test_benchmark_asr.py`.
- Run `uv run --with pytest pytest`.

## Assumptions
- "Retire usage" means deprecate and de-emphasize CrispASR rather than deleting backend code in this pass.
- Do not push; commit locally only.
