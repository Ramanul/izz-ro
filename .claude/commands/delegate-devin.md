---
description: Write a verified spec for a task and hand it to Devin Local (the executor). Manager protocol — premises must be verified before the spec exists.
argument-hint: [short description of the task to delegate]
---

You are the MANAGER delegating to Devin Local (executor, model SWE-1.6, Devin Desktop) the task: **$ARGUMENTS**

Protocol — every step is mandatory, in order:

1. **Verify premises TWICE, in text.** Before writing any spec line, confirm every factual claim
   the spec will rest on by reading the actual files (`Read`, `Grep`, `git ls-tree`, `git show`).
   Lesson from 2026-07-18: a spec claimed "no CI exists" while `.github/workflows/tests.yml`
   existed — the whole delegation was wasted. On Windows Git Bash, `git show origin/main:path`
   can fail from MSYS path mangling: prefer `git ls-tree origin/main -- <path>` and READ stderr.
2. **Check the working tree.** `git status -s`. Note every modified/untracked file that belongs
   to the user — the spec must list them as UNTOUCHABLE so Devin never restores/stashes them.
3. **Write the spec** to `specs/<task-slug>.md` (3–8 lines core + scope + acceptance criteria):
   - goal, exact files authorized (nothing else), verification command with expected output,
   - branch name `devin/<task-slug>`, "commit then STOP — no push, no merge, no PR",
   - explicit list of user WIP files Devin must not touch, stage, or discard.
4. **Hand off.** Tell the user the spec is ready, or if computer-use access to the Devin window
   is granted, paste into Cascade: "Read AGENTS.md, then execute specs/<task-slug>.md exactly."
5. **Do NOT babysit visually.** Screenshot supervision costs more tokens than doing the task
   yourself. Devin's auto-run + deny-list handles safe commands; return only for `/review-devin`.
