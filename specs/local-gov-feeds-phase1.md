# Spec: local-gov-feeds-phase1

**Goal:** Wire the first pilot batch of official local-government RSS sources into the
generator: 13 new county-council (CJ) feeds as literal `SOURCES` entries, plus a CSV-driven
loader for the GOLD primării list, capped by env var. Report `data/RAPORT_SURSE_LOCALE.md`,
Phase 1. Branch: `oc/local-gov-feeds-phase1`.

## Files you may touch — NOTHING else
- `generator/local_sources.py` (NEW)
- `generator/config.py` (only the two edits described below)
- `tests/test_local_sources.py` (NEW)

## UNTOUCHABLE — do not touch, stage, stash, or discard
- `generator/render.py` (user WIP, uncommitted)
- `data/entities/salariul-minim.yaml` (user WIP, uncommitted)
- `.claude/commands/delegate-jules.md`, `tools/jules_api.py` (untracked, not yours)
- any other file in the repo

## Task 1 — `generator/local_sources.py` (new module)
Standalone module (must NOT import `generator.config` — it will be imported BY config).
One public function:

```python
def load_gold_sources(csv_path: str, limit: int) -> dict:
```

- Reads the CSV with `encoding="utf-8-sig"` (file has BOM) via `csv.DictReader`.
- Keeps only rows where `rss_ok` == `"yes"` and `rss_url` is non-empty.
- Deterministic order: sort by (`judet`, `localitate`).
- Returns at most `limit` entries; `limit <= 0` returns `{}`.
- Entry format (same shape as existing SOURCES values):
  key = `"pl_" + slug` where slug = lowercase `judet_localitate` with every char not in
  `[a-z0-9]` replaced by `_` (collapse repeats, strip edge `_`);
  value = `{"name": "Primăria " + localitate.title(), "url": rss_url, "category": "local"}`.
- If the file is missing, return `{}` (never crash the generator).
- On duplicate keys keep the first occurrence.

## Task 2 — `generator/config.py` (two edits only)
1. In the `# local` section of `SOURCES`, add these 13 literal entries (category `"local"`,
   names exactly as written, URLs copied EXACTLY — do not retype, do not strip diacritics
   from names). `cj_cluj` and `cj_timis` already exist — do NOT duplicate them:
   - `cj_arad` — CJ Arad — https://www.cjarad.ro/feed/
   - `cj_bihor` — CJ Bihor — https://www.cjbihor.ro/feed/
   - `cj_botosani` — CJ Botoșani — https://www.cjbotosani.ro/feed/
   - `cj_buzau` — CJ Buzău — https://cjbuzau.ro/feed/
   - `cj_calarasi` — CJ Călărași — https://www.calarasi.ro/feed/
   - `cj_galati` — CJ Galați — https://cjgalati.ro/feed/
   - `cj_giurgiu` — CJ Giurgiu — https://cjgiurgiu.ro/feed/
   - `cj_ialomita` — CJ Ialomița — https://cjialomita.ro/feed/
   - `cj_iasi` — CJ Iași — https://www.icc.ro/feed/
   - `cj_ilfov` — CJ Ilfov — https://cjilfov.ro/feed/
   - `cj_sibiu` — CJ Sibiu — https://www.cjsibiu.ro/feed/
   - `cj_vaslui` — CJ Vaslui — https://cjvs.eu/feed/
   - `cj_vrancea` — CJ Vrancea — https://cjvrancea.ro/feed/
2. AFTER the `SOURCES = {...}` dict closes, append:

```python
from generator.local_sources import load_gold_sources
_GOLD_CSV = os.path.join(ROOT, "data", "primarii_lists", "gold_integrare.csv")
SOURCES.update(load_gold_sources(_GOLD_CSV, int(os.environ.get("LOCAL_GOLD_LIMIT", "35"))))
```

Touch nothing else in config.py. The file contains Romanian diacritics — edit surgically,
never rewrite whole sections (No mangled output).

## Task 3 — `tests/test_local_sources.py` (new)
Tests use a small CSV written to `tmp_path` (do not depend on the real data file):
- respects `limit` (returns exactly N when more rows qualify; `limit=0` → `{}`);
- filters out `rss_ok != "yes"` and empty `rss_url`;
- keys start with `pl_`, are unique, values have `name`/`url`/`category == "local"`;
- missing file → `{}`.
Plus one integration assert: `from generator import config` succeeds and
`sum(1 for k in config.SOURCES if k.startswith("pl_"))` is `> 0` and `<= 35`.

## Acceptance
- `python -m pytest tests/ -q` → ALL tests pass (baseline today: 56 passed; yours add more).
- `python -c "from generator import config; print(sum(1 for k in config.SOURCES if k.startswith('pl_')), sum(1 for k in config.SOURCES if k.startswith('cj_')))"` → `35 15`.
- `git diff --stat` shows ONLY the 3 authorized files.

## Handoff
Work on branch `oc/local-gov-feeds-phase1` (create from current `main`). When acceptance
passes: commit with a clear message, then **STOP — no push, no merge, no PR**. Live-feed
validation is NOT your job (feedcheck runs in CI; the sandbox has no internet).
