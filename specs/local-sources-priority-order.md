# Spec: local-sources-priority-order

**Goal:** The AI budget processes new items in `SOURCES` dict order (niche-first — see the
comment at the top of the dict). `SOURCES.update(load_gold_sources(...))` appends the 35
GOLD primării at the TAIL, after general/sport/economic — so with a limited AI budget they
starve (build run 2026-07-20: 497 new items, 0 pl_ processed). Fix: insert the GOLD
entries immediately AFTER the last literal source whose `category == "local"`, so they get
niche-first priority like the other local sources. Branch: `oc/local-sources-priority-order`.

## Files you may touch — NOTHING else
- `generator/config.py` (only the loader-call block after the SOURCES dict)
- `tests/test_local_sources.py` (add the ordering test)

## UNTOUCHABLE — do not touch, stage, stash, or discard
- `generator/render.py` (user WIP, uncommitted)
- `data/entities/salariul-minim.yaml` (user WIP, uncommitted)
- `.claude/commands/delegate-jules.md`, `tools/jules_api.py` (untracked, not yours)
- any other file in the repo

## Task 1 — `generator/config.py`
Replace the current block:

```python
from generator.local_sources import load_gold_sources
_GOLD_CSV = os.path.join(ROOT, "data", "primarii_lists", "gold_integrare.csv")
SOURCES.update(load_gold_sources(_GOLD_CSV, int(os.environ.get("LOCAL_GOLD_LIMIT", "35"))))
```

with insertion after the last literal `category == "local"` entry:

```python
from generator.local_sources import load_gold_sources
_GOLD_CSV = os.path.join(ROOT, "data", "primarii_lists", "gold_integrare.csv")
_gold = load_gold_sources(_GOLD_CSV, int(os.environ.get("LOCAL_GOLD_LIMIT", "35")))
# Bugetul AI proceseaza in ordinea dictului (niche-first) -> sursele locale intra
# imediat dupa blocul 'local' literal, nu la coada (altfel sunt infometate de buget).
if _gold:
    _items = list(SOURCES.items())
    _idx = max((i for i, (_k, _v) in enumerate(_items) if _v.get("category") == "local"),
               default=len(_items) - 1)
    _items[_idx + 1:_idx + 1] = list(_gold.items())
    SOURCES = dict(_items)
```

Nothing else in config.py changes. The file contains Romanian diacritics — edit
surgically, never rewrite whole sections (No mangled output).

## Task 2 — `tests/test_local_sources.py`
Add one test (keep all existing tests):
- `keys = list(config.SOURCES)`; assert every `pl_` key has a SMALLER index than the
  index of `"gsp"` (a late, non-local source) — i.e. `max(idx of pl_) < idx of "gsp"`;
- assert `pl_` count is still 35 (nothing lost by the reordering);
- assert the entry immediately BEFORE the first `pl_` key has `category == "local"`.

## Acceptance
- `python -m pytest tests/ -q` → ALL tests pass.
- `python -c "from generator import config; ks=list(config.SOURCES); pl=[i for i,k in enumerate(ks) if k.startswith('pl_')]; print(len(pl), max(pl) < ks.index('gsp'))"` → `35 True`.
- `LOCAL_GOLD_LIMIT=0` still yields zero `pl_` sources and no crash.
- `git diff --stat` shows ONLY the 2 authorized files.

## Handoff
Work on branch `oc/local-sources-priority-order` (create from current `main`). When
acceptance passes: commit with a clear message, then **STOP — no push, no merge, no PR**.
