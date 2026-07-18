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
4. **Hand off via CLI — zero screenshots.** Always go through the wrapper (never call devin.exe
   directly: a git-provider nudge menu blocks every raw headless run — see tools/devin_headless.py
   docstring). From the repo root, in background (Bash run_in_background):
   `python tools/devin_headless.py --timeout 3600 -- -p "Read AGENTS.md, then execute specs/<task-slug>.md exactly. Report in Romanian." --permission-mode smart`
   Needs `pywinpty` (verified installed 2026-07-18). Model on Free plan: swe-1-6-slow.
   If the wrapper reports auth errors: user must run devin.exe `auth login` in their own terminal
   (one-time browser OAuth; CLI credentials are separate from the Desktop app). Do NOT fall back
   to computer-use on the Devin window unless the user explicitly asks.
   Modes: `smart` auto-runs edits + safe commands (pytest, git branch/commit); it blocks
   destructive ones — which is exactly the guardrail we want. Never use `dangerous`.
5. **Do NOT babysit.** The CLI streams Devin's full transcript as text to the background log —
   read it ONCE when the process exits, not in a poll loop. No screenshots at any point.
   When it finishes, run `/review-devin devin/<task-slug>`.
