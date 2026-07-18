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
4. **Hand off via CLI — zero screenshots.** Devin has a headless CLI bundled with Devin Desktop:
   `$LOCALAPPDATA/Programs/Devin/resources/app/extensions/windsurf/devin/bin/devin.exe`
   First check auth: `devin.exe auth status`. If "Not logged in", STOP and ask the user to run
   `devin.exe auth login` in their own terminal (one-time browser OAuth) — do NOT fall back to
   computer-use on the Devin window unless the user explicitly asks.
   Then run in background (Bash run_in_background, from the repo root):
   `"$DEVIN" -p "Read AGENTS.md, then execute specs/<task-slug>.md exactly. Report in Romanian." --permission-mode smart`
   Modes: `smart` auto-runs edits + safe commands (pytest, git branch/commit); it blocks
   destructive ones — which is exactly the guardrail we want. Never use `dangerous`.
5. **Do NOT babysit.** The CLI streams Devin's full transcript as text to the background log —
   read it ONCE when the process exits, not in a poll loop. No screenshots at any point.
   When it finishes, run `/review-devin devin/<task-slug>`.
