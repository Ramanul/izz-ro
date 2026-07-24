# STATE — project execution state

> Single source of truth for "where we are". Writes are owned by the MANAGER (Claude Code):
> updated at the end of every slice and every `/review-devin`. One writer at a time.
> Executors receive this file as read-only context. Overwrite sections in place — never let
> this file grow past ~30 lines of content.

**Updated:** 2026-07-24 (slice: redundant serving — GitHub Pages mirror + monitor live, failover Worker pending token)

## Current task
`parallel-fetch` — spec `specs/parallel-fetch.md`, branch `oc/parallel-fetch`, delegated
2026-07-20 (prereq for raising LOCAL_GOLD_LIMIT past ~100). In parallel, manager research
agents are hunting REGIONAL publications; feedcheck cycle follows, then populate `regional`.
`track-cost-per-slice` — spec `specs/track-cost-per-slice.md`, branch
`devin/track-cost-per-slice`, delegated to Devin Local 2026-07-20 (metrics.log + helper CLI
for solo-vs-executor cost accounting). Awaiting Devin report, then `/review-devin`.
Jules UNBLOCKED 2026-07-24: CLI auth works (GitHub App connected), smoke session
16571763303422774183 ran; `/delegate-jules` + `tools/jules_api.py` committed. Third
executor route active. `JULES_API_KEY` in env is INVALID (401) — CLI is the route.

## Last relevant commits
- `oc/geo-categorii` MERGED (6d90543, OpenCode, 76/76, manager-verified): `regional`/`zonal`/
  `local` trio in CATEGORIES/SEED/PINNED/LABELS; 8 CJ + 7 county papers moved to `zonal`;
  GOLD loader + `pr_buzau` stay `local`; `regional` is an empty seed (sources added later).
- `oc/local-sources-priority-order` MERGED (cfccbc8, OpenCode, 72/72): gold sources
  inserted after the literal `local` block — `SOURCES.update()` appended them at the tail
  where the dict-order AI budget starved them (build 2026-07-20: 497 new, 0 pl_ processed).
- `oc/local-feeds-quality-filter` MERGED (7f9d138, OpenCode, 71/71): loader filters
  `last_signal_date >= 2026-01-01`, sorts desc; 7 dead CJ pruned. Feedcheck #2: 42/43 alive
  (vs 44/48 dead in the alphabetical pilot). Only `pl_prahova_brazi` 403 (WAF).
- `oc/local-gov-feeds-phase1` MERGED (8ccedfb): CJ feeds + GOLD CSV loader,
  `LOCAL_GOLD_LIMIT` default 35, kill-switch =0. `oc/fix-normalize-url` MERGED (a7396b3, #67).
- The CI bot commits every ~30 min — always `git pull --ff-only` before writing any spec.

## User WIP — UNTOUCHABLE
- `generator/render.py` (modified, uncommitted)
- `data/entities/salariul-minim.yaml` (modified, uncommitted)

## Blockers
- MAI WAF blocks this IP (502 on `*.prefectura.mai.gov.ro` AND www.mai.gov.ro) — do NOT
  probe MAI from this IP; retest in days or from GitHub Actions.

## Redundancy (2026-07-24, live + CI-verified)
- Mirror serving system #2 LIVE: GitHub Pages `ramanul.github.io`, synced by build.yml job
  `mirror` (deploy key = secret `MIRROR_DEPLOY_KEY`). Monitor `monitor.yml` green (10-min cron).
- PENDING (needs user): deploy the edge failover Worker `infra/failover-worker.js` —
  requires a Cloudflare token with Workers Scripts:Edit + Workers Routes:Edit, then
  `cd infra && wrangler deploy`. See infra/README-failover.md.

## Next steps
- Read feedcheck run 29715730835 results; prune dead feeds if any; watch next build.yml
  cron run time (worst case +8 min: 48 new feeds × TIMEOUT=10s, fetch_all is SEQUENTIAL).
- Phase 1 batch 2+: raise `LOCAL_GOLD_LIMIT` gradually once `oc/parallel-fetch` lands.
- SEO gaps: `og:type` on article pages, `dateModified` in JSON-LD, `lastmod` in sitemap —
  BLOCKED while `generator/render.py` is user WIP.
