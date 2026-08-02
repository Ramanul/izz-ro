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
   `bash tools/oc_run.sh --dir . --title "<task-slug>" "Read AGENTS.md and specs/STATE.md (context, read-only), then execute specs/<task-slug>.md exactly. Work on branch oc/<task-slug>. Report in Romanian." 2>&1`
   - `tools/oc_run.sh` walks the free-route ladder below automatically: it skips routes whose
     key is unset, runs the first eligible one, and falls through on INFRASTRUCTURE failure
     only (non-zero exit, or an `Error:` line from opencode — auth / quota / rate limit /
     "credit card"). A route that runs and reports the task went badly is NOT retried —
     that is a task problem, and re-running it on four more providers only burns quota.
     Exit 0 = one route completed; exit 1 = every eligible route failed.
     `bash tools/oc_run.sh --list` shows which routes are live right now and why the others
     are skipped. Override the ladder for one run with `OC_ROUTES="a,b"`.
     Calling `opencode run` directly still works; you just lose the automatic fallback.
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
     2. `google/gemini-3.1-flash-lite` — works, but **deliberately gated behind its own key,
        `GEMINI_API_KEY_OC`, and dormant until the owner creates one.** MEASURED 2026-08-02:
        the Gemini free tier allows **15 requests per MINUTE** (probed directly — request 16
        returned 429 with `limit: 15`), and `generator/providers/gemini.py` sits exactly on
        that ceiling by design (`GEMINI_THROTTLE=4.0` → 4s × 15 = 60s). An unthrottled
        opencode call on the SAME key during a pipeline run pushes production over the limit,
        and with a single key `gemini.py` has no second key to fail over to → failed run on
        the live site. The second key must be on a **different Google account** — a second key
        on the same account shares the quota and fixes nothing.
        TRAP, still true: opencode's `google` provider reads `GOOGLE_GENERATIVE_AI_API_KEY`,
        not a `GEMINI_*` name — it lists the models fine and fails only at call time with
        "API key is missing". Handled by the explicit `provider.google.options.apiKey` in
        `opencode.json`. Do not "fix" it by setting a new env var.
     3. `mistral/codestral-latest` — **separate quota, SMOKE-TESTED OK 2026-08-02** with the
        owner's key. Third real fallback after the two above.
        `openrouter-free/*` — still dormant, needs `OPENROUTER_API_KEY` (and a one-off $10
        deposit on their side). The manager never creates accounts or handles keys.
        **`cerebras/*` and `groq/*` are OUT of the ladder — keys exist and are valid, but
        both free tiers are structurally unusable for an agentic harness. Do NOT re-diagnose
        this as a bad key:** groq caps tokens-per-minute at 8k–12k while opencode's system
        prompt alone is 32–46k tokens ("Request too large" on every call); cerebras returns
        `payment_required` on every chat call and caps free context at 8k anyway. They stay
        wired in `opencode.json` so a paid plan would work instantly.
     4. `ollama/qwen2.5-coder:7b` — local, unlimited, offline. **Deliberately NOT in the
        default ladder.** Measured 2026-08-02: this machine has a GTX 1060 with 3GB VRAM and
        16GB RAM, so a 4.7GB 7B model runs half on CPU — far too slow to drive an agentic
        loop with tool calls. Reachable on purpose with
        `OC_ROUTES="ollama/qwen2.5-coder:7b" tools/oc_run.sh "..."` after
        `ollama pull qwen2.5-coder:7b`. Offline last resort, not a replacement executor.
     NOT a fallback: `vercel/*` free models. Verified 2026-08-02 — the AI Gateway refuses
     with "requires a valid credit card on file" despite `AI_GATEWAY_API_KEY` being set.
   - `small_model` (session titles/metadata) is pinned to `mistral/codestral-latest`
     so housekeeping calls burn Mistral's separate quota instead of the 100/day Zen budget — and never touch the Gemini key the live pipeline depends on.
   - If it errors with auth/credentials: the user must run `opencode auth login -p opencode`
     in their OWN terminal (API key from https://opencode.ai/auth) — the manager never
     handles the key.
   - Zen free models may train on prompts — do NOT delegate anything confidential.
   After launching, update `specs/STATE.md` → Current task: `<task-slug>`, branch
   `oc/<task-slug>`, delegated <date>. STATE.md is manager-owned: executors read it, never write it.

5. **Do NOT babysit.** Read the transcript ONCE when the process exits, not in a poll loop.
   When it finishes, run `/review-executor oc/<task-slug>`.
