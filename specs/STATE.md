# STATE — project execution state

> Single source of truth for "where we are". Manager-owned; updated at the end of every slice.
> Executors get it read-only. Keep it tight — when it outgrows ~40 lines of content, cut the
> settled history, not the open work. `git fetch` immediately before rewriting it.

**Updated:** 2026-07-25 (seven PRs merged; the "few articles" mystery is solved)

## OPERATING MODE — SINGLE ACCOUNT
Account A is inactive. **This account is the only writer.** No `/handoff`, no `TASKS-B.md`
parking, no waiting for another account to review or merge. §14's substance still holds:
branch, small diff, land it. Owner wants sub-agents used — but see the cost note below.

## Open
1. **PR #93** — `feed_check.py` now calls the pipeline's `_fetch_one_guarded`. 143 tests pass.
2. **`test/restore-3-primarii`** — a MEASUREMENT branch, not a proposal. Three slugs
   (`hunedoara_municipiul_brad`, `prahova_brazi`, `suceava_oras_frasin`) read as alive from the
   sandbox; `feedcheck` run from a runner decides whether they are reachable from where
   `build.yml` actually pulls. Do not merge it on sandbox evidence.
3. **Owner decision pending:** `BATCH_SIZE` 6→10 gives ~+67% articles per run but risks JSON
   truncation unless `maxOutputTokens` (2048, hardcoded) rises with it.
4. **Bug, found and NOT fixed:** ~129 official sources are re-fetched every run and expired by
   `state.expire()` in the *same* run — 76% of their content is already past the 7-day TTL when
   read. No AI cost, but wasted fetch and **falsified stats**: a log read "B: 437" when the real
   commit diff was +14 URLs.

## Settled today — do NOT re-derive
- **The "too few articles" cause was an outage, not the budget.** 30 consecutive `pipeline` runs
  failed 21 Jul 17:40 → 24 Jul 03:37 UTC with `AI DOWN — HTTP 400`: Gemini's `-latest` alias
  repointed to a 3.x model that rejects `thinkingConfig`. Fixed by `d56a8db` (#76); green since.
  The 40- and 92-article days were outage days; 198 was the recovery day, with a TTL expiry spike.
- **Real production budget:** `MAX_AI_CALLS_PER_RUN=18` and `UPGRADE_RESERVE=8` (both set in
  `build.yml`, so the 12/3 defaults in `main.py` are dead in production) → **10 calls/run for new
  articles**. Model B yields 6 articles/call, model C yields 1 (its value is de-duplication).
  Measured against 741 new items available per run: the call budget is the real ceiling.
- **Gemini's free tier is NOT saturated:** ~1000 requests/day per key against our max 216/day.
  `GEMINI_API_KEY` already supports multiple keys with failover (`gemini.py:30-42`), so a second
  key is free headroom. Full provider comparison in `specs/ai-provider-capacity.md`; Groq ranks
  first as a *failure* backup, not a capacity multiplier.
- **The sandbox CAN reach the live site and PR previews.** `https://izz.ro/` returns 200, and
  `https://<branch>.izz-ro.pages.dev/` works. Used to prove before/after on real deploys. News
  sites remain proxy-blocked — that limit is separate and still real. CLAUDE.md §16.3 rewritten.
- **feedcheck's 74 "dead" sources were not a code bug.** Same code, 15 minutes apart, gave 1 vs
  74; four of them fetched fine from here with both old and new implementations. Pattern points
  at transient host-side limiting on shared GitHub runner IPs. Unproven mechanism — do not state
  it as fact. #93 is justified anyway: checker and production could silently diverge.
- **"Alive from the sandbox" says nothing about runner reachability.** `pl_vaslui_tacuta`:
  200 with 10 entries here, 403 from runners twice. Dropped in #90 because `build.yml` pulls from
  those runners. Judge every source from the vantage point production uses.
- **Sub-agents cost ~5.6x per delivered line** (129 vs 23 tokens/100 lines, measured over 21
  slices in `COORD-DASHBOARD.md`). Worth it for genuinely parallel or noisy measurement work.
  CI is the cheapest executor — free minutes on a public repo, and the only one with real network.

## Merged today
#86 reviewers could not read code (failed on every PR) · #87 131 articles stranded on the old
geographic category · #88 cadence docs + reviewers no longer gate on quota · #89 `/surse/` shows
all 189 sources instead of 2 links · #90 freed the slot held by an unreachable source ·
#91 dark-mode contrast (305 hidden pa11y errors), sticky subnav, PWA name + its cache-bust ·
#92 agent runs quantified, report timestamped.

## Blockers
- MAI WAF blocks `*.prefectura.mai.gov.ro` from this IP (502). Retest from Actions.
- Cloudflare free plan ~500 builds/month is why `build.yml` runs every 2h (`13 */2`). Do not
  raise the frequency — see CLAUDE.md §17.
