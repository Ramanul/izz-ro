# STATE — project execution state

> Single source of truth for "where we are". Writes are owned by the MANAGER (Claude Code):
> updated at the end of every slice and every `/review-devin`. One writer at a time.
> Executors receive this file as read-only context. Overwrite sections in place — never let
> this file grow past ~30 lines of content.

**Updated:** 2026-07-19 (slice: STATE.md workflow wiring)

## Current task
None in flight.

## Last relevant commits
- origin/main tip: `abaa8b7` (izz-bot content update — the CI bot commits every ~30 min,
  so always `git pull --ff-only` before writing any spec).
- Live since 2026-07-18: `c3b4b81` pipeline fail-loudly, `e2ff966` gemini-flash-lite-latest,
  `18ce032` piataauto via Google News sitemap.

## User WIP — UNTOUCHABLE
- `generator/render.py` (modified, uncommitted)
- `data/entities/salariul-minim.yaml` (modified, uncommitted)
- `data/primarii_domains_all.txt`, `data/raport_complet_primarii.csv`,
  `specs/check-primarii.md` (untracked — primarii work in progress, owner: user)

## Blockers
None.

## Next steps
- `gsp` RSS source returns 404 — needs a new feed URL or removal.
- SEO gaps: `og:type` on article pages, `dateModified` in JSON-LD, `lastmod` in sitemap.
