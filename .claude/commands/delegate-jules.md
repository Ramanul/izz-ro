---
description: Write a verified spec and hand it to Jules (executor, cloud, Gemini — 15 tasks/day free). Manager protocol, headless via tools/jules_api.py.
argument-hint: [short description of the task to delegate]
---

You are the MANAGER delegating to Jules (Google cloud executor via official API) the task: **$ARGUMENTS**

Protocol — identical to /delegate-opencode steps 0–3 (sync + STATE.md, premises verified
TWICE, working-tree check, spec in `specs/<task-slug>.md`) with these Jules specifics:

- Branch prefix `jules/<task-slug>`. Jules runs in ITS OWN cloud VM on a fresh clone of
  `origin/main` — it cannot see or damage local WIP, but it also cannot see uncommitted
  work: NEVER delegate a task whose premises depend on unpushed local changes.
- The spec must be fully self-contained in the prompt (Jules reads the repo, including
  AGENTS.md, but specs/ on origin may lag — inline the whole spec in the prompt).

4. **Hand off via the `jules` CLI** (primary route, verified end-to-end 2026-07-24 —
   session 16571763303422774183; the 401 from 2026-07-19 was the GitHub App not being
   connected, fixed since). Auth is automatic: OAuth token in Windows Credential Manager
   (`jules-cli:default`), no browser needed. From repo root:
   `jules new --repo Ramanul/izz-ro "<full spec text. Work on branch jules/<task-slug>. Commit, push the branch, do NOT merge. Report in Romanian.>"`
   TRAP: `jules` exits 0 even on failure — verify the output contains `Session is created`
   and an ID; never trust the exit code. Note the session id, update `specs/STATE.md` →
   Current task + session id. Free quota: 15 tasks/day, 3 concurrent — check
   `jules remote list --session` before parallel delegations.
   Fallback route (structured JSON, watch with auto-approve, AUTO_CREATE_PR):
   `python tools/jules_api.py ...` — requires a VALID `JULES_API_KEY` (the one in env
   returned 401 ACCESS_TOKEN_TYPE_UNSUPPORTED on 2026-07-24; the user regenerates it at
   https://jules.google.com/settings#api in their own terminal, never the manager).

5. **Do NOT babysit.** Check `jules remote list --session` once when you next need the
   result, not in a poll loop. When Status is Completed, pull the work onto a local branch:
   `git switch -c jules/<task-slug> && jules remote pull --session <id> --apply`
   (or, if Jules opened a PR, review with `gh pr diff` instead of a local checkout).
   Then run `/review-executor jules/<task-slug>`.
