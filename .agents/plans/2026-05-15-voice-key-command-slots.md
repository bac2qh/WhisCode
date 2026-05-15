# Add Configurable Hands-Free Key Command Slots

## Summary

Add three voice command slots that are trained like wake/end samples but map to fixed physical keyboard actions: Page Up, Page Down, and Enter. The spoken phrases are not hardcoded; enrollment records samples for each slot, and the user can say any phrase they want for that slot.

## Key Changes

- Add command reference folders under `~/.config/whiscode/wake/commands/page-up`, `page-down`, and `enter`.
- Guided enrollment records wake, end, then the three command slots. Prompts name the target key, not required wording.
- Runtime loads one local detector per command slot and listens only while idle. During recording/transcribing, command detections are ignored so dictated text cannot inject keys.
- Command slot mappings are fixed for v1:
  - `page-up` -> `pynput.keyboard.Key.page_up`
  - `page-down` -> `pynput.keyboard.Key.page_down`
  - `enter` -> `pynput.keyboard.Key.enter`
- Add CLI tuning flags for command threshold and confirmations, defaulting to wake behavior: threshold `0.055`, confirmations `2`.

## Telemetry And Diagnostics

- Emit bounded telemetry for command detection and key injection using slot name, distance, threshold, RMS/active-ratio gate context where available, and outcome.
- Do not log raw audio, transcripts, arbitrary spoken phrases, file contents, or provider payloads.
- Reuse existing hands-free detector distance/gate summaries for command detector tuning.

## Test Plan

- Unit-test command slot detection requires enough samples and confirmation count.
- Unit-test command events are emitted only while idle and ignored while recording/transcribing.
- Unit-test key injection maps slots to Page Up, Page Down, and Enter.
- Unit-test guided enrollment writes samples into the three command slot folders and preserves wake/end enrollment.
- Unit-test CLI parsing for command threshold/confirmation options.
- Run full pytest suite plus `uv run whiscode --help`, `uv run whiscode-enroll --help`, and `uv run whiscode-calibrate --help`.

## Assumptions

- The physical keys are Page Up, Page Down, and Enter.
- Spoken command phrases are arbitrary and learned from samples; WhisCode does not hardcode "page up" or "page down".
- Commands are active only while idle.
- Wake/end behavior and Right Shift fallback stay unchanged.
