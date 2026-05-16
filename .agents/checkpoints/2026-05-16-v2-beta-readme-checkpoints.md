# V2 Beta README And Tag Checkpoints

## 2026-05-16 Start

- Created branch/worktree `v2-beta-readme` from local `main` at `f605289`.
- Existing tags include `v1.0.0`; chosen new beta tag is `v2.0.0-beta.1`.
- Immediate next step: update README version/status docs, verify, commit, merge to local `main`, and create the tag.
- Verification: pending.

## 2026-05-16 Implementation

- Updated README with a `Version Status` section naming `v2.0.0-beta.1` and summarizing v2 as the hands-free beta.
- Added the v2 hands-free startup command near basic usage.
- Bumped package metadata from `0.1.0` to PEP 440 beta version `2.0.0b1`.
- Updated project memory with the v2 beta milestone.
- Verification: `PYTHONPATH=. uv run --with pytest python -m pytest` passed with 129 tests.
- Immediate next step: commit the README/version metadata update, merge to local `main`, and tag the merged commit.
