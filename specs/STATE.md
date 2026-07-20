# STATE — project execution state

> Single source of truth for "where we are". Writes are owned by the MANAGER (Claude Code):
> updated at the end of every slice and every `/review-devin`. One writer at a time.
> Executors receive this file as read-only context. Overwrite sections in place — never let
> this file grow past ~30 lines of content.

**Updated:** 2026-07-20 (slice: local-gov-feeds-phase1 merged; feedcheck validation in CI)

## Current task
None in flight. Feedcheck CI run 29715730835 (manual dispatch) validating the 48 new
local-gov feeds — check results before scaling `LOCAL_GOLD_LIMIT` past 35.
Jules CLI onboarding still blocked: 401 despite login OK + GitHub App installed —
waiting on user (key #2 / Google↔GitHub link).

## Last relevant commits
- `oc/local-gov-feeds-phase1` MERGED (8ccedfb, executor OpenCode, manager-verified
  68/68 tests + acceptance `35 15` + `LOCAL_GOLD_LIMIT=0` kill-switch): 13 CJ feeds +
  `generator/local_sources.py` GOLD CSV loader. Branch deleted.
- `oc/fix-normalize-url` MERGED (a7396b3, executor OpenCode): closes #67; branch deleted,
  plus cleanup of merged `devin/*` branches.
- `gsp` RSS source RECOVERED (200 + valid XML, verified 2026-07-20) — no action needed.
- The CI bot commits every ~30 min — always `git pull --ff-only` before writing any spec.

## User WIP — UNTOUCHABLE
- `generator/render.py` (modified, uncommitted)
- `data/entities/salariul-minim.yaml` (modified, uncommitted)
- `.claude/commands/delegate-jules.md`, `tools/jules_api.py` (untracked, Jules onboarding WIP)

## Blockers
- MAI WAF blocks this IP (502 on `*.prefectura.mai.gov.ro` AND www.mai.gov.ro) — do NOT
  probe MAI from this IP; retest in days or from GitHub Actions.

## Next steps
- Read feedcheck run 29715730835 results; prune dead feeds if any; watch next build.yml
  cron run time (worst case +8 min: 48 new feeds × TIMEOUT=10s, fetch_all is SEQUENTIAL).
- Phase 1 batch 2+: raise `LOCAL_GOLD_LIMIT` gradually; parallel fetch is a candidate
  executor task before scaling past ~100.
- SEO gaps: `og:type` on article pages, `dateModified` in JSON-LD, `lastmod` in sitemap —
  BLOCKED while `generator/render.py` is user WIP.
