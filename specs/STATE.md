# STATE — project execution state

> Single source of truth for "where we are". Manager-owned; updated at the end of every slice.
> Executors get it read-only. Keep it tight — when it outgrows ~40 lines of content, cut the
> settled history, not the open work. `git fetch` immediately before rewriting it.

**Updated:** 2026-08-03 12:30 (account A — #123 and #124 MERGED: the AI budget spends all 18 calls, and no listing page is orphaned any more)

## READ FIRST — a bot-challenge page served with HTTP 200, triggered by SWEEP VOLUME (2026-08-02)

**The cause is established, with response bodies, not inferred.** Earlier versions of this section
blamed the GitHub runner IP and recommended a proxy or a self-hosted runner. **That was wrong —
do not act on it.** Two hypotheses were tested and killed before the real one held up:

- ~~"runner IPs are blocked"~~ — `silent_probe` from a runner, 10 sources: **10/10 fine**. Same
  runner infrastructure, 75 sources: **74/75 fine**. The IP is not blocked.
- ~~"the conditional-request cache returns 304s"~~ — the 10:05 production run had a cache 3h23m
  old, past `CACHE_MAX_AGE_H = 3`, so it sent unconditional requests, and still read 852.
  `feed_check.py` never passes a cache at all (`_fetch_one_guarded(key, src)`, third arg omitted).

**What actually happens.** Probe all 189 sources sequentially from a runner and it reproduces:
**74 with 0 entries**, matching feedcheck's 75. Same infrastructure, same script, ~20 minutes after
the 75-source run that produced 1. The variable is **sweep volume**, not IP and not time.

72 of the 74 return a byte-identical page, HTTP **200**:

```text
<!DOCTYPE html><html lang="en"><head>... <script>(function(){
  setTimeout(function(){ window.location.reload(); }, 5000); }())</script>
<title>One moment, please...</title> <style>.spinner{...
```

A JS bot-challenge interstitial that auto-reloads after 5 s. `feedparser` parses it as valid HTML
with zero entries and **no error** — which is exactly why nothing ever reported it.
**65 of the 74 are served by `openresty/1.31.1.1`**, one shared hosting stack; the rest are
3× Apache, 3× cloudflare, 1× `openresty/1.29.2.3`. Affected set: 64 of the 120 `pl_*` municipal
feeds (56 are fine) plus `bookhub bizbrasov ziarultransilvaniei zch stirilemoldovei stirimuntenia
cronicaolteniei stirileolteniei piataauto contributors`.

**The loss itself is real and measured with the production function**, `fetch_all()` — not a
reimplementation, and not two different metrics compared by accident:

```text
local, cold cache : 1428 articles, 186/189 sources with >=1, 3 dead, 164 capped at 8
production        :  860 (03:47) / 861 (06:42) / 852 (10:05)
```

The same 189-source sweep from the owner's residential IP loses 3 sources; from a runner it loses
74. So IP reputation sets the *threshold*, but **volume is the trigger** — which makes this a
fetch-pacing problem in `generator/fetch.py` (`MAX_WORKERS = 8` against 189 sources, 65 of them on
one host), **not** the deploy-topology decision the previous version of this section claimed.
→ ~~"a back-off-and-retry may pass it"~~ — **TESTED, AND FALSE.** With a 6 s wait, past the page's
own reload timer, **40 of 40** sources got the same interstitial again. The quota is time-windowed.
Do not re-open this.
→ **The grouping key cannot be host name or IP.** The 66 challenged domains resolve to many
different addresses (checked 30: `37.143.163.59` x3, `89.39.83.125` x2, the rest distinct) — one
Romanian hosting provider on many IPs behind one WAF. Only the `Server` header identifies it, and
that is known only from a response, i.e. from the previous run.
→ **THE FIX IS [PR #113](https://github.com/Ramanul/izz-ro/pull/113) — MERGED, owner approved.** (a) reports these as `challenge anti-bot servit cu 200 (sursa NU e moarta)` instead of
the "feed gol" label #110 gave them, which invites deleting good sources from config; (b) adds
`_HostPacer` — caches the `Server` header per source, spaces requests sharing a provider, only for
groups >= `FETCH_PACE_GROUP_MIN` (10), default 2.0 s, `FETCH_PACE_S=0` disables it; (c) deletes
`claude-docs-review.yml` on the owner's call. 19 new tests, 281 pass.
→ **WHAT #113 DOES NOT ESTABLISH:** 2.0 s is reasoned, not measured — today's probing consumed the
provider's quota, so there was no clean window. Compare `Articole citite` across a few runs and
tune `FETCH_PACE_S`.
→ **CAVEAT when reading the next production runs:** today's probes spent that quota. A low
`Articole citite` on the next `build.yml` may be my measurements, not a regression.
→ #110 is what made any of this visible: before it, a source answering 200 with an unparseable
body was dropped silently. The next production run prints the real list.

## OPERATING MODE — owner active on ACCOUNT A (2026-08-02)
Owner was on account B, hit the usage limit mid-work on three draft PRs, switched to account A
(this local session) to continue. Per §14 (amended): **the account the owner is working from
merges** — that is account A now. All three PRs landed here; see "Merged 2026-08-01/02".

## SIRUTA — sourced, MEASURED, village-level BLOCKED on county-aware matching (2026-08-02)
Groundwork committed (branch `claude/siruta-groundwork`, NOT merged): `data/siruta_raw.csv`
(official SIRUTA via github.com/andrei-furnica/localitati-romania → data.gov.ro; cp1250, `;`,
comma decimals) + `tools/build_gazetteer.py`. **geo.py is UNCHANGED — still the safe primării CSV.**
- SIRUTA holds 42 counties + 3181 UATs + 13755 villages. Of villages, 8736 names are globally
  unique, ~5019 collide (POIANA×38, "SATU NOU"×42 — hopeless without source county).
- **Measured on the live corpus: adding even the unique villages REGRESSES the gate.** 49 articles
  wrongly became `local`: "Saturn retrograd" (Saturn is a Black-Sea resort/village), the horoscope,
  "Senatul... decarbonizarea", "FCSB vs FK Auda". A unique village name can still be a common word.
- Conclusion: village-level geo needs **source-county disambiguation** (a Vrancea paper's "Poiana"
  = Poiana-Vrancea), i.e. plumb the source's county into `geo.clasifica`. That is the real Slice 2.
  Naive addition is a regression, so it was NOT shipped (owner methodology: measure, don't ship
  below the bar). UAT-only switch also churned 155 classifications vs the primării CSV — not a
  clean win either. Reference features (Bucegi, Ceahlău, Dunărea) are a separate small curated list.

## Lead photos now come from the LOCALITY — PR #101 (2026-08-02)
Branch `claude/scraping-romanian-public-data-u63sqz`. **0 → 129 real photos**; before, every
article carried a generated icon cover. Full rationale, measurements and the Wikidata/licence
details live in `specs/locality-lead-photos.md` — read that, not this, before touching it.
Three rules that bite if forgotten:
- **County match is mandatory, no fallback**, and renditions are named by **QID, not name**:
  4 distinct Costești / 3 Ungheni / 2 Zărnești exist, all with different photos.
- **`license_free` must keep rejecting CC-BY-NC and CC-BY-ND** — we crop, so we make derivatives.
- **Bump `MISS_VERSION`** when adding a search route, or cached misses hide it on all content.
CLAUDE.md §13's audit baseline was stale (home Perf 89, July) and is now **re-recorded from 5
runs per page**: home 80, article 88, A11y/BP/SEO 100, pa11y 0, with the Lighthouse/pa11y/
Chromium versions written to `.audit/versions.txt`. `audit.sh` no longer picks the article page
with `find | head -1` (it scored different pages across runs); pin it with `ARTICLE_PATH=` for any
before/after. **The "one extra run read home 84" note is superseded** — see CLAUDE.md §13: six runs
across two revisions show a two-state CLS switch (~0.156 → home 83-84, 0.272 → home 76), not a
spread. Run 3+ repetitions per revision and compare medians; one pair proves nothing under ~8 points.
`data/localities.json` (3179 UAT, county labels + `localities.match`) overlaps SIRUTA Slice 2 —
reuse it rather than building a second county matcher.

## OWNER ANSWERS 2026-08-02 — treat as decided, do not re-ask
- **Dark mode: "merge".** Open 0 is CLOSED. Do not spend another session on it.
- **7 regions**, not 9. He says he answered this long ago. Feed it into SIRUTA Slice 2 / the map.
- **Photos: "totul legal cu cat mai multe poze".** The policy is maximise coverage WITHIN the
  consent rules of §18 — never relax the licence checks to get more photos.
- **The salary calculator is BROKEN and he noticed:** "cand pun cifre nu face calculul". Measured
  on live, https://izz.ro/ghiduri/salariul-minim/ : `calcSalariu` undefined, `#calc-results` empty.
  `_render_calc_salariu` emits an inline <script> plus oninput=/onclick=, and CSP is
  `script-src 'self'` with NO 'unsafe-inline'. **It has never worked in production.** Partial fix
  in #115 (external static/calc-salariu.js); wiring listed in that commit message, including
  adding it to `_asset_ver` or §16.2's immutable cache hides the fix.
- **He did not understand items phrased as CLS / og:image / SHA pinning.** Explain consequences in
  plain language before asking him to decide anything. That is a lesson about how to ask, not
  about him.

## 2026-08-03 — THE SITE WAS PUBLISHING A STALE MINIMUM WAGE. Do not re-derive this.
#119, #120, #121 merged. What matters for the next session:
- **Salariul minim is 4.325 lei from 1 July 2026** — [HG 146/2026](https://legislatie.just.ro/Public/DetaliiDocument/308231),
  read on the portal, art. 1; art. 2 repeals HG **1.506/2024** (the entity had it as "1506/2025").
  The site served 4.050 for a month. `verificat: true` now — the primary act was read.
  **The calculator took the personal deduction as 20% of that stale figure**, so it computed wrong
  net pay for the whole time it worked. `_SALARIU_MINIM_FALLBACK` and the entity are now tied by
  `test_fallback_nu_diverge_de_entitate` — they drift with nothing visibly breaking.
- **Alocatia: 719 / 292 lei, indexation suspended** (art. XXV, Law 141/2025) against 1.019 / 794
  published. `verificat` STAYS false and the yaml says why: the primary act could not be read —
  `legislatie.just.ro` serves Law 61/1993 in its 1999 republished form, art. 3 still "3.500 lei",
  pre-denomination. Its history table was deleted, not corrected; it started from the same
  contradicted numbers. **Do not set `verificat: true` here without reading the act.**
- **OPEN, owner's call (§10):** at 4.325 brut the calculator returns **2.616**, sources say
  **~2.699**. The flat 20% deduction understates art. 77 of the Fiscal Code at low incomes. The
  guide text now says "ordin de mărime, nu suma exactă din fluturaș" — accurate, but the formula
  is still approximate. Fixing it is a fiscal-rules decision, not a data one.
- **`published` sort: the refactor was NOT needed and was not done.** Measured: 1736/1736 entries
  are `+00:00`, because both parsers end in `astimezone(timezone.utc)`. `tests/test_published_is_utc.py`
  guards the invariant instead. Rewriting the three sorts to `datetime` would have hidden the real
  exposure — order would look right while mixed offsets leaked into `datePublished` and the feed.
- **CodeRabbit was right twice and wrong twice on the same PR.** Right: the stale wage, the
  allowance bands. Wrong: it asked to drop the 15-year contribution rule from `pensia-minima`
  (real — no minimum stage, no pension right, so nothing to top up), and to make a test assert
  `verificat: true` (a test asserting the editorial gate empties it of meaning). **Verify its legal
  claims before applying them; it is confident in both directions.**

## Open
0. **DARK MODE — mechanics now CONFIRMED ON LIVE (#106). Still open only for the owner's own
   "nu merge" to be re-tested by him.** Do not spend another session reproducing it blind.
   History: the owner merged #96, was asked to press ☾ and check the theme survives a refresh,
   and replied **"nu merge"**; no detail was gathered before that session ran out of budget.
   **Likely what he saw (INFERENCE, not established):** #96 did fix the mechanics, but the button
   kept a hardcoded `☾` glyph plus `title="Mod întunecat"` and `aria-pressed="false"` in the
   markup — so pressing it changed the page while the control itself looked and announced itself
   unchanged. From the user's side that is indistinguishable from "nothing happened". #106 fixed
   exactly that: the glyph now comes from CSS keyed on `data-theme` (correct at first paint), and
   `title`/`aria-pressed` are set from the applied theme.
   **Measured on `https://izz.ro/` 2026-08-02 09:18, real browser, not local:** fresh visit → ☾ /
   "Mod întunecat" / `aria-pressed=false` / bg `rgb(246,247,249)`; after click → ☀︎ / "Mod luminos"
   / `true` / `rgb(13,17,22)`, `localStorage.izz_theme=dark`; **after a full reload the dark theme
   and all three attributes persist**; no CSP or other console errors were observed during that
   check — which is evidence the policy does not block this path, not proof it blocks nothing
   (§16's own history: `script-src 'self'` silently killed the inline handler before #96).
   Deliverability (§16.2)
   holds — live serves `styles.css?v=44d15474` and `theme.js?v=318109e6`, both new hashes.
   **What is NOT established:** that this was the owner's complaint, or that his device behaves the
   same. Only he can close this — ask him to press it once and say what he sees. If he still says
   "nu merge", the next step is his exact browser + a console screenshot, NOT another blind fix.
1. ~~**PR #101 (locality lead photos) awaiting owner sign-off**~~ — **MERGED 2026-08-02 03:19.**
   This entry was stale. What is still open is only §16's third state: nobody has confirmed the
   129 photos ON LIVE. `smoke_live.py` or a look at izz.ro closes it.
1. **SIRUTA Slice 2 — BUILT, PR #125 OPEN (`feat/siruta-sate-pe-judet`).** Villages match only
   against the county of the source that published. `geo.clasifica(text, judet=None)` is unchanged
   bit for bit without the second argument; `judet_sursa()` reads a new `judet` field in
   `config.SOURCES` for the 9 county papers (`zcj` does not tell anyone it is Cluj) and falls back
   to parsing the key for the 129 institutional sources. `build_gazetteer.py` emits
   `data/sate_judet.csv` (12540 villages, 42 counties).
   → **Measured on 1733 articles, 665 from sources with a county: 10 reclassifications, all
   correct** — Nicula, Dezmir (Cluj), Igriș, Urseni ×3, Bulgăruș (Timiș), Merișor, Copalnic (MM).
   Five had no geographic rubric at all before.
   → **Two defects the measurement caught in the fix itself, both fixed:** (a) SIRUTA has villages
   named after their own county, so "județul Galați" matched the village GALATI and turned a county
   story local (3 of the first 15 changes — Galați, Brașov, Vaslui); names already in the UAT index
   are now skipped, they were judged above at their correct level. (b) **Village names that are
   really first names**: counted in one week of corpus, ADRIAN appears 19×, ROMANA 12× ("Poliția
   Română"), NEAGRA 10× ("Marea Neagră"), MARIUS 9, IULIA 8, VENUS 6, IRINA 6, SATURN 4 — all real
   villages, none of them meant as places. The county gate cannot catch this (ADRIAN *is* a village
   in Mureș), so 24 names were dropped from the index.
   → **No live effect until the next pipeline runs:** classification happens at processing time and
   existing articles keep the category stored in state.
   → Still open after it: regional papers cover several counties and therefore get no `judet` (they
   would need a county list), and the curated FEATURES list (Bucegi, Ceahlău, Dunărea).
2. **Interactive guides — NEEDS OWNER DESIGN + DATA.** Owner (2026-08-02): the static guides are
   useless, must be interactive. Natural form = calculators (brut→net salariu, copii→alocație).
   BLOCKED on two things, both the owner's: (a) which interactivity exactly; (b) the CORRECT
   formulas/rates — these are legal/financial (§10), a wrong net-salary published is worse than a
   static figure. Do NOT build calculators on guessed formulas. `data/entities/*.yaml` still
   `verificat: false` (honest). Owner must supply figures + deep-link `sursa_url` (RO domains).
3. ~~**Official sources re-fetched and expired in the same run**~~ — **FIXED, #108.** Do not re-open.
4. **Local press expansion — 79 researched candidates, NONE verified** (web session, 2026-08-02).
   A sub-agent mapped county press incl. weeklies. Only **CJ/IS/TM/BV/MM/AR/PH** have a dedicated
   county source today; the candidates would give **34 counties + București** their first one.
   Every RSS URL is a GUESS (the `<domain>/feed/` WordPress pattern) — the sandbox cannot fetch
   them, so verify BEFORE config and expect ~⅓ fallout.
   **DO NOT verify them with `feedcheck.yml`.** That runs on GitHub runners, i.e. the exact
   observation point that returns 200-with-nothing for 73 live sources (READ FIRST above). A
   candidate marked dead there tells you nothing. Verify from the owner's machine, or from the
   web sandbox — a third IP — and say which one produced the verdict.
   **The 14 candidates named here WERE verified from the owner's home IP, 2026-08-02 (read-only,
   nothing added to config): 10 of 14 serve a real feed at `<domain>/feed/`.**
   ✅ `cvlpress.ro` (50 intrări, "Cuvântul Libertăţii") · `alba24.ro` (20) · `zi-de-zi.ro` (12) ·
   `monitorulbt.ro` (12) · `turnulsfatului.ro` (10) · `bihon.ro` (10) · `gazetadecluj.ro` (9) ·
   `b365.ro` (4) — plus **both domains this file flagged as INFERRED are real**: `mytex.ro` (10)
   and `monitorulexpres.ro` (10). Drop the warning on those two.
   ❌ `monitorulsv.ro` — `/feed/` 301s to the homepage (458 KB of HTML, 0 entries); the WordPress
   guess is wrong for it, needs a real feed path. `dobrogeanoua.ro` and `saptamanagiurgiuveana.ro`
   — HTTP 404. `gazetademaramures.ro` — `SSL: CERTIFICATE_VERIFY_FAILED`.
   4/14 fallout ≈ 29%, so the ~⅓ estimate was right. The other 65 candidates exist only in the web
   session's transcript, not on disk — account B has to re-emit the list before they can be checked.
   Land in waves of ~15: 79 at once would starve the 10-call AI budget. Strongest first —
   `cvlpress.ro` (DJ), `zi-de-zi.ro` (MS), `monitorulbt.ro` (BT), `monitorulsv.ro` (SV),
   `turnulsfatului.ro` (SB), `alba24.ro` (AB), `bihon.ro` (BH), `b365.ro` (București).
   Weeklies the owner asked for: `gazetadecluj.ro`, `dobrogeanoua.ro`, `saptamanagiurgiuveana.ro`,
   `gazetademaramures.ro`. Two domains are INFERRED, not sourced — `mytex.ro`,
   `monitorulexpres.ro` (BV) — do not type them into config unverified. CV/HR real local press is
   mostly Hungarian-language, which breaks the `lang: ro` assumption.
5. **`/surse/` grouping — DONE by #105**, `templates/surse.html` renders `group.regions`. What is
   still open is only the **MAP** to select news by region/zone, plus the unanswered granularity
   question (9 vs 7 regions) — both owner decisions, not implementation work.
   Data is already there: `judet` is in `gold_integrare.csv` and encoded in every `pl_<judet>_*`
   key. Depends on the geo axis, i.e. on SIRUTA Slice 2 above.
6. **A 7-slice plan arrived from another session (2026-08-03). Four of its findings were checked
   against this tree and hold; three of its framings do not.** Keep the findings, not the ordering.
   ✅ **`sorted(key=lambda a: a.get("published") or "")` is a LEXICOGRAPHIC sort on a string**, in
   three places — `state.py:100`, `render.py:346`, `render.py:436` (the plan said four, with line
   numbers that no longer exist). Mixed `+03:00` and `Z` offsets order wrong. Smallest real bug on
   the list, no gate, and everything about ranking sits downstream of it. Do this first.
   ✅ **`significance` was a DEAD BRANCH IN PRODUCTION — the branch is DELETED by #124.** What is
   still open is only the decision to populate it from the AI schema; if that happens, it comes
   back as a field the pipeline writes, not as a template `{% if %}` waiting for one.
   (Was: `_card.html` and `index.html` rendered `Relevanță X/10` behind
   `{% if a.significance is defined %}` while no `.py` ever wrote the key — a promise the page
   never once kept.) If it is populated, it goes **on top of #118, not instead of it.**
   #118 already ranks pre-AI on
   corroboration + freshness with an md5 tie-break that review caught; `significance` is a post-AI
   ordering. Anyone who rewrites the ordering from scratch will silently drop that tie-break.
   ✅ **Model C is not batched** — `process_cluster(group, provider)` is one call per cluster while
   B batches 10. But the plan's gate ("implement if `ai_calls` often hits 12") is calibrated on the
   wrong number and is already answered: the default is 12 (`main.py:173`) yet **`build.yml:55`
   overrides it to 18**, so production never runs on 12 — and #118's session already measured, from
   `build.yml` logs, that the budget is consumed in full on every run. Read `stats["deferred"]`
   (added by #118 for exactly this) over 2-3 runs and build it; do not re-litigate the gate.
   ✅ **Untrusted RSS text is interpolated straight into the prompt** — `process.py:260`,
   `USER_B.format(title=item.get("original_title"), description=...)`. Impact is bounded (text out,
   human moderation, official `pl_/cj_/pr_` sources are processed deterministically with no AI at
   all), so this is insurance, not growth. Whether it rides along with the `significance` prompt
   edit is a real toss-up: same strings and one `PROMPT_VERSION` bump argue for merging, a mixed
   review that hides an AI-quality regression behind a security change argues against.
   ❌ **`content-visibility: auto` as a warm-up slice — do not run it.** §13 measured the CLS cause
   (`#izz-install-btn`, 49 px, 100% Lighthouse attribution) and explicitly forbids chasing the
   number with tricks; the fix is a placement decision the owner makes. The plan's own DoD admits
   it can introduce shift on fast scroll. It is the one slice that walks into a written rule.
   ❌ **The source-coverage loop, as written, would produce false metrics.** "Live sources over
   time" is measured with a checker that reimplements its own fetch — the exact defect logged at
   the top of this file, where 74 sources return an anti-bot interstitial with HTTP 200 and
   `feedparser` reads it as a valid empty feed. Fix the measurement before building a metric on it.
   ✅ **News sitemap — DONE, #122, CONFIRMED ON LIVE.** `https://izz.ro/sitemap-news.xml` served
   404 before, serves **404 entries** now (the count, not the code), all inside the window, and
   `robots.txt` announces it. Separate file, not a namespace on `sitemap.xml`: the protocol wants
   only 48h of news, `sitemap.xml` carries 1413 URLs including guides and legal pages. The
   eligibility gate the plan proposed was dropped as misplaced — it is the owner's question, in
   parallel, and a refused application costs the sitemap nothing.
   (Dropped by the plan itself, correctly: prompt caching — under the ~1024-token cache minimum and
   irrelevant on the free Gemini path, where the cost is calls, not tokens.)
7. ~~**THE AI BUDGET IS 18 AND THE PIPELINE USES 10.**~~ — **FIXED, #123 MERGED (`7d3fca94`).**
   `ai_reserve()` caps the reserve at the real number of upgradable articles, so on today's state
   all 18 calls go to new items instead of 10. The reserve is not abolished: a `PROMPT_VERSION`
   bump makes ~1100 articles eligible at once and it protects them then — a test guards that.
   The eligibility predicate moved into `upgradable()`, used by both callers, and `ai_budget` /
   `upgrade_reserve` / `upgradable` are now in stats plus one line in the report, because the
   symptom (`ai_calls 10`) was unreadable without crossing two env vars with state.
   **Watch on the next runs, not blocking:** daily Gemini usage rises from ~120 to at most 216
   calls (the number `MAX_AI_CALLS_PER_RUN=18` already intended; the 4 s throttle keeps 18 calls
   ≈ 72 s, under the measured 15/min ceiling), and model-B throughput can double, so
   `data/articles.json` (1.9 MB / 1736 articles today) may grow toward ~3.5 MB.
   Kept below for the measurement that produced it — do not re-derive it:
   `build.yml` sets `MAX_AI_CALLS_PER_RUN: 18` and `UPGRADE_RESERVE: 8`, and `main.py:178` hands
   `process_new` only `budget - reserve` = **10**. The reserve then goes to `upgrade_fallbacks`,
   which upgrades articles that are `model == "B"` **and** have `original_title` **and** are either
   `processed_by == "fallback"` or on a stale `PROMPT_VERSION`. Counted on today's state:

   ```text
   1117 (B, gemini, v2-esenta)   386 (C, gemini, v2-esenta)   233 (B, official, None)
   fallback left in state: 0        eligible for upgrade: 0
   ```

   The 233 official items never qualify — they are processed deterministically and carry no
   `original_title`. So **8 of 18 calls (44%) are reserved for an empty queue**, while three
   consecutive runs deferred new items for lack of budget:

   ```text
   03:49  new 94   B 70  C 3   deferred  20   ai_calls 10
   23:06  new 119  B 90  C 1   deferred  27   ai_calls 10
   21:07  new 185  B 50  C 4   deferred 127   ai_calls 10
   ```

   `ai_calls 10` on every run is the proof the reserve is never spent, not a coincidence.
   **The reserve is not wrong by design** — a `PROMPT_VERSION` bump makes ~1100 articles eligible
   at once, which is what it exists for. It is wrong *unconditionally*: reserve
   `min(UPGRADE_RESERVE, eligible_now)` and the calls go to new items on runs with no backlog.
   Expected effect: 10 → 18 calls per run, ~+80% new-item throughput, +32 s of runtime at the 4 s
   Gemini throttle. **This outranks batching model C** — batching makes each call carry more, this
   makes 8 free calls exist at all, and it is one constant plus a count.

## Settled today — do NOT re-derive
- **OpenCode no longer dies when the Zen quota runs out.** `tools/oc_run.sh` walks a free-route
  ladder automatically (`--list` shows what is live); `/delegate-opencode` step 4 goes through it.
  It falls through only on INFRASTRUCTURE failure (exit≠0 or an `Error:` line) — a route that runs
  and reports a bad task result is deliberately not retried. Commits `4157e401`, `6243d96c`,
  `48bc5c2a`, `1acae53b`. **5 live routes**, each smoke-tested by running: 3× Zen free
  (`deepseek-v4-flash-free`, `laguna-s-2.1-free`, `north-mini-code-free`) + `google/gemini-3.1-flash-lite`
  (separate quota) + `mistral/codestral-latest` (separate quota). `small_model` moved to Gemini
  flash-lite so session titles stop burning the 100/day Zen budget.
  **Four dead ends, measured — do NOT re-diagnose as "bad key":** (a) opencode's `google` provider
  reads `GOOGLE_GENERATIVE_AI_API_KEY`, not `GEMINI_API_KEY` — it lists models fine and fails only
  at call time; fixed in config, not with a new env var. (b) `vercel/*-free` needs a credit card on
  file despite a valid `AI_GATEWAY_API_KEY`. (c) **groq**: key valid, free tier caps TPM at 8k–12k
  while opencode's system prompt alone is 32–46k → "Request too large" on every agentic call; only
  a paid Dev Tier fixes it. (d) **cerebras**: key valid (lists models) but every chat call returns
  `payment_required`, and its free context cap is 8k anyway. Both stay wired for a future paid plan.
  Local `ollama` is out too: measured hardware is a GTX 1060 3GB / 16GB RAM — too slow for an
  agentic loop. `OPENROUTER_API_KEY` is the only unclaimed free-ish route (needs a one-off $10).
- **Gemini free tier = 15 requests per MINUTE. MEASURED, not read** (`54581538`): probed the
  production key directly — 15 calls returned 200, the 16th returned 429 with `limit: 15` for
  `generate_content_free_tier_requests`. `gemini.py` sits exactly on that ceiling by design
  (`GEMINI_THROTTLE=4.0` → 4s × 15 = 60s), which is why its comment says 2s tripped 429.
  The daily cap is irrelevant: `MAX_AI_CALLS_PER_RUN=18` × 12 runs = 216/day, hardcoded.
  → Consequence: opencode must NEVER share that key. Its google route now reads
  `GEMINI_API_KEY_OC` (dormant until a key from a **different Google account** exists — same
  account shares the quota), and `small_model` moved to `mistral/codestral-latest` because it
  runs on every session and must not depend on a contended key.
  → Also measured: **zero Gemini errors across the last 6 pipeline runs.** The 429s in those
  logs are feed sources (elle, bzi, libertatea), not the AI provider. Do not re-diagnose.
- **The "too few articles" cause was an outage, not the budget.** 30 consecutive `pipeline` runs
  failed 21 Jul 17:40 → 24 Jul 03:37 UTC with `AI DOWN — HTTP 400`: Gemini's `-latest` alias
  repointed to a 3.x model that rejects `thinkingConfig`. Fixed by `d56a8db` (#76); green since.
  The 40- and 92-article days were outage days; 198 was the recovery day, with a TTL expiry spike.
- **Real production budget:** `MAX_AI_CALLS_PER_RUN=18` and `UPGRADE_RESERVE=8` (both set in
  `build.yml`, so the 12/3 defaults in `main.py` are dead in production) → **10 calls/run for new
  articles**. Model B batches `BATCH_SIZE=10` per call, model C yields 1 (its value is
  de-duplication).
  → **RE-MEASURED 2026-08-02 from three consecutive `build.yml` logs: the budget is exhausted on
  EVERY run, 10/10.** 13:49 → 261 new, B 0, C 10; 15:14 → 252 new, B 20, C 8; 17:11 → 244 new,
  B 40, C 6. At 13:49 clusters ate the whole budget and not one single article was processed.
  The "741 new items per run" figure above predates #108's stale-skipping; the real inflow is
  ~250/run. Unprocessed items are never written to state, so they return as "new" next run.
  → Consequence, and it is why #118 exists: under permanent saturation the CONSUMPTION ORDER is
  the editorial policy, and that order was `config.SOURCES` order (`fetch.py:560` keeps it
  deliberately: "ce ajunge la coada e infometat"). The head of that list is lifestyle
  (`unica`, `csid`, `sfatulparintilor`, `elle`); hard news sits at the tail.
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

## Merged 2026-08-03 (account A — announce, per §14)

- **#123 MERGED (`7d3fca94`) — the AI budget stopped reserving upgrades that cannot happen.**
  Details and the follow-up to watch are in Open 7 above.
- **#124 MERGED (`4f335153`) — every listing page is reachable, no dead links.**
  Measured on the pre-fix render: `general/3`, `politic/3`, `tech/3` were dead links (2-page
  categories), and **44 of 79 rendered listing pages were linked from nowhere** — `zonal` rendered
  20 and stopped the nav at 3. The sitemap is not a second path: `_write_sitemap` emits no
  pagination at all, so an orphan had no way in. `_pagination()` now derives the nav from the real
  page count (first, last, ±`PAGE_WINDOW`, prev/next), which keeps the link count small while
  putting every page one hop from its neighbours; the tests assert reachability by walking the
  rendered links, not the markup. The `20` hardcoded four times became `PAGE_SIZE`.
  → **`significance` is deleted** here (two templates, two CSS rules, 0 of 1736 articles). If it
  ever comes back it comes back as a written field, not as a template branch waiting for one.
  → **A defect the window introduced, caught by measuring:** at 375 px the 11 items overflowed and
  the whole page scrolled sideways (`scrollWidth` 392 vs `clientWidth` 375). `flex-wrap: wrap`
  on `.pagination`; re-measured 375/375. Verified in a real browser on the built site, pa11y
  WCAG2AA 0 errors on `/tech/`, `/tech/2/`, `/zonal/10/`. 440 tests pass locally.
  → **Three review points, all real, all taken:** (a) an article whose title slugifies to `2`
  would land on `/cat/2/` and, since articles are written AFTER the listing pages, would
  overwrite page 2 silently — 0 of 1733 titles do that today, but it is a property of the paths,
  not of the corpus, so `_assign_slugs` prefixes numeric slugs; (b) the new fixture renders
  **unconditionally** — the "render only if `output/` is missing" pattern in the two older
  fixtures is what made this session debug two stale-output failures, and 30 s per run is cheaper
  than a verdict about another branch's render; (c) `_numar_din_cale` strips `SITE_BASE`,
  verified by running the file with `SITE_BASE=/preview`.
  → **CONFIRMED ON LIVE** (§16.3, cache-busted, 12:45): `https://izz.ro/tech/` serves `‹ 1 2 ›`
  (the dead `/tech/3/` link is gone and that URL 404s, unlinked), `/tech/2/` now carries a nav of
  its own instead of being a dead end, and `/zonal/10/` — one of the 44 orphans — is reachable
  and shows `‹ 1 … 8 9 10 11 12 … 19 ›`. No "Relevanță" anywhere.
  → **Still open, deliberately:** pagination pages are linked but NOT in `sitemap.xml`. Whether
  pages 2+ should be indexed at all (or carry `noindex`) is an SEO decision, not implementation.
- **#112 MERGED (`5c631f7d`) — every action reference in `.github/workflows/` is pinned to a
  commit SHA.** zizmor's `unpinned-uses`, raised by CodeRabbit on #111 and skipped there because
  pinning one new workflow while 13 stayed on floating tags is an inconsistency, not a fix. 32
  references, 13 workflows. Each SHA resolved with `gh api repos/<o>/<r>/git/ref/tags/<tag>` and
  confirmed to exist with `.../commits/<sha>` — none guessed. **Four of the seven tags are
  annotated** (`peaceiris`, `browser-actions`, `anthropics`, `github/codeql-action`), so the ref
  had to be dereferenced through `/git/tags/<sha>`; taking `object.sha` directly there pins the
  tag object, not a commit, and the run fails. Remember that when bumping by hand.
  → The trailing `# vN` is load-bearing, not decoration: `.github/dependabot.yml` already has a
  weekly `github-actions` entry and parses exactly that format, so **pinning does not freeze
  versions** — bumps keep arriving as PRs. Do not "simplify" the comment away.
  → `persist-credentials: false` added to the checkouts that never push (codeql, feedcheck, probe,
  smoke, tests, ua-probe, visual, claude-code-review). **Deliberately NOT added, each with a
  comment in the file so the asymmetry does not read as an oversight:** `build.yml/pipeline`
  (pushes the state commit), `build.yml/mirror` (publishes via `peaceiris`, i.e. the §10 deploy
  path — it pushes with `MIRROR_DEPLOY_KEY` not the checkout token, so it is *probably* safe to
  add, but that is a separate slice), `fonts.yml` (commits fonts), `claude.yml` (`contents: write`,
  "@claude apply your fixes" commits on the branch). `monitor.yml` uses no actions at all.
  → **Proven by running, on the runners:** `pytest` and CodeQL `analyze` both green on the PR with
  the pins in place, which exercises checkout, setup-python, codeql-action/init + /analyze and
  claude-code-action. **NOT exercised by any PR-triggered workflow:** `upload-artifact` (visual),
  `setup-chrome` and `actions-gh-pages` (build). First proof for those comes from the next
  `pipeline` / `visual-live` cron run — if either goes red, look at the pin first.
  → Merge conflict on the way in: main had **deleted** `claude-docs-review.yml` (`c5a3c3ef`,
  "drop the duplicate reviewer") while the branch was modifying it. Resolved by accepting the
  deletion. Local suite after merging main: **402 passed** — the "262 tests" figure in CLAUDE.md §4
  is stale as of today.

## Merged / open 2026-08-02 EVENING (account A — announce, per §14)

- **#115 MERGED (`e3803973`) — the salary calculator works on live, for the first time ever.**
  External `static/calc-salariu.js` under CSP + `select.py` extraction + a guard test against
  inline JS in any template. **CONFIRMED ON LIVE, driven as a user** (§16.3): on
  `https://izz.ro/ghiduri/salariul-minim/`, typing 7000 brut recomputes to 4.176 lei net
  (CAS 1.750 / CASS 700 / deducere 810 / impozit 374). `window.calcSalariu` is undefined by
  design now — the fix uses listeners, not globals — so do NOT read that as the old symptom;
  the old symptom was `#calc-results` EMPTY, and it is now populated. Asset served as
  `/static/calc-salariu.js?v=516f4eba`, i.e. §16.2 deliverability holds.
- **#116 MERGED (`32e01c72`) — three guides that had never reached a reader.** buletin-pasaport,
  permis-auto, noua-casa ported from the dead `/utile/` path into `/ghiduri/`, plus an optional
  `sectiuni` field in the entity schema. All three live and 200 on izz.ro.
  → Merge conflict with #115 resolved locally: main's `_render_calc_salariu(env, ent)` signature
  kept, this branch's `sectiuni` block kept. They sit on adjacent lines; nothing else overlapped.
- **#117 MERGED (`d119b098`) — the sitemap listed only news.** Live sitemap now carries 1307 URLs
  including all 6 guides, the calculator, `/calendar/`, `/surse/` and the legal pages — verified
  by fetching `https://izz.ro/sitemap.xml` after deploy. Zero `/utile/` leakage.
- **#118 OPEN, green, CodeRabbit APPROVED — budget ordering.** See the budget bullet above.
  Corroboration (distinct domains) then freshness decide who consumes the AI budget, plus
  `stats["deferred"]`. Reconstructed on the real corpus: `csid` took 9 of 19 slots before,
  6 sources share them after; median age of selected items 619 → 140 min. 387 tests.
  → CodeRabbit caught a real defect: Python's sort is stable, so equal keys fell back on input
  order, i.e. the config order the slice removes — and ties are systematic for feeds that give a
  date without a time (`_parse_w3c_date`, `_parse_ro_date` → midnight UTC). Fixed with an md5(url)
  tie-break, uncorrelated with the source.
- **STILL OPEN, in order: delete the dead `/utile/` path.** Unblocked now that #115 is in —
  the modify/delete conflict on `templates/utility.html` is gone and #116 saved the content.
  Targets: `render._render_utilities`, `templates/utility.html`, `templates/utilities.html`,
  `data/utilities.json`.
- **A test-design trap that cost time twice today, worth fixing:** the fixtures in
  `test_entities_verified.py` and `test_sitemap_editorial.py` re-render ONLY when `output/` is
  missing, so a stale `output/` from another branch makes them fail (or, worse, pass) against
  code that is not the code under test. CI never sees it; a local run does.

## Merged / open 2026-08-02 (account A — announce, per §14)

- **#106 MERGED (`e558f3da`) — theme toggle shows the ACTION, not a fixed moon.** Glyph moved to
  CSS (`.theme-toggle::before`, keyed on `data-theme`, `\FE0E` so Chrome/Windows draws ☀ as text
  and not colour emoji); markup no longer asserts a state; `theme.js` sets `title` + `aria-pressed`
  from the applied theme. Audit run before/after, article pinned, 3 reps each: no regression
  (medians home 84→83, article 92→92, pa11y 0 both). Confirmed on live — see Open 0.
  → CodeRabbit's residual point was **declined with a reason, not silently dropped**: between HTML
  parse and `DOMContentLoaded` the two attributes are absent. `aria-label` is always present, so a
  missing `aria-pressed` reads as "button" rather than a *false* "not pressed"; closing it needs
  either a second render-blocking script after the button or an inline one the CSP refuses.
- **#108 MERGED (`41658bf0`) — items already past TTL no longer enter the pipeline.** Closes the
  old Open 3. Measured on a real cold fetch: **795 of 1096 "new" items (73%) from 126 sources**
  were already older than the 7-day TTL when read, so they burned AI budget, were deleted by the
  trailing `expire()` in the SAME run, and returned as "new" on the next one. Nothing about what
  gets published changed. The reviewer confirmed a data-loss path I had only inferred:
  `process_cluster` sorts a group ascending by `published` and takes `group[0]`, so **the oldest
  member becomes the representative** — a stale item could absorb a FRESH article via `folded` and
  take it down with it on expiry. `stats["stale_skipped"]` now reports the count.
- **#109 MERGED (`6a4a6ad0`) — §13's CLS explanation was wrong twice over.** The shift is 100%
  `body > main`, and it is **`#izz-install-btn`**: hidden in markup, revealed by `personalize.js`
  on `beforeinstallprompt`, inside `.nav` in the sticky header. Measured at 412 px: hidden → `main`
  at 236.3, shown → **285.3**, matching Lighthouse's `boundingRect.top: 285` exactly. 49 px of
  content jump mid-read, and the event's nondeterministic timing is why the score is bimodal.
  **Dead ends, do not re-investigate:** `#izz-consent` is `position:fixed` (out of flow, cannot
  move `main`); the font swap measures **0 px** delta at 412 px and 1280 px.
  → **Open, and it is the owner's call:** where the install button goes so it stops growing the
  header. Reserving the row always costs 49 px of mobile header for a button most visitors never
  see. Delaying the reveal past the CLS window is forbidden — that is chasing the number.
- **#107 MERGED — `tools/audit.sh` never worked on Windows**, found while doing the above. Three
  independent Linux-only assumptions: Chromium detection missed every Windows path; the version
  line ran `chrome.exe --version`, which forwards to a running instance and logged
  `Opening in existing browser session.` instead of a version (so #103's whole comparability
  mechanism held nothing on Windows); and pa11y got the MSYS path `/c/Program Files/...`, which
  node/puppeteer cannot resolve — it died with stderr to `/dev/null`, and `wc -l - 1` on the empty
  CSV printed **"WCAG2AA errors on home: -1"**, a fabricated number where a failure belonged.
  A lighthouse `EPERM` on temp-profile cleanup (raised *after* a successful audit) also aborted the
  script under `set -e` before pa11y ever ran. All fixed; a missing report is now a hard failure.

## Merged 2026-08-02 (web session — announce, per §14)
- **#98** — `_fetch_sitemap_news` returned `(items=[], None)`: a sitemap that answers 200 with
  valid `<url>` entries but yields nothing looked HEALTHY and never reached the dead-source list.
  `piataauto` (the only `sitemap_news` source) produced 0 articles from 19 Jul on, unnoticed.
  Now it reports entry count + likely cause, and `MAX_PER_SOURCE` is applied AFTER filtering
  (bad leading entries no longer starve a source). Parser extracted as `_parse_sitemap_news`
  so it is testable without network; 6 new tests. **Why piataauto's entries are unusable is
  still UNKNOWN** — the sandbox cannot reach piataauto.md (403 tunnel); the next run's log names it.

## Merged 2026-08-01/02 (account A, from B's draft PRs)
- **#96** — dark-mode toggle was dead on live: CSP `script-src 'self'` (no `unsafe-inline`)
  refused the inline `onclick` + `<script>`; worked locally only because `http.server` skips
  `_headers`. Moved to external `static/theme.js` (event delegation, cache-busted). **Verified on
  the branch preview with real CSP**: toggle flips `data-theme`, persists, zero console/CSP errors.
- **#99** — geographic section decided from article TEXT, not an AI guess (`generator/geo.py`):
  region→regional, county→zonal, locality→local, most-specific wins, no place name → stays on
  topic. Fixes the "Swiss village under regional" leak. 28 geo tests incl. the real triggers.
- **#97** — CLAUDE.md §19 session hygiene + §14b bounded background work. §18 numbering collided
  with main's institution-images section; resolved (kept both, hygiene→§19), merged via main.

## Merged 2026-07-25 (prior session)
#86 reviewers could not read code (failed on every PR) · #87 131 articles stranded on the old
geographic category · #88 cadence docs + reviewers no longer gate on quota · #89 `/surse/` shows
all 189 sources instead of 2 links · #90 freed the slot held by an unreachable source ·
#91 dark-mode contrast (305 hidden pa11y errors), sticky subnav, PWA name + its cache-bust ·
#92 agent runs quantified, report timestamped.

## Blockers
- MAI WAF blocks `*.prefectura.mai.gov.ro` from this IP (502). Retest from Actions.
- Cloudflare free plan ~500 builds/month is why `build.yml` runs every 2h (`13 */2`). Do not
  raise the frequency — see CLAUDE.md §17.
