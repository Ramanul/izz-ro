# Spec / measurement report — AI budget yield & the 25-vs-286 article variance

**Status: MEASUREMENT ONLY. Nothing in this repo was changed by this investigation.**

**Date:** 2026-07-25. **Author context:** requested by owner after observing "25 articles by
noon" vs a range of 25-286/day over the preceding week, measured directly in
`data/articles.json`.

## 1. Where the AI calls go (traced through the code)

`generator/main.py:run()` (line 133): `budget = int(os.getenv("MAX_AI_CALLS_PER_RUN", "12"))`.
`reserve = min(int(os.getenv("UPGRADE_RESERVE", "3")), budget)` (line 136).
Two consumers, in order:

1. **`process_new(new_items, provider, budget - reserve, existing)`** (main.py:137) — the
   producer of *new* articles. Inside (`main.py:27-81`):
   - Official sources (`pl_*`, `cj_*`, `pr_*`) are split off first and processed by
     `process_official()` (process.py:174) — **zero AI calls**, confirmed correct, not
     re-litigated per the brief.
   - Synthesis candidates (Model C, ≥2 distinct-domain sources on the same event,
     `cluster.is_synthesis_candidate`, `config.CLUSTER_MIN_SOURCES = 2`) go **first**, one AI
     call each (`process.process_cluster`, main.py:60-68), until budget runs out.
   - Remaining singles (Model B) go in batches of `config.BATCH_SIZE = 6`, **one AI call per
     batch** (`process.process_batch`, main.py:71-76), until budget runs out. Leftover singles
     beyond the budget are simply not returned this run.
2. **`upgrade_fallbacks(combined, provider, budget - used)`** (main.py:143) — re-processes
   *already-published* articles still on deterministic fallback text or a stale
   `prompt_version`, **one AI call per article** (`process.process_single`, single-item, not
   batched — main.py:94-104). This does not add new articles, it improves existing ones.

## 2. Measured yield per call

Measured by running `python -m generator.main --dry-run` instrumented with a fake AI provider
that always succeeds (real key unavailable in this sandbox — see §7), so the exact
`process_new`/`upgrade_fallbacks` selection logic runs unmodified against **live fetched RSS
data** (185-192 new items across two runs, 2026-07-25). Script:
`/tmp/.../scratchpad/measure_budget.py` (kept out of the repo, not a deliverable).

| Model | Calls → articles | Measured yield |
|---|---|---|
| **B** (batch) | 1 call = 1 batch of `BATCH_SIZE=6` | **exactly 6 articles/call** when the batch succeeds fully (upper bound; a real API can return a partial/malformed array — see §3) |
| **C** (synthesis) | 1 call = 1 cluster | **exactly 1 article/call**, but folds ~2.5 raw source-items into that one article on average (measured: 2 clusters, 5 folded sources) — this is a *dedup* win, not a *volume* win |
| **upgrade_fallbacks** | 1 call = 1 article | **1 article/call**, not batched (confirmed live: 2026-07-25 06:26 UTC run log: "Upgrade fallback → AI: 8 articole vechi reprocesate" for 8 calls) |

**So: Model B is 6× more article-yield per call than Model C or an upgrade call.** C's value is
dedup quality (§7 "one axis, one home" / Zero Zgomot), not throughput — treat it as a fixed cost,
not a lever.

With production settings (see §3): 10 calls into `process_new`, typically 2 go to C, 8 to B →
**8×6 = 48 new AI-B articles/run** is the real steady-state ceiling, not a bigger number.
Confirmed against actual item supply: production log (2026-07-25T06:26 UTC) reports 741 new
items fetched that run — **the AI-call budget, not source volume, is the binding constraint**
by a huge margin (budget covers ~50-60 of 741 available items/run).

## 3. The 12-vs-18 verdict

**Production always runs at 18/8, never at the code's literal 12/3 default.** Verified directly
from a live CI job's env block (`get_job_logs`, run `30147499588`, step "Ruleaza pipeline"):
```
MAX_AI_CALLS_PER_RUN: 18
UPGRADE_RESERVE: 8
```
`build.yml:55-56` sets both unconditionally (`workflow_dispatch.max_ai_calls` defaults to the
string `'18'` when empty, and `UPGRADE_RESERVE` is hardcoded `"8"` with no override input at
all). The code's `os.getenv(..., "12")` / `os.getenv(..., "3")` defaults are **dead in
production** — they only apply if someone runs `python -m generator.main` locally without
setting the env vars (e.g. this sandbox's `--dry-run` run did exactly that).

This is not a bug, but it is a real documentation trap: reading `main.py` alone gives the wrong
number for both budget (12 vs actual 18) and reserve (3 vs actual 8), which is exactly the kind
of mismatch CLAUDE.md §17 was written to stop people re-diagnosing. Effective production
`process_new` budget is **18 − 8 = 10 calls/run**, not 9 (12−3) and not 15 (18−3).

## 4. Queue depth & TTL (7-day, `config.ARTICLE_TTL_DAYS`)

Checked the live committed state (`data/articles.json`, 1096 articles): only **8 articles** are
currently past the 7-day cutoff — TTL expiry of *genuinely-new* content is **not** the current
bottleneck. But see §6 for a large, separate TTL interaction found in the official-source path.

`main.py`'s own docstring claims unprocessed items are "reluat la rularea următoare" (picked up
again next run) — true in the common case, but **not guaranteed**: `fetch.py`'s conditional-GET
cache (`CACHE_MAX_AGE_H = 3`) means a source that returns **HTTP 304** contributes **zero items**
to that fetch (`fetch.py:380-381`), including any item that missed the AI budget last time and
was never added to state. If the source's feed doesn't change again within the ~3h cache window,
that item is invisible to the pipeline for up to ~1-2 cron cycles, not "next run" as the comment
implies. Not independently quantified (would need instrumenting live cache hit/miss over several
real cron cycles); flagged as a caveat, not verified as a live problem right now.

## 5. The measured cause of the 25 → 286 variance

The owner's numbers reproduce exactly from the live state
(`published`-date histogram, `data/articles.json`, run 2026-07-25):

| Date | Articles | Note |
|---|---|---|
| 2026-07-19 | 286 | normal, full day |
| 2026-07-20 | 229 | normal, full day |
| 2026-07-21 | 101 | outage started 17:40 UTC (see below) — partial day |
| 2026-07-22 | 40 | **entire day inside the outage** |
| 2026-07-23 | 92 | **entire day inside the outage** |
| 2026-07-24 | 198 | fix landed ~05:20 UTC, recovered ~06:36 UTC — partial-outage day |
| 2026-07-25 | 25 (as of last available data, 07:00 UTC) | normal operation, partial day |

**Root cause of the 40/92 collapse, confirmed via GitHub Actions run history
(`mcp__github__actions_list` / `get_job_logs`, repo `Ramanul/izz-ro`, workflow `pipeline`):**
30 consecutive scheduled runs failed from **2026-07-21T17:40 UTC to 2026-07-24T03:37 UTC**
(~60 hours). Every failing run's log shows the same signature:
```
!! AI DOWN — toate cele 11 apeluri AI au esuat. NIMIC nou publicat.
   Ultima eroare: HTTPError: HTTP Error 400: Bad Request
```
Root cause (already diagnosed and fixed in-repo, see `generator/providers/gemini.py:48-51`
comment): the `gemini-flash-lite-latest` alias silently repointed to a Gemini 3.x model that
rejects the `thinkingConfig` field with 400 INVALID_ARGUMENT. Because `main.py`'s `ai_down` check
(`main.py:152`, `sys.exit(1)` at `main.py:232`) correctly aborts *before* the commit step
(confirmed: job step "Comite starea" shows `conclusion: skipped` on every failing run), **zero
state commits happened for the full 60 hours** — this is the systemic-failure guard working
exactly as designed, not a new bug. Fix `d56a8db` ("drop thinkingConfig rejected by Gemini 3.x
models") landed 2026-07-24 05:20 UTC; the next run (06:36 UTC) succeeded and the streak has been
100% green since.

**Side effect, also measured:** the recovery run's commit shows total known articles dropping
1319 → 988 in one step (`data/articles.json` history via `git show <sha>:data/articles.json`) —
the 60-hour-old backlog crossed the 7-day TTL and got purged in bulk the moment the pipeline
resumed, right as fresh production needed to rebuild from a smaller base. That compounding is
why 2026-07-24 (198) undershoots a normal day (229-286) despite recovering early in the day.

**Is 2026-07-25's "25 by noon" itself abnormal?** Compared hour-by-hour cumulative
`published`-date counts (all times UTC) on three fully-healthy days vs today:

| Day | cumulative by 07h | cumulative by 09h (≈ noon Bucharest) |
|---|---|---|
| 2026-07-19 | 73 | 97 |
| 2026-07-20 | 72 | 90 |
| 2026-07-24 | 43 | 66 |
| **2026-07-25** | **25** (last data point available) | *(day not complete in this checkout)* |

25 by 07h is noticeably below the 43-73 range other days show at the same hour — roughly
2-3× lower — even though every run since the 2026-07-24 recovery has been green
(`ai_down: false` in every subsequent job log checked). This could not be fully isolated in the
time available (see §8): plausible non-exclusive contributors are (a) still working off a
thinner post-outage item backlog upstream at source sites, (b) ordinary day-to-day news-volume
variance, (c) the fixed ~48-article/run AI-B ceiling applies every run regardless of how much
raw material is available, so if fewer runs so far today landed with typically-sized batches,
the shortfall shows. **Not attributable to budget misconfiguration** — the same 18/8 budget that
produced 286 articles on 2026-07-19 is running today.

## 6. Bug found — reported, NOT fixed (per instructions)

**The 129 official/local-government sources (`pl_*`/`cj_*`/`pr_*`, of which up to
`LOCAL_GOLD_LIMIT=120` from `data/primarii_lists/gold_integrare.csv`) are re-scraped and
re-"published" every single 2h run, then immediately deleted by `state.expire()` in the *same*
run, because most of what they serve is already older than the 7-day TTL at scrape time.**

Measured two ways:
1. **Live sample:** fetched 60 of the 129 official sources directly (`generator.fetch`); of 445
   items returned, **338 (76%) already had a `published` date past the 7-day TTL cutoff** —
   these are static municipal pages (licitații, anunțuri de atribuire, dezinsecție…) with real
   dates from weeks ago, scraped fresh because `_fetch_html_list`/`_fetch_sitemap_news` have no
   per-item persistent cache (only the RSS path uses `feed_cache.json`).
2. **Live commit diff:** compared `data/articles.json` before/after a real production commit
   (`159733c` → `08c996f`, 2026-07-25 06:26 UTC run). The run's own printed stats claimed
   `noi: 741 | B: 437 | C: 9` (446 "processed"), but the actual net change in committed state was
   **+14 URLs** (14 added, 28 removed). The ~430-item gap is items added and expired in the same
   `run()` call — `main.py:141-144` merges `processed_new` into `combined` and then immediately
   calls `state.expire(combined)` before saving, so anything already stale on arrival never
   survives to be visible.

**Impact:** zero AI budget lost (confirmed — official items bypass AI entirely, correctly). The
real costs are (a) wasted fetch/CPU time scraping ~120+ static pages every 2 hours for content
that can never be published, and (b) **the pipeline's own stats line is actively misleading** —
"B: 437" reads as a highly productive run when 96% of it evaporates before the commit. This
nearly derailed this investigation's own read of the yield numbers; a future diagnosis session
reading `main.py` logs at face value would draw the wrong conclusion the same way. Not fixed —
flagged per the brief ("dacă găsești un bug clar, raportează-l separat, fără să-l repari").

## 7. Three ways to raise articles/day without more AI quota

All three keep `MAX_AI_CALLS_PER_RUN` and `UPGRADE_RESERVE` at their current effective production
values (18/8) — none of them ask for more Gemini quota. All three need empirical verification
(clustering-tuner / pipeline-runner / a real quota-metered run) before landing — not done here,
per the brief ("NU implementa nimic").

### A. Raise `config.BATCH_SIZE` (currently 6)
Direct multiplier on Model B yield: at `BATCH_SIZE=10`, the same 8 batch-calls/run become
**8×10 = 80 AI-B articles/run** instead of 48 (+67%), for the identical 18/8 call budget.
**What could break:** `providers/gemini.py:52-55` hardcodes `maxOutputTokens: 2048` for *every*
call, batch or not. A bigger JSON array response risks truncation mid-array; `_parse_json_array`
(process.py:148) will then fail to parse the whole response, and **every** item in that batch
(not just the overflow) is dropped for the run — a straight regression vs. today, and it could
silently get *worse* the more items are packed in. Needs `maxOutputTokens` raised in step with
`BATCH_SIZE` and a real-quota test (clustering-tuner doesn't cover this; use pipeline-runner /
`clustering-tuner`-style before/after sampling) checking teaser quality doesn't thin out with
more items sharing one prompt — §7 (Zero Zgomot) is explicit that a volume gain bought with
truncated or generic output is not acceptable.

### B. Lower `UPGRADE_RESERVE` from 8
Every call moved from reserve to `process_new` is worth **6 new B-articles vs. 1 upgraded
article** (measured ratio, §2) — a steep asymmetry in favor of `process_new` purely on an
articles/day metric. E.g. reserve 8→4 frees 4 calls/run → **+24 AI-B articles/run** (+50% over
the current 48/run ceiling). **What could break:** the reserve exists specifically to drain the
fallback/stale-prompt backlog that piles up after exactly the kind of outage measured in §5 — an
outage that ended barely 24h before this measurement. The 2026-07-25 06:26 run just spent its
full reserve (8/8) upgrading 8 real fallback articles; QA currently reports 0% fallback content,
meaning the backlog is freshly drained, not proven stable. Cutting the reserve now removes the
safety margin right after the exact failure mode it exists for. If done, cut moderately (8→5 or
6, not to 0) and re-check `tools/qa_check.py`'s "fallback (fara AI)" percentage over a few days
before cutting further.

### C. (Rejected, documented for completeness) Reduce C-cluster priority to free calls for B
Model C's absolute priority (main.py:59-68) can cost 2-9 of the 10 `process_new` calls/run on
clusters that only replace 1 article each. Redirecting some of that budget to B batches (6
articles/call vs. C's 1) looks attractive on a pure volume metric, but it means genuinely
multi-sourced events would publish as separate near-duplicate B articles instead of one
synthesized story — directly the "one axis, one home" / dedup promise in §7. **Rejected**: this
is exactly the kind of quality-for-volume trade the brief says to call out as unacceptable, not
propose.

## 8. What could not be measured here

- **Real (non-simulated) AI success/failure rate per batch** — no working `GEMINI_API_KEY` in
  this sandbox (checked: unset). §2's yields assume a 100%-success fake provider; real Gemini
  calls do occasionally fail (429/503, see `providers/gemini.py` retry logic) or return
  partially-mapped batch arrays, which would lower the *effective* (not theoretical) B yield
  below 6/call. Not quantifiable without production log mining beyond what §5/§6 already pulled.
- **Whether 2026-07-25's below-normal pace (§5) continues past 07:00 UTC** — this sandbox's repo
  checkout is a snapshot; could not watch the day complete.
- **The 304-cache retry gap (§4)** — plausible from reading the code, not observed live across
  multiple real cron cycles in this session.
- **Full-population check of the 76% stale-official figure (§6)** — measured on 60 of 129
  sources (445 items) for time budget reasons, not all 129.
