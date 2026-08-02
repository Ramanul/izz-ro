# STATE — project execution state

> Single source of truth for "where we are". Manager-owned; updated at the end of every slice.
> Executors get it read-only. Keep it tight — when it outgrows ~40 lines of content, cut the
> settled history, not the open work. `git fetch` immediately before rewriting it.

**Updated:** 2026-08-02 (locality lead photos — PR #101 ready for review; merged main in)

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

## Lead photos now come from the LOCALITY — PR #101, ready for review (2026-08-02)
Branch `claude/scraping-romanian-public-data-u63sqz`, spec `specs/locality-lead-photos.md`.
**0 → 113 real photos.** Before this, every article on the site carried a generated icon cover:
`data/leadphotos.json` was 1684 entries, all `miss`. The old route looked up P18 on the article's
PERSON entities and required landscape AND PD/CC0 at once — a mayor's portrait is vertical and
almost always CC-BY, so the intersection was empty.
- Resolution keys off the deterministic source slug `pl_<judet>_<localitate>`, not entity text.
  Measured on the 120 GOLD primării: 120/120 resolve, 108 have P18, **81 usable (67%)**.
- Wikidata classes that work: `Q659103` comună / `Q16858213` oraș / `Q640364` municipiu, with a
  DIRECT `wdt:P31`. `P31/P279* Q15284` misses every *oraș*; `P31/P279* Q486972` returns 504.
  Ask for XML — the ~2 MB JSON response arrives truncated intermittently.
- **County match is mandatory, no fallback**: 12 of 120 names have homonyms elsewhere
  (Zărnești/Buzău vs Zărnești/Brașov) — a wrong town's photo on a local story.
- CC-BY and CC-BY-SA are accepted here. Attribution rides on the article page
  (`figcaption.art-credit`); CC 4.0 §3(a)(2) / CC 3.0 §4(c) allow satisfying it via a link, and
  the card links to the article. **Cards get no new element — §7 untouched.**
- `data/localities.json` (3179 UAT) is committed so the build never needs Wikidata. Rebuild
  rarely: `python tools/fetch_localities.py`.
- A `miss` now carries `v` = MISS_VERSION. **Bump it when adding a search route**, or the cached
  misses make the new route invisible on all existing content.
- Front-end audit measured BEFORE and AFTER on the same machine: home Perf 80 → 80 (identical,
  CLS 0.234 both), article 88 → 87 (LCP +0.3 s, +65 KiB). A11y 100, pa11y 0, BP 100, SEO 100
  throughout. **CLAUDE.md §13's baseline (home Perf 89, 2026-07-02) is STALE** and will keep
  producing false regression alarms until the owner re-records it.
- **Overlap with SIRUTA, worth reconciling:** `data/localities.json` is a Wikidata gazetteer of
  the same 3179 UATs, already carrying county labels and the county-matching helper
  (`generator.localities.match`). SIRUTA Slice 2 needs exactly that disambiguation — reuse or
  consolidate rather than building a second county matcher.

## Open
0. **PR #101 (locality lead photos) is out of draft, CI green, awaiting owner sign-off + live
   confirmation.** Per §16 the most that can be claimed is "verificat local"; only the owner or
   `smoke_live.py` can confirm on izz.ro.
1. **SIRUTA Slice 2 — county-aware village matching.** Groundwork merged (siruta_raw.csv +
   build_gazetteer.py). Design is now clear: villages match ONLY when the source's county matches
   the village's county. This kills the measured false positives — Saturn/horoscope/FCSB all come
   from NATIONAL sources (no county), so village matching simply won't fire for them; a Vrancea
   paper's "Poiana" → Poiana-Vrancea works. Needs: source→county map, `geo.clasifica(text, county)`,
   plumb through `_resolve_category`. Plus a small curated FEATURES list (Bucegi, Ceahlău, Dunărea).
2. **Interactive guides — NEEDS OWNER DESIGN + DATA.** Owner (2026-08-02): the static guides are
   useless, must be interactive. Natural form = calculators (brut→net salariu, copii→alocație).
   BLOCKED on two things, both the owner's: (a) which interactivity exactly; (b) the CORRECT
   formulas/rates — these are legal/financial (§10), a wrong net-salary published is worse than a
   static figure. Do NOT build calculators on guessed formulas. `data/entities/*.yaml` still
   `verificat: false` (honest). Owner must supply figures + deep-link `sursa_url` (RO domains).
3. **Bug, found and NOT fixed:** ~129 official sources are re-fetched every run and expired by
   `state.expire()` in the *same* run — 76% of their content is already past the 7-day TTL when
   read. Wasted fetch + **falsified stats**. Fixable without owner — good next code slice.

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
