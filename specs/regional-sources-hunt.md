# SPEC — populate the empty `regional` category (research + feed verification)

Read `AGENTS.md` and `CLAUDE.md` in the repo root first and follow them strictly.

**Executor:** account B (Claude Code web / cloud). **Branch:** `claude/regional-sources` from `main`.
**Why account B:** this is network research, and several targets block the owner's home IP
(see Blockers). A cloud runner has a different IP. Nothing here needs the local machine.

**Goal:** produce a VERIFIED list of Romanian news feeds whose editorial scope is REGIONAL —
larger than one county, smaller than national — so the manager can populate the category.
You produce data, not config changes.

**Verified premises** (manager checked on 2026-07-24, `main @ febabdd`):
- `regional` exists in `CATEGORIES` (config.py:106), `SEED_CATEGORIES` (110), `PINNED_CATEGORIES`
  (115) and `LABELS` (123) — verified by `grep -n regional generator/config.py`.
- `regional` has ZERO sources. Verified by counting `config.SOURCES`: local 36, zonal 15,
  extern 6, general 5, economic 4, lifestyle 4, politic 4, cultura 3, sport 3, auto 2,
  sanatate 2, discounturi 1, tech 1 — total 86, `regional` absent. So its page renders empty.
- The three geographic scopes were split by `oc/geo-categorii` (6d90543):
  `local` = primărie / UAT level · `zonal` = county level (CJ + county papers) ·
  `regional` = ABOVE county — multi-county publications, historical or development regions
  (Transilvania, Moldova, Banat, Oltenia, Dobrogea, Muntenia, Crișana–Maramureș).
- `LOCAL_GOLD_LIMIT` (default 35) governs only the `pl_*` GOLD loader, NOT this category.
- `fetch_all` is now PARALLEL (merged febabdd), so added sources cost far less build time.

## Scope — authorized files ONLY
1. `data/regional_candidates.csv` — CREATE. Columns, in this exact order:
   `slug,name,url,region,http_status,last_item_date,items_count,notes`
2. `specs/regional-sources-hunt-report.md` — CREATE. Findings, method, and what you rejected.

Touch NOTHING else. Do NOT edit `generator/config.py` — wiring the sources in is the manager's
step, on `main`, and editing it here would collide (CLAUDE.md §14: one writer on main).

## Method
- Find candidates whose masthead covers MORE than one county. A single-county paper is `zonal`
  and does NOT belong here — when in doubt, reject and say why in `notes`.
- For each candidate, find the real RSS/Atom URL and FETCH IT. Record the actual HTTP status,
  the date of the newest item, and how many items the feed returns.
- **Apply the quality filter already used for local feeds** (`oc/local-feeds-quality-filter`,
  7f9d138): a feed whose newest item predates 2026-01-01 is DEAD — record it with its date, but
  mark it rejected. That pilot found 44/48 alphabetically-chosen feeds dead; assume most
  candidates fail and let the data say so.
- Aim for 8–15 VERIFIED-ALIVE feeds with reasonable geographic spread. Fewer, alive and truly
  regional, beats a long list of dead or mislabeled ones.
- Note in `notes` anything that returned 403/WAF — the manager needs to know which are blocked
  by IP rather than dead, since retrying from a different network may succeed.

## Acceptance criteria
- `data/regional_candidates.csv` exists, parses as CSV, one header row + one row per candidate.
- EVERY row's `http_status` and `last_item_date` come from a fetch you actually performed —
  no guessed or remembered values. If you could not fetch one, put `unknown` and say why.
- The report states: how many candidates examined, how many alive, how many rejected and on
  what grounds (dead / single-county / no feed / blocked), and lists rejected ones by name.
- `python -m pytest tests/ -q` still passes (88 tests) — you changed no code, so this is a
  regression check that nothing leaked outside the authorized files.
- Commit on `claude/regional-sources`, message in English, then STOP. No push to `main`,
  no merge, no PR. The manager reviews with `/review-executor` and wires the sources in.
