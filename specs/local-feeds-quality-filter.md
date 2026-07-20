# Spec: local-feeds-quality-filter

**Goal:** Feedcheck CI run 29715730835 (2026-07-20) showed the Phase-1 pilot picks mostly
EMPTY feeds: alphabetical sort filled the batch with one county (Alba), and `rss_ok=yes`
only means "the feed responds", not "it has content". Fix selection quality in the loader
and prune the CJ entries that failed live validation. Branch: `oc/local-feeds-quality-filter`.

## Files you may touch — NOTHING else
- `generator/local_sources.py`
- `generator/config.py` (only the edits described below)
- `tests/test_local_sources.py`

## UNTOUCHABLE — do not touch, stage, stash, or discard
- `generator/render.py` (user WIP, uncommitted)
- `data/entities/salariul-minim.yaml` (user WIP, uncommitted)
- `.claude/commands/delegate-jules.md`, `tools/jules_api.py` (untracked, not yours)
- any other file in the repo

## Task 1 — `generator/local_sources.py`
Change `load_gold_sources` signature to:

```python
def load_gold_sources(csv_path: str, limit: int, min_date: str = "2026-01-01") -> dict:
```

- Keep existing filters (`rss_ok == "yes"`, non-empty `rss_url`), ADD: keep only rows
  where `last_signal_date` is non-empty AND `>= min_date` (plain ISO string compare).
- Change ordering: sort DESCENDING by `last_signal_date`; tie-break ASCENDING by
  (`judet`, `localitate`) so the result stays deterministic. Then cap at `limit`.
  (Rationale: freshest feeds first = national spread + real content; the suspiciously
  round `2026-01-01` artifact dates sink to the bottom on their own.)
- Everything else (BOM encoding, missing file → `{}`, `limit <= 0` → `{}`, `pl_` keys,
  duplicate-key first-wins) stays as is.

## Task 2 — `generator/config.py`
1. REMOVE these 7 CJ entries (failed live feedcheck 2026-07-20, run 29715730835):
   `cj_arad`, `cj_bihor`, `cj_ilfov`, `cj_sibiu` (HTTP 200 but 0 entries),
   `cj_buzau` (502), `cj_iasi` (timeout), `cj_calarasi` (frozen, newest item 2022).
2. Directly above the remaining CJ block, add ONE comment line:
   `# CJ cazuti la feedcheck 2026-07-20 (nu re-adauga fara re-test): arad/bihor/ilfov/sibiu=GOL, buzau=502, iasi=timeout, calarasi=inghetat 2022`
3. Do NOT touch the `load_gold_sources` call (default `min_date` applies automatically).
Keep: `cj_botosani`, `cj_galati`, `cj_giurgiu`, `cj_ialomita`, `cj_vaslui`, `cj_vrancea`
(all had fresh content). The file contains Romanian diacritics — edit surgically, never
rewrite whole sections (No mangled output).

## Task 3 — `tests/test_local_sources.py`
Update existing tests for the new signature/ordering and add:
- rows older than `min_date` (or with empty date) are excluded;
- ordering is by `last_signal_date` DESC (a fixture row with a newer date must be picked
  over an older one even when the older sorts first alphabetically);
- tie on date → ascending (`judet`, `localitate`).
Keep the integration assert (`pl_` count `> 0` and `<= 35`); relax any test that assumed
alphabetical pick.

## Acceptance
- `python -m pytest tests/ -q` → ALL tests pass.
- `python -c "from generator import config; print(sum(1 for k in config.SOURCES if k.startswith('pl_')), sum(1 for k in config.SOURCES if k.startswith('cj_')))"` → `35 8`
  (8 = cluj + timis + the 6 kept above).
- `python -c "from generator.local_sources import load_gold_sources; import os; s=load_gold_sources(os.path.join('data','primarii_lists','gold_integrare.csv'), 35); import collections; print(len(collections.Counter(k.split('_')[1] for k in s)))"` → prints a number `>= 10` (county spread, not one county).
- `git diff --stat` shows ONLY the 3 authorized files.

## Handoff
Work on branch `oc/local-feeds-quality-filter` (create from current `main`). When
acceptance passes: commit with a clear message, then **STOP — no push, no merge, no PR**.
