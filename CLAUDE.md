# CLAUDE.md — izz.ro

> Operating contract for Claude Code / Cowork in this repository.
> Read fully before acting. These rules override default behavior.

## 0. Communication
- Talk to the user (Alexandru) in **Romanian**. Code, identifiers, commit messages, logs, and technical terms stay in **English**.
- Be direct and concise. No flattery, no auto-agreement. If a request is wrong or there is a better path, say so with reasons.
- State uncertainty explicitly. Never present a guess as fact.

## 1. What izz.ro is
AI-powered Romanian news aggregator. Brand promise: **"Zero Zgomot"** (Zero Noise) — synthesized, de-duplicated, clean news. The site is **statically generated** from a content pipeline (scrape -> synthesize -> cluster -> categorize -> render).

## 2. Tech stack — VERIFY, do not assume
Known: Python + Jinja2 SSG, GitHub Actions (CI/CD), Cloudflare Pages (hosting), SQLite (pipeline state).
Exact versions, libraries, and entry points are NOT verified in this file. Fill section 9 (Bootstrap) on first run. **Do not invent commands or imports.**

## 3. Repository structure — fill via Bootstrap
<<< Document the canonical layout once verified: pipeline modules, templates/, static/, output/, data/, .github/workflows/. >>>

## 4. Commands — fill via Bootstrap, then use the EXACT strings
- Install deps: <<< >>>
- Run pipeline: <<< >>>
- Build site: <<< >>>
- Serve locally: <<< >>>
- Lint / format: <<< >>>
- Type-check: <<< >>>
- Tests: <<< >>>

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
All visual styling derives from the token file (golden-ratio type scale, Fibonacci spacing). Reference: <<< path, e.g. static/css/tokens.css >>>.
- Never hardcode colors, font sizes, or spacing in templates — reference tokens.
- Value missing? Add a token; do not inline a one-off.

## 9. Bootstrap — run ONCE, first session in this repo
Before writing feature code, populate sections 3, 4, and the token path in 8 with VERIFIED values:
1. Read: README, `.github/workflows/*`, `requirements.txt` / `pyproject.toml`, any `Makefile`, and the pipeline entry point.
2. Replace each `<<< >>>` with real, tested commands and the real structure.
3. Show the user the filled sections; ask for confirmation before proceeding.
If a command or file is not found, say so — never fabricate.

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
