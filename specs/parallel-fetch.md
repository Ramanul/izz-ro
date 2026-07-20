# SPEC — Parallel feed fetching (unblocks scaling LOCAL_GOLD_LIMIT past ~100)

Read `AGENTS.md` in the repo root first and follow it strictly.

**Goal:** `generator/fetch.py::fetch_all` fetches sources concurrently (thread pool) instead of
sequentially, so a build with 100+ sources is bounded by the slowest feed (~TIMEOUT), not the
sum of all timeouts. Behavior and output stay identical otherwise.

**Verified premises** (manager checked on 2026-07-20, `main @ e3a0bb3`):
- `generator/fetch.py:374-384` `fetch_all` is a sequential `for key, source in config.SOURCES.items()`
  loop calling `_fetch_one(key, source, cache)` — verified by reading the function.
- `TIMEOUT = 10` (fetch.py:18); current source count is 86 (`len(config.SOURCES)`), growing as
  `LOCAL_GOLD_LIMIT` rises → worst case today ≈ 14 min sequential; STATE.md flags parallel fetch
  as the prerequisite for scaling past ~100.
- `_fetch_one` writes `cache[key]` (a per-key dict entry) and returns `(items, err)`; item order
  inside one source comes from the feed. The ORDER of sources in the returned `all_items` matters:
  the AI budget processes in that order (see `oc/local-sources-priority-order` in STATE.md) —
  parallelizing must NOT change the final ordering.
- Only stdlib is available (no new pip deps): use `concurrent.futures.ThreadPoolExecutor`.

**User WIP — UNTOUCHABLE** (do NOT restore/stash/stage/commit):
- `generator/render.py` (modified), `data/entities/salariul-minim.yaml` (modified)
- `.claude/commands/delegate-jules.md`, `tools/jules_api.py` (untracked)

**Scope — authorized files ONLY:**
1. `generator/fetch.py` — modify ONLY `fetch_all`:
   - `ThreadPoolExecutor(max_workers=int(os.environ.get("FETCH_WORKERS", "12")))`.
   - Submit `_fetch_one(key, source, cache)` per source; collect results; then extend
     `all_items` / append `dead` **in the original `config.SOURCES` iteration order**
     (collect futures in a dict keyed by source key, iterate `config.SOURCES` again to drain).
   - Cache: `_fetch_one` already writes distinct `cache[key]` entries (GIL-atomic per key);
     keep `_cache_load()` before and `_cache_save(cache)` after the pool completes.
   - A worker exception must not kill the run: wrap the future result in try/except and record
     `f"{key}: {exc}"` in `dead` (same contract as today).
2. `tests/test_fetch_parallel.py` — create — stdlib-only test that monkeypatches `_fetch_one`
   with a fake (no network; e.g. returns one item per key with a per-key delay via `time.sleep(0.01)`)
   and asserts: (a) all sources fetched, (b) `all_items` preserves `config.SOURCES` order,
   (c) one raising source lands in `dead` and doesn't break others.
Touch NOTHING else.

**Verification** (run and paste real output):
1. `python -m pytest -q` — expected: all pass (76 today + your new tests).
2. `python -m generator.main --dry-run` — expected: exits 0; the "Surse RSS care NU au raspuns"
   section may list many dead feeds in THIS sandbox (no internet here is possible) — that is
   environment, not regression; what must hold is: no traceback, summary line prints.

**Branch:** `oc/parallel-fetch` from fresh `main`. Commit on green, then STOP.
Do not push, do not merge, do not open a PR.

**Permission fallback (headless):** if a git/python command is blocked, still write the FULL
edits (deliverable), then report exactly which commands you could not run.
