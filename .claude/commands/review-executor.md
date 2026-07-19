---
description: Manager review of ANY executor branch (devin/*, oc/*, jules/*) — text-based, cheap, verdict merge/fix/reject. Run after the executor reports done.
argument-hint: [branch name, e.g. oc/smoke-test or devin/ci-tests]
---

You are the MANAGER reviewing executor branch: **$ARGUMENTS** (default: the most recent
`devin/*` or `oc/*` branch if none given). The executor prefix tells you who did the work;
the protocol is identical for all of them.

Review in TEXT via git — no screenshots, no UI. Every step mandatory:

1. **Scope check.** `git diff main...$ARGUMENTS --stat` — compare touched files against the
   authorized list in `specs/<task-slug>.md`. ANY file outside the list → instant REJECT.
2. **User-WIP check.** Confirm no commit on the branch touches files listed as user WIP in the
   spec. If yes → REJECT, verify the WIP still exists in the working tree, report immediately.
3. **Regression check.** For every modified (not new) file, read the FULL before/after diff.
   Deleted lines are guilty until proven innocent — config, comments, and guards that exist
   usually exist for a reason.
4. **Verify by running.** Check out the branch (refuse to review if checkout would touch user
   WIP), run the spec's verification command, capture REAL output.
   For izz.ro: `python -m pytest tests/ -q` and, if pipeline code changed,
   `python -m generator.main --dry-run`.
5. **Verdict, one of exactly three:**
   - **MERGE** — all green: merge into main locally, delete the branch, report. Push follows
     the standing authorization (after green review).
   - **FIX** — small correctable issues: list them precisely, hand back to the SAME executor
     that owns the branch (`/delegate-devin` follow-up or `opencode run --continue`); do not
     fix them yourself.
   - **REJECT** — scope violation, WIP damage, or net regression: delete the branch after
     confirming nothing of value is lost, state the reason in one paragraph, record the
     lesson in memory if it is a new failure mode. Note WHICH executor failed and how — this
     feeds the routing decision (which executor gets which class of task).
6. **Write the state.** Update `specs/STATE.md`: verdict + merge commit (or FIX/REJECT reason)
   under "Last relevant commits", clear/replace "Current task", refresh "Next steps". Keep the
   file under ~30 lines.
7. **Report** in Romanian: verdict first, then evidence (real command output), then cost
   (files touched, lines, anything rejected), then executor scorecard note (one line).
