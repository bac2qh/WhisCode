# V2 Beta README And Tag

## Summary

Document the current build as the v2 beta and tag the merged main commit as `v2.0.0-beta.1`.

## Key Changes

- Update README version/status language to call out `v2.0.0-beta.1`.
- Describe v2 as the hands-free beta: local wake/end phrases, voice key commands, floating overlay default, and no start/end notification banners unless explicitly requested.
- Align package metadata to PEP 440 beta version `2.0.0b1`.
- Preserve existing setup and usage docs while making the version status clear near the top.

## Verification

- Run the test suite after the README change.
- Confirm the tag does not already exist before creating it on local `main`.

## Assumptions

- Use semantic prerelease tag `v2.0.0-beta.1`.
- Create the tag locally unless the user separately asks to push tags.
