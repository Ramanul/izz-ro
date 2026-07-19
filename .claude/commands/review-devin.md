---
description: Manager review of a Devin executor branch — text-based, cheap, verdict merge/reject. Run after Devin reports done.
argument-hint: [branch name, e.g. devin/ci-tests]
---

You are the MANAGER reviewing executor branch: **$ARGUMENTS** (default: the most recent `devin/*` branch if none given).

Review in TEXT via git — no screenshots, no UI. Every step mandatory:

1. **Scope check.** `git diff main...$ARGUMENTS --stat` — compare the touched files against the
   authorized list in the task's `specs/<task-slug>.md`. ANY file outside the list → instant REJECT.
2. **User-WIP check.** Confirm no commit on the branch contains changes to files that were the
   user's uncommitted WIP at delegation time (listed in the spec). If yes → REJECT, and check
   whether the WIP still exists in the working tree; report immediately if anything was lost.
3. **Regression check.** For every modified (not new) file, read the FULL before/after diff.
   Deleted lines are guilty until proven innocent — config, comments, and guards that exist
   usually exist for a reason (lesson: Devin replaced a deliberately push-less CI trigger).
4. **Verify by running.** Check out the branch (stash nothing — refuse to review if checkout
   would touch user WIP), run the spec's verification command, capture REAL output.
   For izz.ro: `python -m pytest tests/ -q` and, if pipeline code changed,
   `python -m generator.main --dry-run`.
5. **Verdict, one of exactly three:**
   - **MERGE** — all checks green: merge into main locally, delete the branch, report. Do not push unless the user has said to.
   - **FIX** — small correctable issues: list them precisely and hand back to Devin with a follow-up instruction; do not fix them yourself (the executor owns the branch).
   - **REJECT** — scope violation, WIP damage, or net regression: delete the branch after confirming nothing of value is lost, state the reason in one paragraph, and record the lesson in memory if it is a new failure mode.
6. **Write the state.** Update `specs/STATE.md`: verdict + merge commit (or FIX/REJECT reason)
   under "Last relevant commits", clear/replace "Current task", refresh "Next steps". Overwrite
   in place — the file must stay under ~30 lines. This is what lets the next session (manager or
   executor) start without re-reading the project.

7. **Report** in Romanian: verdict first, then evidence (real command output), then what it cost
   (files touched, lines, anything rejected).
