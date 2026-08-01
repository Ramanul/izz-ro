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
   - **Free fallback ladder (verified 2026-08-02).** When the Zen quota (~100 req/day) is
     spent, re-run the SAME command with `-m <route>`; no reconfiguration needed. In order:
     1. `opencode/laguna-s-2.1-free` · `opencode/north-mini-code-free` — other Zen free
        models (SMOKE-TESTED OK). Same quota pool, so this only helps if one model is
        rate-limited, not if the daily budget is gone.
     2. `google/gemini-3.1-flash-lite` — **separate quota**, key already in the env
        (SMOKE-TESTED OK, returned a correct answer). This is the real first fallback.
        TRAP (2026-08-02): opencode's `google` provider reads `GOOGLE_GENERATIVE_AI_API_KEY`,
        NOT `GEMINI_API_KEY` — it lists the models fine and then fails at call time with
        "API key is missing". Fixed in `opencode.json` via an explicit
        `provider.google.options.apiKey = {env:GEMINI_API_KEY}`. Do not "fix" it by
        setting a new env var.
     3. `cerebras/*` (1M tok/day) · `groq/*` · `openrouter-free/*` · `mistral/*` — wired in
        `opencode.json`, DORMANT until the owner creates the key himself and sets
        `CEREBRAS_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` / `MISTRAL_API_KEY`.
        The manager never creates accounts or handles keys.
     4. `ollama/qwen3-coder:30b` — local, unlimited, offline, no data leaves the machine.
        Requires `ollama pull qwen3-coder:30b` first; confirm the exact tag with `ollama list`.
     NOT a fallback: `vercel/*` free models. Verified 2026-08-02 — the AI Gateway refuses
     with "requires a valid credit card on file" despite `AI_GATEWAY_API_KEY` being set.
   - `small_model` (session titles/metadata) is pinned to `google/gemini-3.1-flash-lite`
     so housekeeping calls burn Google's quota instead of the 100/day Zen budget.
   - If it errors with auth/credentials: the user must run `opencode auth login -p opencode`
     in their OWN terminal (API key from https://opencode.ai/auth) — the manager never
     handles the key.
   - Zen free models may train on prompts — do NOT delegate anything confidential.
   After launching, update `specs/STATE.md` → Current task: `<task-slug>`, branch
   `oc/<task-slug>`, delegated <date>. STATE.md is manager-owned: executors read it, never write it.

5. **Do NOT babysit.** Read the transcript ONCE when the process exits, not in a poll loop.
   When it finishes, run `/review-executor oc/<task-slug>`.
