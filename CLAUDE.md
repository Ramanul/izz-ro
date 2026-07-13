# CLAUDE.md — izz.ro

> Operating contract for Claude Code / Cowork in this repository.
> Read fully before acting. These rules override default behavior.

## 0. Communication
- Talk to the user (Alexandru) in **Romanian**. Code, identifiers, commit messages, logs, and technical terms stay in **English**.
- Be direct and concise. No flattery, no auto-agreement. If a request is wrong or there is a better path, say so with reasons.
- State uncertainty explicitly. Never present a guess as fact.

## 1. What izz.ro is
AI-powered Romanian news aggregator. Brand promise: **"Zero Zgomot"** (Zero Noise) — synthesized, de-duplicated, clean news. The site is **statically generated** from a content pipeline (scrape -> synthesize -> cluster -> categorize -> render).

## 2. Tech stack — VERIFIED 2026-06-26
Python 3.11 (cloud) / 3.14 (local), Jinja2, feedparser, pyyaml, python-slugify, markdown, python-dotenv.
AI: Gemini 2.5 Flash Lite via REST (no SDK), switchable to Claude API via `AI_PROVIDER=anthropic`.
CI/CD: GitHub Actions (`build.yml`, cron 30 min). Hosting: Cloudflare Pages (render-only build).
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
.github/workflows/  build.yml (fetch+AI+commit, cron 30min)
```

## 4. Commands — use EXACT strings
- Install deps: `pip install -r requirements.txt`
- Run pipeline (full): `python -m generator.main`
- Dry run (no save, no render): `python -m generator.main --dry-run`
- Render only (no AI/fetch): `python -m generator.main --render-only`
- Serve locally: `python -m http.server 8000 --directory output` → http://localhost:8000
- Lint / format: *(not configured — ruff not in requirements.txt)*
- Type-check: *(not configured)*
- Tests: *(not configured)*

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
- Setup once: `npm i -g lighthouse pa11y`. The script auto-detects Chromium (`CHROME_PATH` to override), renders, serves `output/`, and writes JSON to `.audit/` (gitignored).
- **Measure is a compass, not an autopilot.** Scores *inform* the next slice, which you still propose and I confirm (see §5). Never launch an autonomous "optimization" marathon, and never chase a Lighthouse number with tricks that degrade the real experience.
- Current scores (2026-07-02, after contrast token fix): home Perf 89 / A11y 100 / BP 96 / SEO 100; article 90 / 100 / 96 / 100; pa11y WCAG2AA 0 errors. The fix that got A11y to 100 darkened two tokens (`--ink-3`, `--gold-strong`) — a cautionary tale: the "footer links" finding was actually 249 site-wide errors; only measurement revealed the real scope. Contrast for new colors must clear 4.5:1 against `--paper` AND `--gold-wash`, not just white.

## 14. Autonomous delivery mandate — ENDED / HISTORICAL (owner decision 2026-07-13)
The 2026-07-10 autonomous mandate is **OVER**. Its backlog shipped (2026-07-11) and the live site is green. It caused a concrete problem: multiple sessions each running an autonomous cron and auto-merging into `main` collided (2026-07-12/13 — GA + security-header work had to be rebuilt after parallel PRs landed). So, permanently now:
- **Do NOT arm any autonomous loop / recurring CronCreate to self-drive the backlog.** No session should merge to `main` on its own schedule.
- **ONE active session at a time writes to izz.ro.** If you are a new session and unsure whether another is active, ask the owner before starting parallel work — do not race `main`.
- **Revert to the §5 confirmation workflow + §16 verification** for all work. Spec → plan → verified slice → the owner (or the live smoke/visual jobs) confirms.
- Historical record of the delivered backlog (do not re-do): Chromium image engine, cache `_headers`, EAA accessibility statement, legal wording pass, A11y/SEO/perf thresholds, pytest suite + tests.yml, covers.py cleanup — all ✅.
- **Owner facts (never invent legal facts):** operator = natural person, initials **S.A.N.**, Romania — already in privacy.md.

## 15. Sub-agents & commands — delegate the verification rituals
Project sub-agents live in `.claude/agents/` (versioned, see its README). Each isolates a noisy, bounded, summarizable job and returns a verdict — use them so the main thread stays on the decision, not the noise. Map task → agent:
- Changing `generator/cluster.py` or its thresholds → **`clustering-tuner`** verifies over-merge AND under-merge on real samples (enforces §7). It reports; it does not edit.
- Changing templates / `static/styles.css` / render.py HTML/JSON-LD → **`frontend-auditor`** runs `tools/audit.sh` and reports the Lighthouse/pa11y delta (enforces §13).
- "Does it still build?" / verify by running → **`pipeline-runner`** runs `--dry-run` / `--render-only` / `qa_check.py` safely (enforces §5.4).
- Reviewing any story-surface change → **`editorial-guard`** checks the attribution formula, Zero Zgomot, one-axis-one-home, and design tokens (enforces §7, §8). Read-only.

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
   - "**confirmat pe live**" = the deployed site shows it fixed. Only I (owner) or the live `smoke_live.py` can reach izz.ro — the sandbox cannot. So Claude MUST NOT say "rezolvat / gata / done" for a user-visible issue. The most it may claim on its own is **"reparat + verificat local; rămâne de confirmat pe live după deploy"**, and it states plainly what the owner should check. "Done" is reserved for after live confirmation.
4. **When you cannot test something, say so explicitly** (which role, why) instead of implying it passed. Honesty about a gap beats a confident false "gata".

This overrides any earlier phrasing that let "committed/rendered" stand in for "fixed for the user".
