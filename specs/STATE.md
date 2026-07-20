# STATE — project execution state

> Single source of truth for "where we are". Writes are owned by the MANAGER (Claude Code):
> updated at the end of every slice and every `/review-devin`. One writer at a time.
> Executors receive this file as read-only context. Overwrite sections in place — never let
> this file grow past ~30 lines of content.

**Updated:** 2026-07-20 (slice: normalize_url merged; Phase 1 local feeds delegated)

## Current task
`local-gov-feeds-phase1` — delegated to OpenCode 2026-07-20, branch
`oc/local-gov-feeds-phase1`, spec `specs/local-gov-feeds-phase1.md` (13 CJ feeds +
GOLD primării CSV loader capped by `LOCAL_GOLD_LIMIT`, default 35).
Jules CLI onboarding still blocked: 401 despite login OK + GitHub App installed —
waiting on user (key #2 / Google↔GitHub link).

## Last relevant commits
- `oc/fix-normalize-url` MERGED (a7396b3, executor OpenCode): scheme-less URLs no longer
  yield `https:///...`; closes #67; 56/56 tests. Branch deleted after merge.
- Merged-branch cleanup: local `devin/check-primarii`, `devin/institutii-si-liste`,
  `oc/fix-normalize-url` deleted (all in main).
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
- Review + merge `oc/local-gov-feeds-phase1`; validate new feeds via feedcheck.yml in CI.
- Phase 1 batch 2+: raise `LOCAL_GOLD_LIMIT` gradually (fetch_all is SEQUENTIAL — watch CI
  run time before scaling; parallel fetch is a candidate task).
- SEO gaps: `og:type` on article pages, `dateModified` in JSON-LD, `lastmod` in sitemap —
  BLOCKED while `generator/render.py` is user WIP.
