# STATE — project execution state

> Single source of truth for "where we are". Writes are owned by the MANAGER (Claude Code):
> updated at the end of every slice and every `/review-devin`. One writer at a time.
> Executors receive this file as read-only context. Overwrite sections in place — never let
> this file grow past ~30 lines of content.

**Updated:** 2026-07-19 (slice: OpenCode executor onboarded, smoke test merged)

## Current task
None in flight. Devin (interactive, user-driven) is researching central public
institutions' websites — coordinate before starting repo work.
Jules CLI onboarding blocked: 401 despite login OK + GitHub App installed — debugging.

## Last relevant commits
- `fix-smoke-brand` MERGED (executor OpenCode, 2nd task): smoke_live.py:57 asserted the
  pre-rebrand descriptor → CI smoke-live red since 771a5ed deploy; 1-line fix, live 36/36.
- OpenCode (Zen, `deepseek-v4-flash-free`) onboarded as second executor: `opencode.json`
  (pinned model + permission denylist), `/delegate-opencode`, generic `/review-executor`.
  Smoke test MERGED: 7 edge-case tests, 56/56 pass. Executor noted (not fixed):
  `normalize_url` on scheme-less URLs yields `https:///www...` — candidate future task.
- Local-government audit: scanners + data + category lists + `data/RAPORT_SURSE_LOCALE.md`.
  1274 GOLD primării in `data/primarii_lists/gold_integrare.csv`.
- The CI bot commits every ~30 min — always `git pull --ff-only` before writing any spec.

## User WIP — UNTOUCHABLE
- `generator/render.py` (modified, uncommitted)
- `data/entities/salariul-minim.yaml` (modified, uncommitted)

## Blockers
- MAI WAF blocks this IP (502 on `*.prefectura.mai.gov.ro` AND www.mai.gov.ro; external
  nodes get 200). Do NOT probe MAI from this IP; retest in days or from GitHub Actions.

## Next steps
- Phase 1 integration: wire GOLD primării feeds + 15 CJ feeds into `config.SOURCES` (batched).
- `gsp` RSS source returns 404 — needs a new feed URL or removal.
- SEO gaps: `og:type` on article pages, `dateModified` in JSON-LD, `lastmod` in sitemap.
