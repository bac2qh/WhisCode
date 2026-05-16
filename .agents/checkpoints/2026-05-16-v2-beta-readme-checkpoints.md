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
- Implementation commit: `95b33b8`.
- Immediate next step: merge to local `main`, tag the merged commit, and remove the task worktree/branch.

## 2026-05-16 Closeout

- Archived the active plan to `.agents/plans/archive/2026-05-16-v2-beta-readme.md`.
- Closeout commit: pending.
- Immediate next step: commit closeout bookkeeping, fast-forward local `main`, create annotated tag `v2.0.0-beta.1`, then clean up the worktree and branch.
