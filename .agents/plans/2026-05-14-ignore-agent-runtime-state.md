# Ignore Agent Runtime State

## Summary
Keep generated agent runtime/worktree state out of git without ignoring durable tracked project state under `.agents/plans`, `.agents/checkpoints`, and `.agents/memory`.

## Key Changes
- Add `.agents/worktree/`, `.agents/worktrees/`, and `.agents/locks/` to `.gitignore`.
- Do not ignore all of `.agents/`, because this repo intentionally tracks plans, checkpoints, and memory.

## Verification
- Run `git status --short --branch` from the task worktree and main checkout.

## Assumptions
- The user wants runtime `.agents` clutter hidden, not removal of the tracked project-state documentation model.
