# SPEC — retry with backoff on HTTP 429 in feed fetching

Read `AGENTS.md` in the repo root first and follow it strictly.

**Goal:** a feed that answers `429 Too Many Requests` gets retried with exponential backoff
instead of being dropped as dead on the first try. Three real production sources are affected.

**Verified premises** (manager checked against `main` on 2026-07-24, after commit `febabdd`):
- There is NO retry anywhere in `generator/fetch.py` — verified by
  `grep -n "retry\|backoff\|sleep\|429" generator/fetch.py`: only two comment lines, both about
  the AI-side 429 defer mechanism, which is a different subsystem.
- `_fetch_one` (fetch.py ~line 347) treats HTTP errors as: `304` → healthy, no new items;
  **anything else, including 429 → dead source, immediately, no retry.**
- The feedcheck run of 2026-07-24 (GitHub Actions run `30093310671`) got `429` on exactly three
  sources: `libertatea` (`https://www.libertatea.ro/rss`), `unica` (`https://www.unica.ro/feed`),
  `bzi` (`https://www.bzi.ro/feed`). This matters in production: `build.yml` runs on the same
  GitHub runners, so the live pipeline loses those three too.
- `fetch_all` is now PARALLEL (merged `febabdd`): `ThreadPoolExecutor`, `MAX_WORKERS` from env
  `FETCH_WORKERS` (default 8), `=1` forces sequential. `TIMEOUT = 10` (fetch.py:18).
- `_fetch_one_guarded` (added `24afef9`) wraps `_fetch_one` so any exception becomes a dead
  source rather than killing the whole run. Your retry lives INSIDE `_fetch_one`, below it.
- The three affected sources are on three DIFFERENT domains, one request each — so this is
  per-IP rate limiting by the target, NOT self-inflicted by the thread pool. Do not build
  per-domain throttling; it would not address the observed failure.

**User WIP — UNTOUCHABLE:** none. Working tree is clean (`git status -s` empty, verified).

## Scope — authorized files ONLY
1. `generator/fetch.py` — modify ONLY the HTTP error handling inside `_fetch_one`:
   - On `HTTPError` with code `429` (and `503`, same class of transient refusal): retry up to
     **2 times**, sleeping between attempts. Backoff: 1s then 3s.
   - **Honour the `Retry-After` header when present** (seconds form; if it parses to more than
     15s, do NOT sleep that long — give up and report the source as dead, so one slow host
     cannot stall a worker in the pool).
   - If every attempt fails, return the SAME dead-source contract as today:
     `items, f"{key}: {exc}"`. Behaviour for every other status code is unchanged.
   - Put the retry count and delays in module-level constants next to `TIMEOUT`, so they are
     tunable without touching logic.
2. `tests/test_fetch_retry.py` — CREATE — stdlib-only, no network. Monkeypatch
   `urllib.request.urlopen` (and `time.sleep`, so the suite stays fast) and assert:
   (a) a source that returns 429 once then 200 ends up SUCCEEDING, with its items;
   (b) a source that returns 429 on every attempt lands in `dead`, and `urlopen` was called
       exactly `1 + retries` times;
   (c) a `Retry-After` larger than the cap does NOT sleep and gives up immediately;
   (d) a 404 is still dead on the FIRST try — no retries wasted on permanent errors.

Touch NOTHING else. Do not change `fetch_all`, `_fetch_one_guarded`, or the cache logic.

## Verification (run it, paste the real output)
1. `python -m pytest tests/ -q` — expected: 88 existing + your new tests, ALL passing.
2. `python tools/feed_check.py general` — expected: runs without traceback. `libertatea` may
   still be dead in this sandbox (its rate limit is per-IP); that is environment, not regression.

## Definition of done
- Both commands above run, with real output pasted in your report.
- The whole test suite is green — a retry that breaks an existing test is a REJECT.
- Commit on branch `oc/fetch-429-retry`, message in English, then **STOP**.
  No push, no merge, no PR. The manager reviews with `/review-executor`.
