---
description: Write a verified spec for a task and hand it to OpenCode (executor, Zen free models). Manager protocol — premises must be verified before the spec exists.
argument-hint: [short description of the task to delegate]
---

You are the MANAGER delegating to OpenCode (executor, headless `opencode run`, Zen free models) the task: **$ARGUMENTS**

Protocol — every step is mandatory, in order (identical to /delegate-devin except the handoff):

0. **Sync + load state.** `git fetch origin && git pull --ff-only` on `main` — the CI bot
   commits content every ~30 min. If the pull refuses because of local WIP, STOP and report —
   never stash or discard user files. Then read `specs/STATE.md`: current task, user WIP, blockers.

1. **Verify premises TWICE, in text.** Before writing any spec line, confirm every factual claim
   by reading the actual files (`Read`, `Grep`, `git ls-tree`, `git show`). On Windows Git Bash,
   prefer `git ls-tree origin/main -- <path>` over `git show origin/main:path` and READ stderr.

2. **Check the working tree.** `git status -s`. Every modified/untracked user file goes in the
   spec as UNTOUCHABLE.

3. **Write the spec** to `specs/<task-slug>.md` (3–8 lines core + scope + acceptance criteria):
   goal, exact files authorized (nothing else), verification command with expected output,
   branch name `oc/<task-slug>`, "commit then STOP — no push, no merge, no PR",
   explicit list of user WIP files OpenCode must not touch, stage, or discard.

4. **Hand off headless.** From the repo root, in background (Bash run_in_background):
   `opencode run --dir . --title "<task-slug>" "Read AGENTS.md and specs/STATE.md (context, read-only), then execute specs/<task-slug>.md exactly. Work on branch oc/<task-slug>. Report in Romanian." 2>&1`
   - Permissions come from repo `opencode.json` (edits allowed; destructive git + rm denied).
     NEVER pass `--auto`.
   - Model: pinned in repo `opencode.json` (`opencode/deepseek-v4-flash-free`). TRAP
     (2026-07-19): without a pinned model, opencode auto-picks a Gemini model from the
     user's `GEMINI_API_KEY` env var and dies on a missing Google key. Free Zen models:
     `opencode models | grep -E "free|pickle"`.
   - If it errors with auth/credentials: the user must run `opencode auth login -p opencode`
     in their OWN terminal (API key from https://opencode.ai/auth) — the manager never
     handles the key.
   - Zen free models may train on prompts — do NOT delegate anything confidential.
   After launching, update `specs/STATE.md` → Current task: `<task-slug>`, branch
   `oc/<task-slug>`, delegated <date>. STATE.md is manager-owned: executors read it, never write it.

5. **Do NOT babysit.** Read the transcript ONCE when the process exits, not in a poll loop.
   When it finishes, run `/review-executor oc/<task-slug>`.
