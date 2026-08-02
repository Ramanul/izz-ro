# CLAUDE.md — izz.ro

> Operating contract for Claude Code / Cowork in this repository.
> Read fully before acting. These rules override default behavior.

## 0. Communication
- Talk to the user (Alexandru) in **Romanian**. Code, identifiers, commit messages, logs, and technical terms stay in **English**.
- Be direct and concise. No flattery, no auto-agreement. If a request is wrong or there is a better path, say so with reasons.
- State uncertainty explicitly. Never present a guess as fact.
- **Be proactive (owner decision 2026-07-24).** In EVERY discussion — izz.ro or any other topic — anticipate the next problem and surface improvement / efficiency ideas unprompted, act with initiative. But proposals stay proposals the owner confirms: initiative never becomes autonomous action on `main` or an unattended loop (§5, §14 still bind).

## 1. What izz.ro is
AI-powered Romanian news aggregator. Brand promise: **"Zero Zgomot"** (Zero Noise) — synthesized, de-duplicated, clean news. The site is **statically generated** from a content pipeline (scrape -> synthesize -> cluster -> categorize -> render).

## 2. Tech stack — VERIFIED 2026-06-26
Python 3.11 (cloud) / 3.14 (local), Jinja2, feedparser, pyyaml, python-slugify, markdown, python-dotenv.
AI: Gemini 2.5 Flash Lite via REST (no SDK), switchable to Claude API via `AI_PROVIDER=anthropic`.
CI/CD: GitHub Actions (`build.yml`, cron `13 */2` — every 2h). Hosting: Cloudflare Pages (render-only build).
Pipeline state: `data/articles.json` (committed to repo — no SQLite).

## 3. Repository structure
```
generator/          pipeline: main.py · fetch.py · cluster.py · process.py · render.py
                             state.py · moderation.py · config.py · util.py · providers/
templates/          Jinja2 (autoescape ON): base.html · index.html · article.html
                    category.html · legal.html · _card.html
static/             styles.css · styles.dark.bak.css · logo.svg · favicon.svg
content/legal/      legal pages (markdown)
data/articles.json  pipeline state (committed to repo, persists between runs)
moderation.yaml     editorial control (human in the loop)
output/             generated site (gitignored; deployed by Cloudflare Pages)
.github/workflows/  build.yml (fetch+AI+commit, cron every 2h — see §17)
```

## 4. Commands — use EXACT strings
- Install deps: `pip install -r requirements.txt`
- Run pipeline (full): `python -m generator.main`
- Dry run (no save, no render): `python -m generator.main --dry-run`
- Render only (no AI/fetch): `python -m generator.main --render-only`
- Serve locally: `python -m http.server 8000 --directory output` → http://localhost:8000
- Lint / format: *(not configured — ruff not in requirements.txt)*
- Type-check: *(not configured)*
- Tests: `python -m pytest tests/ -q` (**235 tests** as of 2026-08-02, counted from a real run after #106; CI runs them via `.github/workflows/tests.yml` on PRs + manual dispatch — deliberately NOT on push, because content commits land every 2h). The count is a rough marker, not a gate: check it against a real run before quoting it anywhere.

## 5. Workflow — MANDATORY (this is the fix for past sprawl)
1. **Spec first.** Before any code, write 3-8 lines: goal, inputs/outputs, acceptance criteria. No spec -> no code.
2. **Plan before non-trivial work.** Use plan mode or an `ultrathink` planning turn: analyse, propose a step plan, name the files each step would touch, DO NOT edit yet. Wait for the user's go-ahead.
3. **Vertical slices.** Implement ONE feature end-to-end, verify it, commit it — then the next. Never broad multi-area edits in one pass.
4. **Verify by running, not by claiming.** After each slice, run the relevant command, capture the REAL output, and check it against the acceptance criteria. "It works" is valid only after you ran it and saw it pass. If you cannot run it, say so — do not assert success.
5. **Commit on green.** Each verified slice = one commit with a clear message. Functional states are checkpoints. Never "improve" working code outside the current slice.
6. **Minimal diffs.** Change the least necessary. No opportunistic refactors of adjacent code.

## 6. Definition of Done (ALL must hold before a slice is "done")
- [ ] Acceptance criteria from the spec are met.
- [ ] The relevant command was run; real output confirms success.
- [ ] Lint / format / type-check pass.
- [ ] Site still builds (no regression).
- [ ] Committed with a descriptive message.

## 7. Domain rules (izz.ro-specific, non-negotiable)
- **No mangled output.** The pipeline must never publish raw, truncated headlines. If a fallback path cannot meet the "Zero Zgomot" quality bar, SKIP the item — do not publish it broken.
- **One axis, one home.** An article belongs to exactly one place per taxonomy axis. Do not cross-post the same item across geography and topic axes (this is what caused duplicates).
- **Clustering changes are verified empirically.** Before committing any change to clustering, test it on real article samples covering BOTH over-merge and under-merge cases. State the results.
- **Source diversity.** Be aware of overconcentration in the Digi / RCS-RDS family; do not introduce logic that worsens it.
- **Attribution formula — PERMANENT (owner decision 2026-07-04).** Every story surface shows exactly ONE provenance element, labeled `Sursă` (1 source) / `Surse` (≥2), placed after the body text: plain names on cards (`sources-inline`), linked names on article pages (`sources-box`), the φ aside on the hero. No other label ("Proveniență", "N surse" counts), no per-article methodology notice — the methodology text lives ONLY in `/legal/method/` (footer "Cum sintetizăm"). Source names are ALWAYS links to the exact external article at that source (`target="_blank" rel="noopener noreferrer"`) — on cards, hero, and article pages alike. Cards end with the sources line — NO extra CTA ("Citește"); the title is the internal link. Any new surface (widget, feed, panel) must reuse this exact formula.

## 8. Design tokens
All visual styling derives from `static/styles.css` (golden-ratio φ=1.618 type scale, Fibonacci spacing, light-golden palette).
- Never hardcode colors, font sizes, or spacing in templates — reference CSS custom properties from `static/styles.css`.
- Value missing? Add a custom property; do not inline a one-off.

## 9. Bootstrap — COMPLETED 2026-06-26
Sections 3, 4, and 8 filled from real repo state. No placeholders remain.

## 10. Do NOT touch without explicit instruction
- Synthesis / attribution logic ("Model C" multi-source) and anything legal / GDPR-relevant.
- Production deploy config (Cloudflare Pages, GitHub Actions secrets).

## 11. SEO — RESOLVED 2026-06-26
All previously listed gaps are implemented and verified against real render output:
- `og:type: article` — present on all article pages (base.html block override in article.html)
- `dateModified` — present in NewsArticle JSON-LD (render.py `_article_jsonld`)
- `lastmod` — present on all sitemap URLs (render.py `_write_sitemap`)
No remaining SEO gaps known. Do NOT re-audit or rebuild without a specific new finding.

## 12. Tooling & effort
- PowerShell and Desktop Commander may run without per-command approval, within the security hook's blocklist. Reading files and running the documented dev/build/lint/test commands needs no confirmation. Destructive or irreversible actions still require confirmation.
- For substantive, multi-file tasks: enable `/effort ultracode` (session-wide xhigh + dynamic workflow orchestration). For routine single-slice edits: `/effort high` is enough and spends fewer tokens. Use an `ultrathink` turn specifically for planning before a hard slice.

## 13. Front-end verification — measure, don't eyeball
Prefer local CLI measurement tools over "testing websites": structured JSON output, runs on **localhost before deploy**, no rate limits. External APIs (PageSpeed Insights, W3C) are a *post-deploy* complement on the live site, not a substitute.
- **After any slice that changes front-end output** (templates, `static/styles.css`, render.py HTML/JSON-LD): run `bash tools/audit.sh` and report Lighthouse scores (Perf / Accessibility / Best-practices / SEO) and pa11y WCAG2AA error count **before vs after**. "It looks fine" is not a result; a score delta is.
- Setup once: `npm i -g lighthouse pa11y`. The script auto-detects Chromium (`CHROME_PATH` to override), renders, serves `output/`, and writes JSON to `.audit/` (gitignored). Auto-detection covers Linux/CI (Chrome *and* Chromium) **and, on Windows, Google Chrome's default install paths only** — Chromium has no official Windows installer, so there is no canonical path to probe; pass `CHROME_PATH` for a Chromium or Edge build there. Until 2026-08-02 the script was Linux-only in three separate ways on Windows (no browser found, a version line reading "Opening in existing browser session.", and pa11y dying on an MSYS path while the run still printed "-1 errors"). If you are reading a `.audit/` from before that date on a Windows machine, its pa11y count is not a measurement.
- **Measure is a compass, not an autopilot.** Scores *inform* the next slice, which you still propose and I confirm (see §5). Never launch an autonomous "optimization" marathon, and never chase a Lighthouse number with tricks that degrade the real experience.
- **Current baseline — re-measured 2026-08-02 on `main` @ `34cc8d3`:** home Perf **80** / A11y 100 / BP 100 / SEO 100; article Perf **88** / 100 / 100 / 100; pa11y WCAG2AA **0** errors. Measured with Lighthouse 13.4.1, pa11y 9.1.1, Chromium 141.0.7390.37 — an upgrade of any of the three moves the numbers, so `audit.sh` now writes them to `.audit/versions.txt` on every run. Compare like with like: the same corpus on the Windows desktop under **Chrome 150.0.7871.187** reads home **83-84** / article **92** in the low-CLS mode below, so 80 is not a number to reproduce there.
- **Pin the article page when comparing.** `audit.sh` used to score `find | head -1`, i.e. whatever the filesystem returned first, so the "article" score silently referred to different pages across runs (measured: 87 vs 88 on the same commit). The default is sorted and therefore stable for a given corpus, but content shifts between renders — for a real before/after, pass `ARTICLE_PATH=/cat/slug/`.
- **On variance — it is a two-state switch, not a spread (measured 2026-08-02, PR #106).** Six runs across two revisions, article pinned: home read 84·83·84 before and 76·83·83 after, and each score tracks CLS landing on exactly one of two values — ~0.156 (home 83-84) or 0.272 (home 76). Same bimodality on article pages: 92 at CLS 0.172, 85 at 0.272. Both modes occur on **both** revisions, so the switch is pre-existing, not something a slice introduced. Consequences: a single before/after pair **cannot** resolve an effect smaller than ~8 points on home, so run **3+ repetitions per revision and compare medians**, with `ARTICLE_PATH` pinned. This supersedes the earlier "5 identical runs, one outlier at 84" reading — that was the same switch seen from one side.
- **A number in this file is a local-sandbox figure, not a promise about izz.ro.** It exists to compare *before vs after a slice on the same machine*. When a score looks like a regression, measure the pre-slice commit in a worktree and compare — that is what turned the "photos broke Perf" alarm of 2026-08-02 into a non-event (home was 80 both before and after; the whole cost of adding real photos was −1 point on an article page, +65 KiB, +0.3 s LCP — full before/after table in PR #101).
- **Why home Perf is held down** (measured from the Lighthouse JSON, not guessed): CLS and FCP. CLS scores 56 at weight 25 in the bad mode, FCP 2.6 s scores 65 at weight 10, `styles.css` blocks render ~900 ms, TBT is a perfect 100. None of it is image-related.
- **The CLS culprit is `#izz-install-btn`, and the two earlier explanations were wrong** (measured 2026-08-02, mobile emulation 412 px). Lighthouse attributes 100% of the shift to a single element, `body > main`, whose final `boundingRect.top` is **285**. Toggling the install button in a real browser: hidden → `main` starts at **236.3**; shown → **285.3**. Exact match. The button lives inside `.nav` in the sticky header group, `hidden` in the markup, and `personalize.js::initInstallButton` clears `hidden` when `beforeinstallprompt` fires — pushing every article down **49 px** mid-read. That event's timing is not deterministic, which is exactly why the score is bimodal rather than noisy.
  - **NOT `#izz-consent`:** it is `position: fixed; bottom: 0`, i.e. out of flow — it cannot move `main`. Do not re-investigate it.
  - **NOT the web-font swap:** forcing the declared fallback stacks and re-measuring gives a **0 px** delta on the header group at both 412 px and 1280 px. The fonts are self-hosted, subsetted (7–17 KB) and two are preloaded. Do not re-investigate this either.
  - Fixing it is a **placement decision, not a technical one** — the button has to stop growing the header, and where it goes instead is the owner's call (§8). Reserving the row permanently would cost 49 px of mobile header for a button most visitors never see. Do not "fix" it by delaying the reveal past the CLS window; that is chasing the number, which this section forbids.
- The 2026-07-02 fix that got A11y to 100 darkened two tokens (`--ink-3`, `--gold-strong`) — a cautionary tale worth keeping: the "footer links" finding was actually 249 site-wide errors; only measurement revealed the real scope. Contrast for new colors must clear 4.5:1 against `--paper` AND `--gold-wash`, not just white.

## 14. Autonomous delivery mandate — ENDED / HISTORICAL (owner decision 2026-07-13)
The 2026-07-10 autonomous mandate is **OVER**. Its backlog shipped (2026-07-11) and the live site is green. It caused a concrete problem: multiple sessions each running an autonomous cron and auto-merging into `main` collided (2026-07-12/13 — GA + security-header work had to be rebuilt after parallel PRs landed). So, permanently now:
- **Do NOT arm any autonomous loop / recurring CronCreate to self-drive the backlog.** No session should merge to `main` on its own schedule.
- **Who merges to `main` — owner rule, 2026-07-24.** The account the owner is *currently working
  from* merges. Not "whoever opened the PR", not "the account that always owns main" — the active
  one. So: if you are the session the owner is talking to right now, you merge; do not park a green
  PR waiting for the other account.
- **After any merge, tell the other account.** Parallel work is allowed *because* the accounts stay
  informed. Write the merge into the cross-account channel (`TASKS-B.md` in
  `Ramanul/claude-desktop-workspace`, plus `specs/STATE.md` here) so the idle account never
  re-does or re-reviews landed work. A merge nobody announced is what causes the collisions §14
  was written about.
- Still true: **do not race `main`.** Branch, keep the diff small, land it, announce it. The old
  blanket "one writer, ask the owner first" is superseded by the two rules above.
- **Revert to the §5 confirmation workflow + §16 verification** for all work. Spec → plan → verified slice → the owner (or the live smoke/visual jobs) confirms.
- Historical record of the delivered backlog (do not re-do): Chromium image engine, cache `_headers`, EAA accessibility statement, legal wording pass, A11y/SEO/perf thresholds, pytest suite + tests.yml, covers.py cleanup — all ✅.
- **Owner facts (never invent legal facts):** operator = natural person, initials **S.A.N.**, Romania — already in privacy.md.

### 14b. Background work — REINSTATED, BOUNDED (owner decision 2026-08-01)
§14 banned autonomous loops because *two accounts* each ran one and collided (12–13 Jul). That
premise is gone: STATE.md records single-account mode. The owner is often away for days and wants
progress meanwhile, so a background Routine is allowed again — under limits that keep the original
failure impossible:
- **It never merges to `main`.** It opens a **draft PR** and stops. Only the owner merges. This is
  the whole safety property: nothing reaches the live site without human review.
- **One task per firing**, taken from the `## Open` list in `specs/STATE.md`. It does not invent
  work, does not touch anything marked "owner decision pending", and does not start a second task.
- **It stops and reports instead of guessing.** Ambiguity, a failing premise, or a task needing a
  cost/design call ends the run with a written note in the PR or STATE.md — not a best guess.
- **It updates `specs/STATE.md`** so the next session (background or owner) starts informed.
- Everything else still applies: §5 spec→verify→commit, §16 two-role verification, §7/§8 domain
  and token rules. A background run gets no exemption from any of them.
Anything wider than this — self-merging, self-directed backlog invention, a second concurrent
loop — remains forbidden by §14 above.

## 15. Sub-agents & commands — delegate the verification rituals
Project sub-agents live in `.claude/agents/` (versioned, see its README). Each isolates a noisy, bounded, summarizable job and returns a verdict — use them so the main thread stays on the decision, not the noise. Map task → agent:
- Changing `generator/cluster.py` or its thresholds → **`clustering-tuner`** verifies over-merge AND under-merge on real samples (enforces §7). It reports; it does not edit.
- Changing templates / `static/styles.css` / render.py HTML/JSON-LD → **`frontend-auditor`** runs `tools/audit.sh` and reports the Lighthouse/pa11y delta (enforces §13).
- "Does it still build?" / verify by running → **`pipeline-runner`** runs `--dry-run` / `--render-only` / `qa_check.py` safely (enforces §5.4).
- Reviewing any story-surface change → **`editorial-guard`** checks the attribution formula, Zero Zgomot, one-axis-one-home, and design tokens (enforces §7, §8). Read-only.

**Executor workflow (Devin, added 2026-07-18):** well-specified implementation tasks can be
delegated to Devin (model swe-1-6-slow, free quota — costs zero Claude tokens). **`/delegate-devin`**
writes a premise-verified spec to `specs/` and hands it off headlessly via
`python tools/devin_headless.py -- -p "..." --permission-mode smart` (NEVER run devin.exe directly —
an interactive startup nudge blocks piped runs; the wrapper's docstring explains). Devin works on a
`devin/<task>` branch under the contract in `AGENTS.md`; **`/review-devin`** then reviews the branch
text-only (git diff + tests) with verdict MERGE/FIX/REJECT. Manager reviews and merges; the executor
never pushes or merges.

**Execution state (`specs/STATE.md`, added 2026-07-19):** the single source of truth for "where we
are" — current task, last relevant commits, user WIP, blockers, next steps. Manager-owned writes:
update it at the end of every slice and inside `/review-devin`; executors receive it read-only.
Overwrite in place, keep it under ~30 lines. Start every session by reading it (after
`git pull --ff-only` — the CI bot commits every 2h, so local main is often stale).

**Delegation-first execution (owner decision 2026-07-24).** Default posture: delegate execution work to agents, keep the main thread on decisions — in any discussion, not only izz.ro. Two agent tiers with DIFFERENT reach, never conflate them:
- *In-session Claude subagents* (`Explore`, `general-purpose`, the verification agents) run in ANY environment, including Claude on the web. These are the default executor when working from a web/Linux session.
- *Free code executors* (Devin, OpenCode) run ONLY from a local desktop session via the Windows wrapper — they are NOT reachable from a web/Linux container (verified 2026-07-24: no `devin.exe`, no `pywinpty`). From the web, do not pretend otherwise: use in-session subagents or do it directly, and say which.
Delegation is not free: when a task's implementation is smaller than the spec+review overhead (≈<5k tokens, see `specs/metrics.md`), do it directly instead of delegating. Never delegate in a way that races `main` or arms an autonomous loop (§14 holds absolutely).

Slash commands in `.claude/commands/`: **`/slice`** drives the mandatory §5 workflow for one vertical slice; **`/audit`** runs the front-end audit. Permission allowlist for the documented-safe commands lives in `.claude/settings.json` (this is §12 made enforceable — read-only and dev/build commands no longer prompt; push/commit/deletes still do). A web-only `SessionStart` hook (`.claude/hooks/session-start.sh`) installs the pipeline deps (with `SETUPTOOLS_USE_DISTUTILS=stdlib`, needed for feedparser/sgmllib3k) so Claude Code on the web can run the pipeline and these agents.

## 16. Two-role verification + honesty calibration — HARD RULE (owner decision 2026-07-12)
Context: a correct CSS fix was reported "rezolvat" while the owner still saw the bug — because it was verified as *code* but never as the *live user experience*, and the fix was undeliverable (immutable-cached `styles.css` with no cache-bust). Never again. For ANY user-visible change:

1. **Verify in BOTH roles before claiming anything.**
   - *As a programmer:* run the code — render / `pytest` / `qa_check` — real output, not assertion.
   - *As a user:* drive the actual built page in a real (headless Chromium) browser and observe the EXACT reported symptom. Reproduce it first, then confirm the fix removes it. Measure, don't infer: computed styles, real requests, real pixels. "It should work now" is not verification.
2. **Verify DELIVERABILITY, not just correctness.** A fix that a cached/immutable asset, a service worker, a stale CDN copy, or a wrong URL prevents from reaching the user is NOT done. Static assets (`styles.css`, JS) MUST carry a content-hash `?v=` (see `render._asset_ver`) so a change actually reaches returning visitors; check the emitted URL changed.
3. **Three distinct states — never conflate them, and use the exact words:**
   - "**reparat în cod**" = the diff is written.
   - "**verificat local**" = both roles above passed on the built site here.
   - "**confirmat pe live**" = the deployed site shows it fixed.
     **MEASURED CORRECTION 2026-07-25 — the old "the sandbox cannot reach izz.ro" is FALSE here.**
     From the Claude Code web sandbox: `https://izz.ro/` → HTTP 200 with real content, and every
     PR gets a Cloudflare branch preview (`https://<branch>.izz-ro.pages.dev/`) that is also
     reachable. Both were used to prove a before/after on the real deploy: live `/surse/` served
     9,804 bytes with 2 external links and zero "Primăria", the preview served 39,262 bytes with
     189 links and 121 primării; live manifest `name` was still `izz.ro — Zero Zgomot` while the
     preview served `izz.ro`. News sites stay blocked by the proxy — that limit is real and
     separate. **So Claude CAN reach the third state now**, and must actually do it before saying
     "gata": fetch the deployed URL, assert the exact symptom is gone, quote the response.
     Always cache-bust (`?cb=$(date +%s)`) — a plain request can hit a cached edge copy.
     If a future sandbox genuinely cannot reach it, say so with the failing command, and fall back
     to **"reparat + verificat local; rămâne de confirmat pe live după deploy"**. What has not
     changed: never say "rezolvat / gata / done" for a user-visible issue on code evidence alone.
4. **When you cannot test something, say so explicitly** (which role, why) instead of implying it passed. Honesty about a gap beats a confident false "gata".

This overrides any earlier phrasing that let "committed/rendered" stand in for "fixed for the user".

## 17. Publication cadence & throughput — MEASURED 2026-07-25 (stop re-diagnosing this)
Twice now a session has read "cron 30 min" in this file, seen runs 1.5–4.5h apart, and concluded
the pipeline was broken. It is not. The docs were wrong; they are fixed above. The real numbers:

- **`build.yml` cron is `13 */2` — every 2 hours, deliberately.** Each state commit triggers a
  Cloudflare Pages build and the free plan allows ~500/month; 12/day ≈ 360/month leaves headroom
  for PR previews. Running more often exhausts the build budget and deploys stop — that is
  literally the 5–9 July 2026 outage. **Do not "fix" the cadence by making it more frequent.**
- **The throughput cap is the AI budget, not the schedule:** `max_ai_calls` defaults to 18 per
  run (≈216/day). `workflow_dispatch` accepts a one-off override for seeding a new category;
  the comment in `build.yml` says explicitly not to change the cron default.
- **Measured volume** (`data/articles.json`, 2026-07-25): 25 articles by midday, against 198 the
  previous full day, 92, 40, 101, 229, 286 for the days before. Day-to-day variance is large and
  normal; a low count at noon is not evidence of a stalled pipeline. **Check run history before
  claiming the pipeline is down** — `gh run list --workflow=pipeline` or the Actions API.
- If the owner wants more articles per day, the lever is the per-run AI budget (costs Gemini
  quota) or clustering yield — **not** the cron. That is a cost decision, so it is the owner's.

## 18. Local institution images — consent-gated (owner decision 2026-07-24)
Taxpayer funding does NOT place a public institution's photos in the public domain, and "public on their site" ≠ free to reuse. Legea 8/1996 art. 9 frees the TEXT of official acts (laws, administrative notices) — NOT photographs. A photo taken by a municipal employee is the INSTITUTION's work: the institution is the rightsholder and must grant reuse; a photo by a contracted photographer or an agency (Agerpres/Mediafax) belongs to that third party. Being of an elected official reduces that person's *image right* (they may be shown) but does NOT touch the *photographer's copyright* in a specific image. These are not legal facts to improvise (§14) — for anything operational, the owner confirms with a lawyer.

izz.ro may use a local institution's image ONLY when one of these holds, verified and RECORDED (link + quote):
1. the institution publishes reuse terms / an open license (open-data / PSI reuse notice) covering images, OR
2. a free-licensed portrait/photo exists on Wikidata / Wikimedia Commons (existing pipeline path — `fetch_leadphotos.py` PD/CC0, `fetch_portraits.py` CC-BY), OR
3. the institution gave written reuse permission.
NO blanket scraping of institution sites. Agents research and gather this evidence per institution into a whitelist; the owner (or legal) approves it before any image is pulled — human-in-the-loop, like `moderation.yaml`. Missing all three → the article keeps its generated cover.

## 19. Session hygiene & context economy — HARD RULE (owner decision 2026-08-01)
Context: a session opened on 2026-07-25 was still being continued on 2026-08-01. Every turn
re-sent a week of history, and two `actions_list` calls returned **340,000 characters each**.
The 5-hour usage window hit 32% in roughly ten minutes of work. Nothing in that history was
needed — `specs/STATE.md` already held every conclusion.

- **One task, one session.** Do not continue a conversation across days. When a slice is done and
  STATE.md is updated, the transcript has no residual value: STATE.md *is* the handoff, and §15
  already requires reading it first. Say so to the owner rather than silently continuing a stale
  session.
- **Never pull a large payload into context.** GitHub Actions listings, full `data/articles.json`,
  log files, `git log` without `--format` — filter at the source (`jq`, a `python -c` that prints
  only the fields needed, `--per_page`, `grep -c`, `head`). A tool result costing more than the
  slice it supports is a defect, not a detail. If a tool dumps to a file because it was too large,
  that is the signal the call was wrong — narrow it, do not read the file.
- **Model to match the work.** Routine single-slice edits do not need the most expensive model;
  reserve it for planning and hard reasoning. §12's effort guidance is about depth, this is about
  cost — they are different dials.
- **Sub-agents cost ~5.6x per delivered line** (measured, `COORD-DASHBOARD.md`). Worth it for
  genuinely parallel or noisy measurement work; wasteful for an edit you can make directly.
- **Agents share the working tree.** A background agent that runs `git checkout` moves the branch
  under everyone else — this happened on 2026-07-25 and cost a rebuild. Give every parallel agent
  `isolation: "worktree"`, or a dedicated `git worktree`. Never let two agents write the same branch.
