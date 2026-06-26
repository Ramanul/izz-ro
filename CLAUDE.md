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

## 8. Design tokens
All visual styling derives from `static/styles.css` (golden-ratio φ=1.618 type scale, Fibonacci spacing, light-golden palette).
- Never hardcode colors, font sizes, or spacing in templates — reference CSS custom properties from `static/styles.css`.
- Value missing? Add a custom property; do not inline a one-off.

## 9. Bootstrap — COMPLETED 2026-06-26
Sections 3, 4, and 8 filled from real repo state. No placeholders remain.

## 10. Do NOT touch without explicit instruction
- Synthesis / attribution logic ("Model C" multi-source) and anything legal / GDPR-relevant.
- Production deploy config (Cloudflare Pages, GitHub Actions secrets).

## 11. SEO — known remaining gaps (treat as discrete slices; do NOT re-audit or rebuild)
SSR/SSG, JSON-LD, and sitemap already exist. Remaining gaps only:
- `og:type` on article pages.
- `dateModified` in article JSON-LD.
- `lastmod` in sitemap entries.

## 12. Tooling & effort
- PowerShell and Desktop Commander may run without per-command approval, within the security hook's blocklist. Reading files and running the documented dev/build/lint/test commands needs no confirmation. Destructive or irreversible actions still require confirmation.
- For substantive, multi-file tasks: enable `/effort ultracode` (session-wide xhigh + dynamic workflow orchestration). For routine single-slice edits: `/effort high` is enough and spends fewer tokens. Use an `ultrathink` turn specifically for planning before a hard slice.
