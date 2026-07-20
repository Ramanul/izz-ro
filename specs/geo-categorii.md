# SPEC — Split geographic `local` into `regional` / `zonal` / `local`

Read `AGENTS.md` in the repo root first and follow it strictly.

**Goal:** three separate GEOGRAPHIC news categories — `regional`, `zonal`, `local` — each with
its own nav entry and page, replacing the single `local` bucket. Sources are reassigned by
geographic SCOPE. `regional` starts with NO sources (its publications are added later by the
manager after a feedcheck cycle) — an empty seed category is allowed and must not fail QA.

**Verified premises** (manager checked against the repo on 2026-07-20, `main @ c2fefcb`):
- `generator/local_sources.py:14` `load_gold_sources(...)` builds `pl_<slug>` sources with
  `"category": "local"` (primărie/UAT level) — CORRECT scope, so the GOLD loader needs NO change;
  those stay `local` automatically. Verified by reading the function.
- `generator/config.py` line 90-91 injects the GOLD primării (`_gold`, `LOCAL_GOLD_LIMIT=35`).
- Hardcoded `"category": "local"` sources in `generator/config.py` (verified by `grep -n`):
  - primărie level → KEEP `local`: `pr_buzau`.
  - county level → MOVE to `zonal`: `cj_cluj`, `cj_timis`, `cj_botosani`, `cj_galati`,
    `cj_giurgiu`, `cj_ialomita`, `cj_vaslui`, `cj_vrancea` (8 county councils) and
    `zcj`, `bzi`, `ziaruldeiasi`, `pressalert`, `tion`, `bizbrasov`, `newsbv` (7 county papers).
- `generator/config.py`: `CATEGORIES` (line 104), `SEED_CATEGORIES` (109), `PINNED_CATEGORIES`
  (114), `CATEGORY_LABELS` (118) — verified via `grep -n`.
- `generator/process.py:98` `_resolve_category` pins any category in `config.PINNED_CATEGORIES`
  so the AI never re-files it onto a topic — verified.
- `generator/render.py:435,511` generate one page per `config.CATEGORIES`; `:514`
  `max(len(items), 1)` gives even an EMPTY category page 1 (so empty `regional` won't 404) — verified.
- `templates/base.html:66` `.subnav` renders every `config.CATEGORIES` entry via the `cat_label`
  filter — verified. So a category added to config appears in nav + gets a page with NO other change.
- `tests/test_config.py` asserts every source `category` ∈ `CATEGORIES`; stays valid because
  `regional`/`zonal` are added to `CATEGORIES` before any source uses them.

**User WIP — UNTOUCHABLE** (do NOT restore/stash/stage/commit these):
- `generator/render.py` (modified)
- `data/entities/salariul-minim.yaml` (modified)
- `.claude/commands/delegate-jules.md`, `tools/jules_api.py` (untracked)

**Scope — authorized files ONLY:**
1. `generator/config.py` — modify — all of the following, nothing else:
   - `CATEGORIES`: add `"regional"` and `"zonal"` next to `"local"` (keep the geographic trio contiguous).
   - `SEED_CATEGORIES`: `{"regional", "zonal", "local"}`.
   - `PINNED_CATEGORIES`: `{"regional", "zonal", "local"}`.
   - `CATEGORY_LABELS`: add `"regional": "Regional"`, `"zonal": "Zonal"` (keep `"local": "Local"`).
   - Change `"category": "local"` → `"category": "zonal"` for exactly these 15 keys:
     `cj_cluj`, `cj_timis`, `cj_botosani`, `cj_galati`, `cj_giurgiu`, `cj_ialomita`, `cj_vaslui`,
     `cj_vrancea`, `zcj`, `bzi`, `ziaruldeiasi`, `pressalert`, `tion`, `bizbrasov`, `newsbv`.
     Leave `pr_buzau` as `local`.
   - Update the two `# local — ...` comment blocks to describe the 3-tier scheme.
   - Do NOT edit `generator/local_sources.py` (GOLD stays `local`, correct). Do NOT add any source.
   Touch NOTHING else — no templates, render.py, tests, or local_sources.py.

**Verification** (run and paste real output):
1. `python -m pytest -q` — expected: all pass.
2. `python -m generator.main --render-only` — expected: exit 0; then
   `ls output/regional/index.html output/zonal/index.html output/local/index.html` — all three exist.
3. `python tools/qa_check.py` — expected: prints the QA block and ends `OK` (empty `regional`
   is a seed warning, NOT a FAIL).

**Branch:** `oc/geo-categorii` from fresh `main`. Commit on green, then STOP.
Do not push, do not merge, do not open a PR.

**Permission fallback (headless):** if a git or python command is blocked, still make the FULL
`generator/config.py` edit (the deliverable), then report exactly which commands you could not run.
The manager runs verification, creates the branch, and commits.
