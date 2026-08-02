# STATE — project execution state

> Single source of truth for "where we are". Manager-owned; updated at the end of every slice.
> Executors get it read-only. Keep it tight — when it outgrows ~40 lines of content, cut the
> settled history, not the open work. `git fetch` immediately before rewriting it.

**Updated:** 2026-08-02 09:20 (account A — #106 merged and CONFIRMED ON LIVE; #107 open; audit.sh was broken on Windows)

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
   and all three attributes persist**; console clean, so CSP blocks nothing. Deliverability (§16.2)
   holds — live serves `styles.css?v=44d15474` and `theme.js?v=318109e6`, both new hashes.
   **What is NOT established:** that this was the owner's complaint, or that his device behaves the
   same. Only he can close this — ask him to press it once and say what he sees. If he still says
   "nu merge", the next step is his exact browser + a console screenshot, NOT another blind fix.
1. **PR #101 (locality lead photos) is out of draft, CI green, awaiting owner sign-off + live
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
4. **Local press expansion — 79 researched candidates, NONE verified** (web session, 2026-08-02).
   A sub-agent mapped county press incl. weeklies. Only **CJ/IS/TM/BV/MM/AR/PH** have a dedicated
   county source today; the candidates would give **34 counties + București** their first one.
   Every RSS URL is a GUESS (the `<domain>/feed/` WordPress pattern) — the sandbox cannot fetch
   them, so route the batch through `feedcheck.yml` BEFORE config and expect ~⅓ fallout.
   Land in waves of ~15: 79 at once would starve the 10-call AI budget. Strongest first —
   `cvlpress.ro` (DJ), `zi-de-zi.ro` (MS), `monitorulbt.ro` (BT), `monitorulsv.ro` (SV),
   `turnulsfatului.ro` (SB), `alba24.ro` (AB), `bihon.ro` (BH), `b365.ro` (București).
   Weeklies the owner asked for: `gazetadecluj.ro`, `dobrogeanoua.ro`, `saptamanagiurgiuveana.ro`,
   `gazetademaramures.ro`. Two domains are INFERRED, not sourced — `mytex.ro`,
   `monitorulexpres.ro` (BV) — do not type them into config unverified. CV/HR real local press is
   mostly Hungarian-language, which breaks the `lang: ro` assumption.
5. **Owner wants `/surse/` grouped by historical region → county** (2026-08-02), and eventually a
   MAP to select news by region/zone. Region granularity (9 vs 7 regions) still unanswered.
   Data is already there: `judet` is in `gold_integrare.csv` and encoded in every `pl_<judet>_*`
   key. Depends on the geo axis, i.e. on SIRUTA Slice 2 above.

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
- **#107 OPEN — `tools/audit.sh` never worked on Windows**, found while doing the above. Three
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
