# STATE — project execution state

> Single source of truth for "where we are". Manager-owned; updated at the end of every slice.
> Executors get it read-only. Keep it tight — when it outgrows ~40 lines of content, cut the
> settled history, not the open work. `git fetch` immediately before rewriting it.

**Updated:** 2026-08-07 (account A — eight PRs landed: #151–#158)

## Merged 2026-08-07, third batch (account A — announce, per §14)

- **#158 `8c7fcd9e` — the same story from two feeds no longer becomes two pages.**
  **57 pairs of articles shared a `url`** in `data/articles.json` (2766 articles, 2.06%), all from
  one combination: `digi24` (general RSS) × `extern` (`digi24.ro/rss/stiri/externe`, a subset of
  the same site). **56 of 57 had different slugs** — two distinct pages, two AI-written titles for
  one source article. 21 pairs confirmed with both pages present in `output/`. Per source: 57 of
  104 `extern` articles (55%) and 57 of 109 `digi24` (52%) were the same story.

  `main.py:212` filtered new items **only against existing state, never against each other**. Two
  items sharing a url in one fetch both passed, each burned an AI call, and both entered `combined`
  — a list concatenation, not a dict. **`state.merge()` promises exactly this dedup and is
  dict-based, hence immune by construction — but is called nowhere in production**: its only caller
  is `tests/test_state.py`. That is why its test stayed green while the real path did not dedup.
  Read that as a warning about safety functions with green tests: check who calls them.

  Excluded by measurement: `normalize_url` is not the cause — `normalize_url(original_link) == url`
  for all 57. First-wins, so `config.SOURCES` order decides which copy survives (`extern` at 180,
  `digi24` at 188); `fetch_all` preserves that order deliberately. New `exemplare_duplicate` stat
  makes feed overlap visible in the run report. 4 new tests, all 4 red on the previous code.

  **Not done:** the 57 pairs already in state stay until they expire (7-day TTL). Deleting them
  would break 57 public permalinks, and **`_redirects` is not generated at all** — verified, the
  file does not exist.

### Owner raised two `/local/` articles on 2026-08-07. They are DIFFERENT bugs.

- **(a) GSP football story on `local` — nothing to fix in code.** The gazetteer matches the city
  inside club names ("CFR **Cluj**", "Universitatea **Craiova**"). Today's code stops it twice
  over (#155 sport, #156 `_locul_e_subiectul=False`). It is live because it was ingested at
  **10:48** and #155 landed at **11:37**. Categories are computed **once, at ingestion**
  (`process.py:303/340/412`) and never recomputed → every classification fix has a blind window of
  up to 7 days. **314 of 1301 geo-axis articles are in this state** (189 sport icon, 179 that #156
  would remove, 54 both). They heal by expiry. Retroactive migration rejected: category is part of
  the permalink, so moving 314 articles breaks 314 public links for a one-week benefit.

- **(b) Cernavodă barge story on `local` — NOT fixed by anything, and it is the real gap.**
  39 geo-axis articles name Cernavodă, 30 from national sources, 28 are `local`, and **all 39 pass
  `_locul_e_subiectul`** — #156 removes zero. The rule works as written: the barges really are at
  Cernavodă. But six national outlets cover the Danube's record-low flow and the nuclear plant at
  once. The owner's 2026-08-02 rule ("LOCAL means WHERE it happens, not WHO publishes") has **no
  notion of a local event with national stakes**. Owner authorised the AI route explicitly.
  Design + dry test + acceptance criteria are written and ready to run, handed to account B:
  `handoff/to-B/2026-08-07-raza-nationala-si-ce-a-ramas.md`. Cheap alternatives already killed by
  measurement — see `WS-0029` (multi-source coverage: 453/1301 = 35% false positives) and the
  entities route (national-institution list rots; `Administrația Națională de Meteorologie` appears
  14× on the geo axis, almost all correct local weather warnings).

  **A `PROMPT_VERSION` bump costs ZERO extra AI calls today** — verified, not assumed: `upgradable()`
  requires `original_title`, `_scrub_processed` strips it from every AI-processed article, and the
  field is absent from all 2766 stored articles. The comment in `ai_reserve` claiming "a bump makes
  ~1100 articles" is stale.

- **`ai_cat` is still not saved**, and that is what makes both of the above unmeasurable backwards.
  Few-line diff at the three ingestion points; `_scrub_processed` does not strip it.

- **`WS-0030` corrects `WS-0027`:** "no lexical collision to fix" was measured only on the frequent
  names. **"Casa Albă" matches the county ALBA** — 11 articles about Trump/Iran/FIFA sit on `zonal`
  right now. Ablation with `ALBA` in `_AMBIGUE`: `kills_wrong=14, kills_right=0`. **Do not ship it
  in that form:** synthetic probes show it loses "Consiliul **Județean** Alba", "Prefectura Alba",
  "Alba a fost lovită de furtună", because `_MARCA_GEO` lacks `JUDETEAN`. The 7-day corpus simply
  had no Alba-county news, so `kills_right=0` is a sampling accident. Widen `_MARCA_GEO` first.

## Merged 2026-08-07, second batch (account A — announce, per §14)

- **#156 — a place named in the text only claims the geographic axis if the story is ABOUT it.**
  "Fitch keeps Romania's rating", published by a Brașov paper, was landing on `zonal`. The
  gazetteer sees that the text *contains* a place; it cannot see whether the story is *about* it.
  Signal costs **no extra AI call and no prompt change**: the model already emits `entities`
  ("1-4 KEY proper nouns"), and unlike its category choice, **entities ARE stored** — so the rule
  was measurable retroactively.

  Two tiers, and the second exists because the first measurement killed the simple version:
  1. title names the place → keep, no further check (that compartment measures **10%** wrong);
  2. otherwise the matched place must be among the story's entities (**53%** wrong otherwise).

  Applying tier 2 over titles too was measured and rejected: it would cut **152** articles from
  tier 1, nearly all **correct**, because the place is swallowed by an institution name
  ("Muzeul de Artă Populară Constanța", "Salvamont Suceava"). `kills_wrong=13/18`,
  `kills_right=2/12`; on corpus **188 of 1075 leave the axis (17.5%)**, removal precision 87%.
  **Known miss, stated up front:** 5 of 18 survive — the model sometimes lists a place among key
  entities on a national story ("Sameday…Cargus" → `['Sameday','Cargus','Muller','Bucuresti']`).

  Required a contained refactor: `clasifica` and the new `locuri_numite` would otherwise have had
  two loops over the same index, the second an **untested** reimplementation of the same guards.
  Extracted `_potriviri()`, one scanner. Equivalence checked in a separate worktree on HEAD:
  **2766 articles classified before and after, ZERO differences.**

- **#157 — the 404 page stops lying.** It rendered from the category template with `articles=[]`,
  so it said *"Nicio știre în această categorie deocamdată"* — the wrong answer for someone who
  arrived from a dead article link. Now: an explanation plus the 12 most recent stories.

### `WS-0028` — the expiry constraints, measured. Read before proposing "keep articles longer".
| constraint | value | source |
|---|---|---|
| files per site, Cloudflare Pages Free | **20,000** | Cloudflare docs, read 2026-08-07 |
| `output/` today | **10,997** (3,092 HTML, 7,557 images) | measured |
| cost per article | **~3.5 files** | derived |
| `_redirects` | 2,000 static + 100 dynamic | Cloudflare docs |

So `ARTICLE_TTL_DAYS` **cannot realistically exceed ~14 days**. And the elegant idea — one splat
rule redirecting expired articles to their category — is **dead, with a quote**: "Redirects are
always followed, regardless of whether or not an asset matches the incoming request", so it would
redirect **live** articles too. Only per-article redirects remain, capped at 2,000 (~6 days).

## Merged 2026-08-07 (account A — announce, per §14)

Five PRs. The first three were written before the GitHub Actions outage of 2026-08-06 15:22 UTC
and had **no CI at all**; the outage is over and they ran green before merging.

- **#152 `4ebb03a8`** — JSON-LD consolidated into one `@graph` with stable `@id`s + `WebPage` node.
- **#153 `842d2c49`** — town-hall names with diacritics, from `localities.json`. 2025 names change.
- **#151 `00709ea5`** — `defusedxml` on the sitemap path. Carried a second change: **the semgrep
  ratchet was tightened 4 → 2**, in the same slice that earned the reduction. The number came from
  CI itself, which asked for it verbatim ("coboara BASELINE_ERROR la 2, altfel clichetul se
  slabeste tacit"). A baseline left above reality silently absorbs the next regression.
- **#154 `f58d9c26`** — **Moldova the country no longer lands on the Romanian `regional` rubric.**
  Closes the known miss left by #127 and recorded in this file: the `_regiune_ca_nume_propriu`
  guard reads the capitalised word glued before the name, so it catches "Republica Moldova" but
  not bare "Moldova" (sentence start, or after a lowercase preposition). New guard is a *different
  kind* of discriminator on purpose: a country marker **anywhere in the text**, because title and
  teaser are classified together and "...în Moldova" in the title is disambiguated by "guvernul de
  la Chișinău" in the teaser, ~80 chars away. `kills_wrong=3, kills_right=0` on 2704 articles,
  verified by three independent mechanisms (text ablation, code mutation, corpus diff).
  **Does NOT touch the `extern` route — that is owner-closed (IZZ-0137) and this does not reopen it.**
- **#155 `ffae7a31`** — **sport no longer lands on the geographic axis, even when the text names the
  city.** Owner instruction was literally "look at similar sites and do the same". Convention found
  (2026-08-07), and it is **finer** than "sport isn't local": the match is Sport; it becomes local
  when the SUBJECT is the local impact.

  | site | local section | sports stories |
  |---|---|---|
  | `adevarul.ro/stiri-locale/constanta` | **0 of 33** | Farul entirely absent |
  | `adevarul.ro/stiri-locale/cluj-napoca` | **1 of 33** | and that one is "the match reroutes the buses" |
  | `digi24.ro/regional` | 0 in snapshot | — |
  | `monitorulcj.ro` — a **local** Cluj paper | separate `Sport` section | "CFR pierde cu 0-5" is filed there |

  Signal is the STORY's theme (`ai_cat`), **not the source's category** — the owner rejected the
  source on 2026-08-02, and measured it would also be wrong: of 159 articles carrying a sport icon
  on the geographic axis, **63 (40%) come from LOCAL papers**, so a source rule would miss them all.

  **Not retro-measurable, stated up front:** `ai_cat` is not stored in `articles.json`, so no
  migration is possible and the 159 figure is a **proxy on the model-chosen icon** (`medal`/`trophy`
  excluded — they also catch music galas). No migration is needed either: the window is 8 days
  (31 Jul – 7 Aug, TTL 7 days), so the stale ones roll out on their own.

### Open debt from this batch
- **`WS-0025`, blocked.** The `# nosemgrep` on `generator/render.py:15` **does not suppress** — the
  finding is still counted by the gate, although the comment there claims it was verified by running.
  Two hypotheses, undistinguished and undistinguishable today: SARIF includes suppressed results and
  the gate ignores `suppressions`, or the suppression does not match at all. The repo has no
  code-scanning alerts to query (measured: `[]`) and local semgrep is broken.
- **Re-measure the geographic leak now that sport is gone.** The "23% of set B is wrong" figure
  measured on 2026-08-07 **includes sport**, so it is stale as of #155.

## CI verifiers — landed 2026-08-06, `0315f745` (#150)

Two "missing" capabilities in HANDOFF were resources that existed and were simply not routed
(pattern recorded as LECTII L10). CodeQL was **not** broken — already fixed by `2acda681`; the two
red runs were doomed dependabot branches, never `main`.

- **`semgrep.yml`** — second static scanner beside CodeQL. Public rulesets `p/python` +
  `p/security-audit` + `p/secrets`; SARIF to the Security tab. **Gate is a ratchet on a measured
  baseline, not a zero threshold:** 67 findings repo-wide, **4 ERROR**, all pre-existing. A fifth
  turns the job red. Three of the four are `use-defused-xml` and are **legitimate** — we parse XML
  with the stdlib over external RSS, i.e. genuinely untrusted input. **Open slice: add `defusedxml`
  to requirements, then drop `BASELINE_ERROR` to 1.**
- **`gemini-review.yml` + `tools/pr_review_gemini.py`** — second AI reviewer on a *different*
  provider so it does not compete for the Claude quota (the documented cause of the Claude reviewer
  dying silently, PR #88). `GEMINI_API_KEY` had been a repo secret since 24 July, used only by the
  pipeline; the free tier is 1500 req/day, one PR = one call. A finding without `file:line` + a
  repro is **dropped mechanically** before it reaches a human, and the dropped count is published.
- **Gotcha, measured live on #150:** the first run reported `review pass 10s` having reviewed
  nothing — 503 on both models, swallowed by `continue-on-error`. That flag was copied from
  `claude-code-review.yml` **without checking whether its justification transfers**: there it hides
  an unfixable external quota, here it hid a transient 503 a retry repairs. Now retries on
  429/5xx (4/12/30s) and posts a "did NOT run" comment on total failure. Suite 599 → **611**.
- **`workflow_dispatch` added** because `opened`/`ready_for_review` alone means a fix to the
  reviewer cannot be tested on the PR that introduces it. `synchronize` would also solve it but
  would comment on every push — owner's call, not a CI side effect.

**Do NOT conclude CodeRabbit is on the wrong plan.** It shows "review rate limited" on *some* runs
of a PR and "Review approved" on others — on #150 it did both. It reviews once per PR and
rate-limits the re-reviews triggered by later pushes. That is expected behaviour, not evidence of
a plan problem. (An earlier read of this signal in HANDOFF treated "rate limited" as "reviewer
unavailable"; it is not.) Whether the free OSS Pro plan is actually applied is still worth one
look in their dashboard, but the rate-limit message is not the evidence for it.

## DUPLICATE — implemented 2026-08-05 (branch `feat/sinteza-actualizata-slug-stabil`)

IZZ-0151 said *what* (the synthesis updates, the slug does not change); this is the *how*, with the
§7 empirical numbers. **Measured on the rebuilt archive, 7443 articles.** Duplicate pairs (same
rubric, ≤6h, Jaccard ≥ 0.5 — the 2026-08-04 metric): **623**, i.e. 706 articles = 9.5% of the corpus.
Composition **B/B 295 · C/C 183 · B/C 145** — so **328 (53%) contain a synthesis**, and every one of
them clears `_strict_match`. They stayed separate for one reason: `main.py:83` filtered candidates to
`model == "B"`, so a published C was invisible to `attach_recent`.

- **The matching threshold is NOT touched.** Only *who is eligible* changes, so the over-merge profile
  stays the one already calibrated for B. Simulated over the 261 reconstructed runs: **470 new
  attachments**, 288 of which promote a group to a synthesis → **+1.1 AI calls per run** (budget 12-18).
- **The representative is now the already-published member** (`processed_by` is the marker), not the
  chronologically oldest. Otherwise a new item one minute older would take over the permalink.
  Its sources are UNIONed, so an absorbed synthesis does not lose its corroboration.
- **Slug is persisted in state** and never recomputed (`render.assign_slugs`, called before
  `state.save`). Proven on the 2507 live articles: **0 slugs differ** from the old algorithm, so no
  permalink moves. `updated` feeds `dateModified` — the only honest signal for "same URL, new text".
- **Found in passing, fixed here because this change made it worse:** `select.sources_coherent`
  judged sources by their URL slug, and BBC/DW serve opaque ids (`c8j2vmzxezro`, `a-77798543`).
  47 of 3511 synthesis sources yield a single token and **all 47 are ids** — no real slug lands
  there. Any synthesis citing BBC or DW therefore failed the gate and was NOT published: **10 of the
  67 rejected** on the archive were real corroborated stories (BBC+Guardian+Politico on the Kyiv
  attack). Sources with fewer than 2 slug tokens are now skipped, same principle as the existing
  `if not t` branch. Verified strictly more permissive: nothing accepted before is rejected now.
- Real run against live feeds (fallback provider, no AI quota spent): **5 syntheses updated at the
  same permalink instead of duplicating**, out of 18 C clusters.
- **Known, deliberately left open:** a group whose only external domain equals the absorbed C's own
  domain still fails `is_synthesis_candidate` (1 distinct domain), so that duplicate survives.
  Counting a C's own `sources` there is a clustering change and needs its own §7 measurement.

**MERGED as `9cdc29f5` (#142), registry row IZZ-0154.** It accidentally carried **#141** with it
(`fix(htmlart): eticheta copertei nu mai poate fi None sau doar spatii`, `efe194c8`): a concurrent
session had left the working tree on `fix/eticheta-copertei-none`, so `git checkout -b` for #142
branched from there instead of `main` — **the §19 shared-working-tree hazard, in the flesh**.
Verified byte-identical: `git diff main pr141 -- generator/htmlart.py tests/test_htmlart_eticheta.py`
is empty, and CI ran over the combined diff. **#141 has nothing left to deliver; it is still open,
with a comment saying so.** Lesson, cheap to apply: `git log -1` before `git checkout -b`, or use a
worktree.


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

## SIRUTA — Slice 2 SHIPPED, #125 MERGED `2ac3c399` (2026-08-03)
**The blocker below is resolved; the section is kept because its measurements are still the reason
the design looks like this.** `geo.clasifica(text, judet)` now takes the source's county and matches
villages only within it. Verified independently on the live corpus before merge, not taken from the
PR body: **10 reclassifications, 10 correct** (Nicula, Dezmir, Igriș, Urseni ×2, Bulgăruș, Merișor,
Copalnic; the three that looked wrong — articles saying "județul Timiș" dropping to `local` — name
the village explicitly in the teaser, so `local` is the more specific and correct answer).
`data/sate_judet.csv` is byte-for-byte reproducible from `tools/build_gazetteer.py`: **12540**
villages, 42 counties. (The PR body said 12.596 until merge day — a count from before the
first-names filter `5329ecba` dropped 56 rows. Corrected in place.)
Synthetic false positives DO exist and did not occur in 1733 articles: a Iași paper writing
"Crucea Roșie" would match village CRUCEA. The general form of that problem is #126 below.

### The measurements that produced the design (2026-08-02) — still valid
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

## DECIDED 2026-08-03 EVENING — owner handed the decisions over ("deblochează tot, decizia îți aparține")
Each of these was decided on a measurement taken the same evening, not on judgement. The numbers
are here so nobody re-derives them; the reasoning is here so anyone can overturn them with a
better measurement.

- **SIRUTA leftover (a), county lists for regional papers — CLOSED, not worth the mechanism.**
  Measured on 1714 articles: giving a `judet` to the three "regional" papers that are really
  single-county (`zdp`→Prahova, `criticarad`→Arad, `newsbucovina`→Suceava) would change **1**
  article. Giving genuinely multi-county papers their region's whole village set would change
  **3** more (Banat 2, Oltenia 1) — and one of those three is dubious ("Salcia" in a story about a
  cruise ship grounded on the Danube). **4 articles total.** Against that, a Transylvania paper's
  gate would grow from ~300 village names to **2817**, a quarter of the global 12540 set this file
  already records as regressing the gate by 49 articles. Bad trade. Not doing it.
- **SIRUTA leftover (b), curated geographic features (Bucegi, Ceahlău, Dunărea) — CLOSED, negative
  expected value.** Measured with a 21-feature probe: **15** articles of 1714 would gain a level,
  but the breakdown kills it — "Marea Neagră" accounts for 5 and **every one is Ukraine-war
  coverage**, "Dunăre" for 8 and most are national infrastructure stories. The list would push war
  reporting onto the Romanian geographic axis, which is the exact leak `geo.py` exists to stop.
  Genuine wins were ~2 (turists stranded on Platoul Bucegi, a crash on Transalpina). Not doing it.
- **`significance` (Open 6) — CLOSED, will not be populated.** #124 deleted the dead template
  branch. Populating it means asking the AI for a 1-10 score and re-ordering by it, layered on top
  of #118's measured pre-AI ranking (corroboration + freshness + md5 tie-break). It costs AI budget
  per article, has no measured benefit, and anyone rewriting the ordering around it will silently
  drop #118's tie-break — which review already had to catch once.
- **`/surse/` granularity (Open 5) — SETTLED at 7 regions.** Already implemented
  (`ORDINE_REGIUNI_AFISARE`, `_COMASARI_AFISARE`) and already an editorial decision from
  2026-08-02. Reopening it churns the geo axis for a presentation preference. Closed.
- **`/surse/` MAP (Open 5) — DEFERRED with an explicit bar, not rejected.** Every county is already
  reachable by text link, so a map adds convenience, not reach. Home Perf is held at 80 by CLS
  (§13) and pa11y is at 0 errors — an interactive SVG of 41 counties risks both for unmeasured
  demand. If it comes back, the bar is: static SVG, text links inside it, no JS, no layout shift,
  pa11y still 0.
- **Interactive guides (Open 2) — the blocker was mis-stated and is now narrow.** The calculator
  EXISTS and the dated-fact mechanism exists (#119/#120/#121: `verificat`, sourced yaml, a test
  tying `_SALARIU_MINIM_FALLBACK` to the entity). What is actually open is one fiscal rule: the
  personal deduction is taken as a flat 20%, which understates art. 77 Cod Fiscal at low incomes —
  4.325 brut returns 2.616 where sources say ~2.699. **Decision: this is not something to invent,
  it is something to READ** — same route that fixed the minimum wage (HG 146/2026 read on the
  portal, article quoted). Fetch art. 77, quote the deduction table verbatim, then implement. If
  the act cannot be read — the failure mode that keeps `alocatia` at `verificat: false` — nothing
  is published and the guide keeps saying "ordin de mărime, nu suma exactă din fluturaș".

## Merged 2026-08-04 EVENING (account A — announce, per §14)

- **#131 `7d41a2f2` — a bare official announcement is published as original title + link.**
  The owner said "ai libertate totală", so the editorial threshold that had been parked for him was
  taken: `select.titlu_fara_informatie` rejects a URL as title, a filename (extension or >=2
  underscores), a title made only of generic announcement words, and fewer than 3 words. Measured
  on the 69 bodyless announcements on main: **rejects 5, no false positives** (`ANUNȚ PUBLIC`,
  `Anunț PUZ` x2, `Publicitate`, `CP_Renta viagera_C2025_29.07.2026`). End to end through the gate:
  **2025 -> 2020** published. `pytest` 532 passed, 2 xfailed.
  → Words are counted as **runs of letters**, not `.split()` pieces: `41 mana+fainare+putregai` is 3
  real words in 2 pieces and is the only false positive `.split()` produces on today's corpus.
  `util.title_tokens` is deliberately not reused — it strips stopwords and <=3-letter words.
  → Thresholds are measured: >=4 words wrongly drops `Concurs Functii publice`; >=1 underscore
  wrongly drops `SITUATII FINANCIARE TRIM II_2026`; "starts with an ordinal number" drops 4
  legitimate Urlati phytosanitary bulletins out of the 5 it catches.
  → Deliberate gap: `DEMETER JOZSEF NIMROD – 27.07.2026` passes. No mechanical rule catches it
  without also dropping legitimate marriage publications, which share the name+date shape.

- **#134 `9d382388` — GitHub's scheduler drops `schedule` firings, so the corpus ages.** Not a bug in
  our code; measured over the last 40 runs. 08-04 got **4** runs (03:32, 06:37, 10:47, 14:35Z)
  instead of 12, 08-03 got 8, 08-02 got 10 — all starting 20-35 min after the `:13` mark, with 3-4h
  holes in the morning and near-normal cadence in the UTC evening. At 17:57Z the corpus was **192
  minutes** old because the 16:13Z firing never happened.
  → Fix in the PR: cron becomes **hourly**, and a new `cadenta` job asks the API when
  `data/articles.json` was last committed, letting `pipeline` run only if that is **>=105 minutes**
  ago. No checkout, ~10s of runner, and the repo is public so the minutes are free.
  → **The publish cadence does not change** — that is the point, and §17 forbids raising it. 105 +
  the ~12 minutes a run takes keeps two content commits >=2h apart, so the ceiling stays 12/day =
  ~360 Cloudflare builds/month against a free ~500. Simulated over 30 days: 0% drops -> 12.0/day
  (max gap 2.0h); 35% drops -> 9.4/day (6.0h) against 7.3/day (10.0h) for today's 2h cron.
  → Manual dispatch bypasses the gate. If the API call fails the gate goes **red** and the pipeline
  is skipped — fail-closed on purpose: a broken gate that let everything through would mean 24
  builds/day, the failure class that stopped deploys on 5-9 July.
  → **First thing to check tomorrow:** the 19:13Z firing must be SKIPPED by the gate (content was
  committed 18:12Z, so 61 min < 105) and the 20:13Z one must RUN (121 min). If instead every hourly
  firing runs, the gate is not working and the Cloudflare build budget is burning 2x.

- **#133 PROVEN IN PRODUCTION the same evening, not just in simulation.** Run `30936585807` (started
  18:00:42Z on `7d41a2f2`) hit the exact race, because a human push landed on main at 18:06Z while
  it ran. Verbatim from the commit step: `! [rejected] main -> main (fetch first)` ->
  `##[warning]push respins (incercarea 1) - reaplic peste origin/main` ->
  `Successfully rebased and updated refs/heads/main.` -> `push OK la incercarea 2`. The content
  commit `4a2e83f2` is on main and `mirror` rendered `content_sha`, green. Before #133 this run
  would have reported SUCCESS with the content discarded.

- **#133 `402731e1` — a rejected push made the run green and threw the content away.**
  Measured over the last 30 `build.yml` runs: **6 (20%) hit `! [rejected] main -> main (fetch
  first)` and all 6 reported SUCCESS**, dropping 200–500 content files each (runs 30902133131,
  30810393072, 30745934913, 30743060578, 30731227441, 30718426381). Cause: a human pushes to main
  during the ~11 minutes a run takes, so it fires exactly on working days. `git push || echo` made
  the rejection exit 0.
  → Push now retries 5× with `git fetch origin main` + `git rebase origin/main` between attempts and
  **exits 1** when the content did not land. **No `-X theirs`**: history has 10 human commits on
  `data/*.json` against 265 bot ones, so a conflict there can be a real manual edit — it goes red
  instead of being overwritten. Zero cost on the measured cases: the human push that killed run
  30902133131 was the #130 merge, touching only `generator/` and `tests/`, so it rebases cleanly.
  → Second defect, same severity: `mirror` checked out `main` without checking main contained the
  run's content. On 30902133131 it took `2dd5aa22` (the human #130 merge), rendered the **old
  corpus** and published it to `ramanul.github.io`, green. It now checks out `content_sha`, the sha
  `pipeline` actually committed. An empty `ref` silently falls back to the default branch, so it is
  refused before checkout. Rejected as too expensive: `ref: main` + `fetch-depth: 0` +
  `merge-base --is-ancestor` — `size-pack` is **356 MiB**, paid 12×/day for an invariant that
  becomes true by construction.
  → **Verified by running, not claimed.** `build.yml` does not run on PRs, so the step was extracted
  verbatim from the YAML and driven against real repos: a local bare origin, a `--depth=1` clone
  (same shape as `actions/checkout`), a third clone playing the human. **17/17** assertions across
  five scenarios — normal push, the measured race, the conflicting race, nothing-to-commit, dead
  remote. The riskiest assumption, "rebase works in a shallow clone", is what scenario B proves.
  → Still uninvestigated: run `30884653008` (08-04 06:37Z) failed at the pipeline step with exit 1,
  unrelated to the push race.

## Merged 2026-08-04 (account A — announce, per §14)
Three PRs, all verified by running before merge. `main` after them: **ruff clean, 503 passed,
2 xfailed.**

- **#127 `35ea00c0` — a region name after a capitalised word is a brand, not geography.**
  Corpus 2130: `regional` 12 → 5, **7 articles changed, all 7 wrong before**, `zonal` (149) and
  `local` (729) bit-identical. The measurements and the six compared options are in the section
  below; what belongs here is what the tests caught that the corpus could not. **Two defects in the
  guard itself:** "Autostrada A3 Transilvania" escaped because the preceding token ends in a digit,
  and **"În Ardeal" was rejected** — a sentence-initial locative preposition looks exactly like a
  compound proper name. The second was caught by `test_clasificare`, which predates this work; the
  1714-article corpus contains no "În Ardeal" at all. **A corpus measurement is evidence of
  coverage, not of correctness.** Guard now consults `_MARCA_GEO` before rejecting, reusing that
  list rather than duplicating it.
  → **NOT confirmed on live**, same as #126: classification runs in `process.py`, not at render, so
  the 7 move only at the next full pipeline run (cron `13 */2`).
  → Two known misses are pinned as `xfail(strict=True)` rather than left as prose: the lowercase
  connector ("Gazeta **de** Transilvania") and the feminine genitive — see below, it is a real
  recall hole worth its own slice.
- **#128 `92072fbf` — a narrow ruff gate (F + DTZ) in `tests.yml`, before pytest.** 13 findings,
  **zero real bugs**, but two that `--fix` would have made worse; the triage is in the section
  below. New `ruff.toml`; `ruff` is deliberately NOT in `requirements.txt`.
  → **Proved on the runner, not only locally:** the `Lint (ruff …)` step in PR #128's `pytest` job
  printed `All checks passed!`.
  → **Trap for anyone touching `generator/render.py`:** two of its imports are deliberate
  re-exports. `sources_coherent` is imported *from `generator.render`* by `tools/qa_check.py:18`,
  which `build.yml:106` runs, so `ruff --fix` there breaks the nightly pipeline with an
  ImportError, not just pytest.
  → Second trap, cheap to hit: **ruff reads `# noqa` out of ordinary prose comments** and warns
  about an invalid directive. A comment explaining the rule had to be reworded to avoid the string.
- **#129 `ba5b31ef` — local press wave 1, 11 county papers.** Ten counties get their first
  dedicated newspaper (DOLJ, ALBA, MURES, BOTOSANI, SIBIU, BIHOR, SUCEAVA, GIURGIU, plus BUCURESTI
  and third Cluj/Brașov titles). Verified **through `generator.fetch._fetch_one_guarded`, not a
  reimplementation** — the defect `feed_check.py` has had twice: **11/11 return items**.
  `monitorulbt` timed out once and returned 8 on retry; recorded as transient.
  → **`monitorulsv` carries `"type": "sitemap_news"` and MUST keep it** — that site has no RSS at
  all, every candidate path returns 200 while silently serving the homepage.
  → **`b365` is the only entry without `judet`, deliberately.** BUCURESTI has zero rows in
  `data/sate_judet.csv`, so the field opens nothing — and
  `test_toate_ziarele_judetene_declara_un_judet_cunoscut` forbids exactly that. It caught the field
  when it was first added "for consistency". Do not fill it back in.
  → **Watch, does not block:** `gazetadecluj` is the only feed in the wave with `bozo=1`
  (SAXParseException, 9 entries recovered). If it ever shows as "200 dar 0 articole …
  SAXParseException" in `dead`, that is this — not the network. And 11 new sources mean more new
  items competing for ~10 AI calls per run; watch `stats["deferred"]`.
- **Review reality on all three: there was effectively no second eye.** CodeRabbit reviewed #127
  (2 comments, one taken, one declined with a reason) and returned `Review limit reached` on both
  #128 and #129. `claude-review` completed green on #127 and #128 **with no observations at all**
  (on #128 its step ran 46 minutes and posted nothing; `Token missing notice` was *skipped*, so the
  token was present). Gemini is sunset, Codex over quota. **A green reviewer check in this repo is
  currently not evidence that anything was reviewed.**

## MEASURED 2026-08-03 NIGHT — four parallel probes, recovered after one died on the session cap
Four read-only agents (`wf_77838023-cf5`). Three returned; the fourth hit "session limit" **after**
writing its answer, which was recovered from its transcript (its `StructuredOutput` call failed
schema validation, so the journal recorded no result — the finding is in
`feedback_agenti_omorati_de_plafon.md`: read the last transcript line before concluding an agent
produced nothing). Photos → Open 1. Local press → Open 4. The other two are here.

### `ruff --select F,DTZ` — triaged finding by finding, 12 findings, ZERO real bugs
`ruff` 0.16.1 is available but **not** in `requirements.txt`, and **no workflow runs any linter**
(grep for `ruff|flake8|pylint|lint` across `.github/workflows/`, `.coderabbit.yaml`, `AGENTS.md`
returns nothing). There is also no `pyproject.toml`/`setup.cfg`/`ruff.toml` at the root — a
`.ruff_cache/` exists, so it has been run ad hoc, never configured. Natural host for the gate is
**`tests.yml`** (the only workflow that both triggers on `pull_request` and installs
`requirements.txt`), one step before the slow pytest run.
- **`render.py:15-18`, four F401 — do NOT run `ruff --fix` on this file.** Two of the four are
  deliberate re-exports and deleting them breaks more than the suite: `sources_coherent` has **9**
  call sites, seven in `tests/test_render_editorial.py` plus `tools/qa_check.py:18` importing it
  *from `generator.render`* — and `build.yml:106` runs `qa_check.py`, so a `--fix` would break the
  nightly pipeline with an ImportError, not just pytest. `_slug_stems` has 2 (`test_render_editorial.py:121-122`).
  `_BODY_PLACEHOLDERS` and `title_tokens` are genuinely unused and can go.
  **Mechanical trap, verified empirically:** a `# noqa: F401` on the first line of a parenthesized
  multi-line import does NOT cover names on continuation lines — the statement has to be split so
  the noqa sits on the physical line carrying the two re-exports.
- **`fetch.py:134` DTZ007 is a FALSE POSITIVE — do not change the semantics.** `_parse_w3c_date`
  parses date-only naive on 134 and does `.replace(tzinfo=timezone.utc)` on 135; ruff misses it
  only because the `d` binding crosses a statement boundary. This is one of the two functions the
  whole `published`-UTC invariant rests on (`test_published_is_utc.py` pins it). Chaining the two
  statements into one clears the diagnostic with zero behaviour change.
- **Both DTZ005 in `render.py` are benign.** `:230` is the footer copyright year (would show the new
  year ~3h early on 31 Dec, nothing more). `:755` feeds `now_timestamp` into `calendar.html`, and
  since `.timestamp()` on a naive datetime interprets it as local — and `_dt.now()` IS local — the
  epoch is already correct today; the one genuine hole is the October DST fold, worth ~an hour a
  year. Both sides of the comparison are absolute epochs, so fixing only `:755` does not
  desynchronize it from `:735`.
- Remainder is cosmetic and autofixable: 4× F541 (`print(f"\n=== Rezumat ===")` in four near-clone
  `tools/` scripts), 1× F401 (`import json` in `tests/test_stale_new_items.py`), 1× DTZ011
  (`tools/log_slice.py:41` `date.today()` — real inconsistency, negligible consequence: the CSV's
  `date` column is written by this machine at UTC+3 and by CI at UTC, then sorted
  lexicographically, which is the same mixed-offset string-sort `test_published_is_utc.py` exists
  to prevent for `published`. Its fix must ALSO drop `date` from the line-21 import or it
  introduces a fresh F401).

### Regions used as brands — the task's premise was PARTLY FALSE, and the fix follows the data
Measured over the whole 1714-article corpus. Only **9** articles are `regional`, and **commercial
brands are not the dominant defect**: 6 of the 9 are **"Republica Moldova" — a sovereign state, not
the historical region** — and exactly 1 is the seed case (Banca Transilvania). At occurrence level,
**24 of 31** region-name matches in the corpus are non-geographic, 13 of those being
Republica/Republicii Moldova; the rest are Universitatea Transilvania ×4, Banca Transilvania ×2,
Piața Agro / Autostrada A3 / Festivalul de Film Transilvania, Gazeta de Transilvania, ISU Țara Bârsei.
Options compared on the same corpus (`kills_wrong` / `kills_right`):
| option | wrong fixed | right lost |
|---|---|---|
| (a) commercial-word blacklist | 1 | 0 |
| (a2) blacklist + REPUBLICA/ISU/CAS/… | 7 | 0 |
| (b) `_AMBIGUE`/`_MARCA_GEO` mechanism | 7 | **1** |
| (c) reject if preceded by a capitalised word | **7** | **0** |
| (c3) (c) with a sentence-start exception | 5 | 0 |
| **(c+) = (c) + geo-relational whitelist** | **7** | **0** |
- **Do NOT reuse the `_AMBIGUE` mechanism here (option b).** Measured, it is the only option that
  kills a correct geographic article (`tion`, "Capitala **de** Moldova" — `de` is not a locative
  preposition) and at occurrence level it rejects "în **regiunea** Banatului", because REGIUNEA is
  not in `_MARCA_GEO`. This confirms the hypothesis the probe was sent to test: historical regions
  appear legitimately without a locative preposition, so #126's gate does not transfer.
- **Chosen: (c+)** — in `clasifica()`, only when `nivel == "regional"`, reject a match immediately
  preceded (spaces only, no punctuation) by a capitalised word that is not in
  {NORDUL, SUDUL, ESTUL, VESTUL, CENTRUL, REGIUNEA, ZONA, TOATA, INTREAGA, PROVINCIA}. ~6 lines,
  cost zero for the rest of the index (the guard evaluates only on the 12 regional names). On the
  corpus it is bit-identical to (c) — none of the 10 whitelist words precedes a region name in 1714
  articles — but on synthetic probes it saves (c)'s only false-positive class ("Toată Oltenia se
  află sub cod roșu", "Regiunea Banatului a înregistrat…"). (c3) was rejected by measurement: its
  sentence-start exception destroys the seed case, since "Banca Transilvania oferă…" sits at
  position 0.
- **Known misses, stated up front:** lowercase-connector collocations survive ("Gazeta **de**
  Transilvania", 1 occurrence, article already `local`), and "în Moldova" with no further marker
  stays undecidable (1 article).
- **Collateral finding that limits the whole rubric's recall, separate slice:** `_ARTICOL =
  (?:ULUI|UL|UI)?` does not cover the feminine genitive. Verified directly — **"Transilvaniei",
  "Olteniei", "Munteniei", "Moldovei", "Dobrogei", "Bucovinei", "Crișanei" do not match at all**
  today, while "Banatului"/"Ardealului" do. Corpus impact is zero right now (the 2 affected
  articles are already `zonal` by county name), but "nordul Transilvaniei" is a very common press
  formulation and is invisible to the gate.
- **[OPINIE] Taxonomy question for the owner, not code:** Republica Moldova stories should arguably
  not touch the Romanian geographic axis at all. Today they fall to `None` and from there to an
  AI-chosen topic rubric — better than `regional`, still not an "extern" rubric.
- Confidence 8/10: 9 regional articles and 31 occurrences is a small sample dominated by one
  pattern and one source (`el_moldova`, 5 articles); the geographic/brand judgements are the
  probe's own reading of the text, not independent labelling.

## ÎNCHISE DE PROPRIETAR 2026-08-04 — nu le mai ridica, nu le mai „verifica"
Alexandru le-a spus explicit, iar pe una dintre ele a spus-o **a patra oară**. Dacă o sesiune
viitoare simte nevoia să le re-deschidă, răspunsul e aici, nu la el.

- **DARK MODE FUNCȚIONEAZĂ.** Punct. Fostul „Open 0" e șters mai jos. Nu-l mai testa, nu mai cere
  browserul sau o poză din consolă, nu mai propune fixuri. A confirmat de patru ori și l-a
  enervat, pe bună dreptate, că tot revine. **Orice sesiune care re-deschide subiectul din proprie
  inițiativă face o greșeală de proces, nu una tehnică.**
- **Știrile despre Republica Moldova NU merg pe o rubrică „extern".** Întrebarea de taxonomie
  ridicată la #127 e închisă cu NU. Comportamentul de azi (cad pe `None` → rubrica de temă aleasă
  de AI) rămâne.
- **Vocabular, pentru că a fost jargon neexplicat:** „**copertă generată**" = desenul pe care
  `covers.py`/`htmlart.py` îl pune pe articol când nu există fotografie reală (dreptunghiul colorat
  cu pictograma rubricii). „45 de fotografii pe live" vs „1302 coperți generate" înseamnă: 45 de
  articole au o poză adevărată, restul au desenul. **Nu folosi cuvântul fără să-l explici.**

## STAREA FELIILOR 2026-08-04 09:40 (contul A) — #130 ATERIZAT, #131 DESCHIS

**1. PR #130 — MERGED**, squash `2dd5aa22`. Toate check-urile verzi pe `5988da68`.
→ Ce face: itemele a căror `description` nu adaugă cel puțin `config.MIN_SUBSTANTA_CUVINTE` (5)
cuvinte peste titlu nu mai ajung la AI și nu se mai publică. Plus scoaterea din prompt a regulii
care cerea fabricarea. Detalii complete în `specs/sinteza-fara-substanta.md`.
→ **Consecință verificată, nu presupusă:** trei surse tac complet — `digisport`, `monitorulsv`,
`piataauto`. Nicio rubrică nu rămâne goală (`sport` are gsp+prosport, `auto` are autocritica,
`nwradu` 81-97 cuvinte noi, `startup` 19-30). Nu re-verifica asta.
→ **Observația CodeRabbit („`src_extra` se pierde prin căile AI") a fost REFUTATĂ pe cod**, nu
ignorată: cele trei funcții sunt în `process.py`, nu în `main.py`, și niciuna nu pierde câmpul.
Gaura reală era că nimic nu lega cele două capete — acoperită acum de `tests/test_substanta_sursa.py`.
Recenzia a rămas `CHANGES_REQUESTED` (stale, dinainte de commit-ul care îi răspunde); răspunsul e
pe PR. **Nu redeschide subiectul.**

**2. FELIA 2 — implementată, PR #131 deschis**, `feat/anunturi-oficiale-fara-teaser`, rebazat pe
main de după #130. Anunțurile de primărie fără corp se publică acum ca titlu original + link.
→ `anunt_oficial_fara_corp()` în `select.py` e un **predicat unic** folosit și de poartă și de
randare, ca cele două să nu se poată depărta. Acoperă ambele forme de „fără corp": placeholder-ul
(69 iteme) și teaserul identic cu titlul (10) — 79 în total, măsurate pe `data/articles.json`.
→ Poarta e slăbită STRICT pe `processed_by == "official"`. `tests/test_anunt_oficial_fara_teaser.py`
(12 teste) pinează inclusiv regresia inversă: un item neoficial fără substanță tot NU se publică.
→ Randarea nu emite elemente goale (`.card` e flex cu `gap`, un `<p>` gol lasă o gaură vizibilă);
`meta description` spune cine a emis anunțul în loc să iasă goală.
→ Local: `526 passed, 2 xfailed`. **Capcană de mediu, nu de cod:** fixturile din
`test_entities_verified` și `test_sitemap_editorial` re-randează doar când `output/` lipsește, deci
două rulări pytest în paralel în același working tree pică una pe alta (`WinError 145`). Rulează-le
singure înainte să crezi că e o regresie.

**3. Rămas deschis, decizie separată:** cele **62 de articole deja publicate** din sursele fără
substanță (52 digisport + 10 piataauto) rămân până expiră pe `ARTICLE_TTL_DAYS`. Poarta tratează
un `src_extra` absent ca „nu știu", nu ca „fără substanță" — **intenționat**, altfel un singur
deploy ar goli feedul. Un backfill e o decizie, nu o scăpare.

**4. Cozi mai vechi, în ordinea din jurnalul de la 07:00:** genitivul feminin din `_ARTICOL`
(xfail-ul e deja scris și va confirma singur ziua în care trece) · valul 2 de presă locală (cei
~65 de candidați există doar în transcriptul sesiunii web, contul B trebuie să re-emită lista) ·
art. 77 Cod Fiscal · confirmarea pe live a lui #126 și #127 (se mută abia la următoarea rulare
completă de pipeline, cron `13 */2`).

**Ce NU ridica, sub nicio formă** — vezi secțiunea „ÎNCHISE DE PROPRIETAR" de mai sus:
dark mode funcționează (a spus-o de patru ori), Moldova nu merge pe „extern", iar „copertă
generată" se explică, nu se aruncă ca jargon.

**Lecția de metodă din sesiunea asta, mai valoroasă decât feliile:** un defect care se vede doar
în TEXTUL PUBLICAT nu poate fi prins de teste care citesc doar cod — de asta a supraviețuit
atâtor iterații. Și „feedul răspunde" ≠ „feedul are conținut": `monitorulsv` a fost adăugat în
#129 după ce s-a verificat că sursa întoarce iteme, nu că itemele conțin ceva.

## Open
-2. **REZOLVAT — PR #132 MERGED**, squash `cb5b1ff4`. Descrierea de mai jos rămâne ca istoric al
   diagnosticului, fiindcă e ușor de re-făcut greșit. Ce a rămas de măsurat: efectul PE CORPUS
   PUBLICAT se vede abia după o rulare completă de pipeline (cron `13 */2`) — până atunci
   `data/articles.json` poartă tot descrierile vechi, deci nu compara cifrele înainte de asta.
   `fetch.py:474` citea
   `entry.get("summary") or entry.get("description")` și atât. `feedparser` pune
   `<content:encoded>` în `entry.content[0].value`, deci corpul nu e citit niciodată.
   → **Măsurat pe feed-uri reale, nu presupus:** din 12 surse testate (dintre cele 32 care produc
   anunțuri „fără corp") **9 trimit un corp real în `content:encoded`**. Exemplu:
   `pl_neamt_municipiul_roman` — 10/10 iteme cu `summary` de **0 caractere** și `content:encoded`
   de **1677 / 2278** caractere. Anunțurile alea NU sunt fără corp; pipeline-ul le orbește.
   → **Contra-verificat pe `digisport`:** are `content:encoded` pe toate cele 100 de iteme, dar
   **max delta 0** față de `summary` — acolo chiar sursa nu trimite nimic peste titlu. #130 rămâne
   corect pentru digisport. Cele două cazuri nu se confundă.
   → **Consecință pentru #131:** „titlu + link" e răspunsul potrivit doar pentru cele ~3 surse din
   12 care chiar n-au corp. Pentru restul, fixul e o linie în `fetch.py`, iar `process_official` ar
   produce un teaser real în loc de „Detalii pe sursa.". **De rezolvat ÎNAINTE de merge pe #131.**
   → Firul vine de la agentul „Audit surse fara substanta" omorât de plafon la 09:17: singura lui
   frază supraviețuitoare, recuperată din transcript, era exact ipoteza asta. Nu am testat toate
   cele 32 de surse — 12 din 32, deci proporția 9/12 e o estimare, nu un total.

-1b. **§13 rulat pe #131 — fără regresie, cu cifre.** Lighthouse mobil, articol pinuit pe `/auto/2/`,
   aceleași versiuni (LH 13.4.1, pa11y 9.1.1, Chrome 150.0.7871.187):
   main `830276dc` → home **83**/100/100/100, articol **91**/100/100/100, pa11y home **0**;
   #131 `9789a643` → home **83**/100/100/100, articol **91**/100/100/100, pa11y home **0**.
   Identice. Pe suprafața NOUĂ (pagina de anunț `/local/publicitate/`, care nu există pe main,
   deci n-are before): **Perf 91 · A11y 100 · BP 100 · SEO 100**, pa11y **0 erori**, iar auditul
   `meta-description` trece cu scor 1 — adică fallback-ul „Anunț oficial publicat de …" chiar
   previne regresia SEO pentru care a fost scris. **O rulare per revizie**, deci per §13 nu poate
   rezolva un efect de Perf sub ~8 puncte; A11y/BP/SEO și pa11y sunt însă deterministe.

-1. **DECIZIE DE PROPRIETAR, deschisă de #131: 7 din cele 79 de anunțuri au titluri care nu spun
   nimic — iar la un anunț fără corp titlul e SINGURA informație.** Măsurat pe `data/articles.json`
   2026-08-04, titluri de maximum 2 cuvinte: `Anunț PUZ` (x2), `Publicitate`, `ANUNȚ PUBLIC`,
   `41 mana+fainare+putregai`, `CP_Renta viagera_C2025_29.07.2026` (un nume de fișier),
   `https://e-consultare.gov.ro/` (un URL brut ca titlu). Mediana e 11 cuvinte, deci **72 din 79
   sunt în regulă** — dar §7 spune „never publish raw, truncated headlines... SKIP the item", iar
   un card al cărui întreg conținut e cuvântul „Publicitate" e exact zgomotul pe care îl promitem
   că-l scoatem. Verificat pe preview-ul lui #131: cardul se randează corect, fără gaură — deci
   nu e un bug de randare, e o limită a variantei (b).
   → Opțiuni, nu recomandare unică: (a) prag de cuvinte în titlu pentru anunțurile fără corp
   (ex. ≥3), (b) listă de titluri-capcană (`Publicitate`, `Anunț`, `ANUNȚ PUBLIC`) plus respingerea
   titlurilor care arată a URL sau a nume de fișier, (c) se publică toate, cum sunt acum.
   **Nu am ales singur: pragul e editorial, nu tehnic.**
   → **ÎNCHIS 2026-08-04 seara: proprietarul a spus „ai libertate totală", varianta (b+a) e MERGED
   în #131 (`7d41a2f2`). Nu se redeschide.** `select.titlu_fara_informatie` respinge URL,
   nume de fișier (extensie sau ≥2 underscore), titlu format doar din cuvinte generice, și sub 3
   cuvinte. Măsurat pe cele **69** de anunțuri fără corp de pe `main` (79 la ora auditului, corpusul
   s-a rotit): respinge **5**, zero fals-pozitive — `ANUNȚ PUBLIC`, `Anunț PUZ` ×2, `Publicitate`,
   `CP_Renta viagera_C2025_29.07.2026`. Cap-coadă prin poartă: **2025 → 2020** articole publicate,
   exact acelea 5. `pytest`: 532 passed, 2 xfailed.
   → Cuvântul se numără pe **secvențe de litere**, nu pe `.split()`: `41 mana+fainare+putregai` are
   3 cuvinte reale în 2 bucăți, și e singurul fals-pozitiv pe care `.split()` îl produce azi.
   Praguri respinse prin măsurare, nu prin gust: ≥4 cuvinte aruncă `Concurs Functii publice`;
   ≥1 underscore aruncă `SITUATII FINANCIARE TRIM II_2026`; „titlul începe cu număr de ordine"
   aruncă 4 buletine fitosanitare legitime din 5 prinse.
   → Limita cunoscută, lăsată descoperită deliberat: `DEMETER JOZSEF NIMROD – 27.07.2026` trece.
   Nicio regulă mecanică nu-l prinde fără să arunce și publicațiile de căsătorie, care au același
   tipar nume+dată.

0. **SINTEZA PRODUCE CLICKBAIT FLUENT CÂND SURSA NU TRIMITE FAPTE — raportat de proprietar
   2026-08-04, cu exemplu de pe live. Diagnostic complet în `specs/sinteza-fara-substanta.md`.**
   Pe scurt, fiindcă e cel mai important lucru deschis acum:
   → **DATE:** `digisport` trimite `description` **identic** cu `title`. Măsurat pe `fetch_all()`:
   **58 din 256 de iteme (23%) sosesc cu 0–4 cuvinte în plus față de titlu**, deci fără nimic de
   sintetizat. Șase surse sunt 100% așa (`digisport`, `monitorulsv`, `piataauto` + 3 primării).
   Pe corpusul publicat: **62 de articole din 2130**.
   → **COD, prompt:** `process.py:27` cere explicit „*dacă descrierea e săracă, extrage esența din
   titlul original*", în timp ce linia 22 interzice clickbait-ul. Când singura intrare e un titlu
   clickbait, cele două se exclud și modelul nu are portiță de refuz.
   → **COD, poartă:** `_quality_gate` verifică doar FORMA IEȘIRII (titlu nevid, corp ≠ titlu, nu
   `fallback`, netrunchiat). O parafrază fluentă a unui clickbait trece toate verificările.
   **De asta „atâtea iterații și fixuri" n-au prins-o: defectul nu e vizibil în cod, ci doar citind
   textul publicat, iar niciun test nu citește textul publicat.**
   → §7 conține deja regula corectă („SKIP the item, do not publish it broken"); nu e implementată
   pentru cazul ăsta.
   → **Autocritică ce trebuie păstrată:** `monitorulsv` a fost adăugat de mine în #129 după ce am
   verificat că sursa *întoarce iteme* — nu că itemele *conțin ceva*. Intrând prin `sitemap_news`,
   nu poate trece niciodată un prag de substanță. **„Feedul răspunde" ≠ „feedul are conținut".**
   → **Blocat pe o decizie de proprietar** (în spec): pragul taie și anunțurile de primărie cu
   descriere goală, care sunt exact motivul rubricii `local`. (a) nu se publică · (b) listă de
   anunțuri fără teaser · (c) se citește pagina sursă.
1. ~~**DARK MODE**~~ — **ÎNCHIS de proprietar 2026-08-04: funcționează.** Vezi secțiunea de mai sus.
   Textul lung de aici a fost șters intenționat: cât timp rămânea scris ca „open", fiecare sesiune
   îl relua și îl întreba din nou.
1. ~~**PR #101 (locality lead photos) awaiting owner sign-off**~~ — **MERGED 2026-08-02 03:19.**
   §16's third state is now CLOSED, and it closed by **refuting the number this entry used to
   carry.** What stood here — "nobody has confirmed the 129 photos ON LIVE; `smoke_live.py` or a
   look at izz.ro closes it" — was wrong in both halves (measured 2026-08-03 evening, full census).
   → **Live serves 45 real photographs, not 129.** Every article URL in the live sitemap was
   fetched with `?cb=<ts>`: 1380 `<loc>`, 1354 article-like, 0 HTTP errors → **PHOTO 45,
   GENERATED 1302, NO-ART 7** (the 7 are the 6 `/ghiduri/*` plus `/instrumente/calculator-salariu/`,
   evergreen pages that legitimately carry no article art). The 45 are 44 in `/local/` + 1 in
   `/economic/`, over 20 distinct localities (Ploiești 7, Sebeș 5, Năvodari 4, Bistrița 3…),
   licences CC BY-SA 3.0 ×16, CC BY-SA 3.0 ro ×11, CC BY-SA 4.0 ×10, PD ×6, CC0 ×2.
   → **[INTERPRETARE] The 129→45 gap is corpus turnover, not a broken feature.**
   `data/leadphotos.json` holds 141 non-miss entries, 107 of which match art_ids in the local
   `data/articles.json` (1714 records) while the deployed corpus is 1354 — photo-bearing local
   announcements age out under `ARTICLE_TTL_DAYS` faster than they are replaced. Not proven by
   HTTP; the census only proves the count.
   → **`smoke_live.py` CANNOT close this, and the old line saying it could was the actual defect.**
   The script has no notion of a real photo: its two image checks assert only that `og:image` ends
   in `/cover.jpg` and that the files are >5 KB. Both hold for a *generated* cover (measured:
   generated `cover.jpg` = 42884 B, `art.jpg` = 35848 B). Its line "coperti generate pe esantion:
   5/5" counts generated covers — **it would print all-ok on a site with zero photographs.**
   → **Counting from the homepage is impossible by construction:** `_card.html:5` and
   `index.html:22-27` emit an identical `<img src="/{cat}/{slug}/art.jpg?v=…" alt="">` for both
   kinds. The discriminator is `<figcaption class="art-credit">`, which exists only on the ARTICLE
   page (`article.html:37-39`, rendered only when `a.lead_credit` is truthy). Hence the census had
   to fetch all 1354 pages.
   → **Consequence for the reader of this file: zero of the 126 articles linked from
   `https://izz.ro/` today carry a photo** (hero + 125 cards, each probed). A visitor landing on
   the homepage sees 126 generated covers; the photos are reachable only by paging into `/local/`.
   Whether that is acceptable is an editorial question, not a bug — but it is the honest state.
   Confidence 9/10 on "45 exactly": point-in-time snapshot, `build.yml` cron `13 */2` can redeploy.
1. **SIRUTA Slice 2 — MERGED `2ac3c399`. Only the two leftovers at the end of this item are open.**
   Villages match only
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
   4/14 fallout ≈ 29%, so the ~⅓ estimate was right.
   **RE-CHECKED 2026-08-03 evening from the same home IP — the 4 failures are now 2 recoveries,
   1 blocked, 1 dead, and the 10 successes were re-confirmed live with their exact config form:**
   ✅ **`monitorulsv.ro` RECOVERED by a different path — it has NO RSS at all.** `/feed/`, `/rss`,
   `/rss/`, `/feed/rss/`, `/?feed=rss2` all return 200 but silently land on the homepage; `/rss.xml`
   is a real 404; the homepage HTML contains **zero** occurrences of "rss" or "feed" and no
   `<link rel=alternate>` — feeds are absent, not moved. But
   `https://www.monitorulsv.ro/sitemap-news.xml` serves 200 `application/xml`, 58 `<url>` with
   `news:title` + `news:publication_date`, newest stamped today, and `robots.txt` is `User-Agent: *`
   with no Disallow and declares that exact sitemap — the same legality basis already used for
   `piataauto`. **It MUST carry `"type": "sitemap_news"`; without that key `fetch.py` treats it as
   RSS and feedparser yields 0.**
   ✅ **`saptamanagiurgiuveana.ro` was a WRONG PATH, not a dead site.** WordPress lives under
   `/wp/`: the homepage 30x's to `/wp/` and declares `href="https://saptamanagiurgiuveana.ro/wp/feed/"`,
   which returns 200 directly over HTTPS, 10 entries, bozo=0.
   ⛔ **`gazetademaramures.ro` — the feed is real and excellent (50 entries at `/rss`, NOT `/feed/`),
   but it is UNREACHABLE by `fetch.py` on this machine, and the cause is TLS trust, not anti-bot and
   not IP.** The server sends a complete chain (leaf ← Let's Encrypt `YR1` ← ISRG `Root YR`); the
   missing piece is the **root `ISRG Root YR`, absent from both this machine's store AND certifi
   2026.05.20** — verified separately, both fail identically with `CERTIFICATE_VERIFY_FAILED`.
   `http://` 301s to https, so there is no plain-HTTP workaround; browsers succeed because they do
   AIA fetching, Python's OpenSSL does not. **Added as-is it becomes a permanently `dead` source.**
   Whether a GitHub runner's ca-certificates carries that root is NOT verifiable from here — test it
   in CI before merging, or wait for the trust stores to catch up.
   ❌ **`dobrogeanoua.ro` — dead and NOT recoverable, stop spending time on it.** Every path 404s;
   `/?feed=rss2` serves the homepage; `robots.txt`, `sitemap.xml` and `sitemap-news.xml` are all 404,
   so the `sitemap_news` escape hatch that saved `monitorulsv` is unavailable. Root cause: it is not
   a CMS site at all — a hand-written static `index.php` brochure page declaring
   `charset=windows-1250`, 13 links total (mostly ads to local businesses), year strings 2010-2016.
   There is no machine-readable output to consume. CONSTANTA is already covered by `dobrogeanews` +
   `dobrogeaonline`.
   **Two editorial cautions for the wave, both measured:** `monitorulexpres.ro` would be the FOURTH
   BRASOV source (after `bizbrasov`, `newsbv`, `mytex`) and its newest item is about **Covasna** —
   pinning `judet: BRASOV` on a paper that routinely covers the neighbouring county is exactly the
   mismatch `judet` exists to avoid, so add it WITHOUT `judet`, or add `mytex` only (§7 diversity).
   `b365.ro`: BUCURESTI is in `geo.REGIUNI` but has **0 rows** in `data/sate_judet.csv`, so `judet`
   there buys no village matching — correct metadata, functionally inert. `gazetadecluj.ro` is the
   only feed in the batch with `bozo=1` (SAXParseException, 9 usable entries recovered); `fetch.py`
   tolerates it today but it is one XML tweak away from zero — if it ever shows as "200 dar 0
   articole … SAXParseException" in `dead`, that is this. The other 65 candidates exist only in the web
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
   numbers that no longer exist). Mixed `+03:00` and `Z` offsets order wrong.
   → **ANSWERED — do NOT "do this first", the refactor was rejected on purpose.** This bullet was
   written at 07:51; the decision landed at 09:06 (`c6ca5254`) and is in the settled list above.
   The three sorts stay on strings and `tests/test_published_is_utc.py` guards the invariant
   instead (1736/1736 entries `+00:00`, both parsers end in `astimezone(timezone.utc)`, plus an
   end-guard that compares string order against real chronological order on `data/articles.json`).
   Rewriting them to `datetime` would hide the real exposure: order would look right while mixed
   offsets kept leaking into `datePublished` and the feed.
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

- **#125 MERGED (`2ac3c399`) — a village counts as local only when it is in the source's county.**
  SIRUTA Slice 2. Full detail in the SIRUTA section above. Merged on a self-review plus an
  independent corpus verification, because **no external reviewer ever ran**: CodeRabbit hit
  `Review limit reached` at 12:21, Gemini is dead, Codex over quota, and the `claude` job was
  skipped. A 4-agent internal review was launched instead and all four were killed mid-run by the
  account session limit — their transcripts are the only reason one of the checks below exists.
- **#126 MERGED (`63128e7d`) — an ambiguous name counts as a place only when the text marks it as one.**
  Found while verifying #125, and it is **older and larger than #125**: it lives in the global UAT
  index, on `main`, independent of villages. Measured on 1733 articles, **49** were `local` on the
  strength of a name that is a real locality and something far more common in text: "Vladimir Putin
  în invazia Ucrainei" (commune in Gorj), "Curtea de Casație din Franța", "Banca Centrală
  Europeană", "Filarmonica George Enescu", "Denis Drăguș", "Oana Roman", "ÎNSCRIERI SÂMBĂTA 22.08",
  and eight horoscopes plus a SpaceX rocket crashing into **Luna** — a commune in Cluj.
  Fix: names in `_AMBIGUE` stay in the index but require a geographic marker (administrative
  qualifier or locative preposition). It cannot be a global rule — 890 of 1606 capitalized matches
  in the corpus carry no marker and are legitimate ("Universitatea Cluj", "Primăria Giurgiu").
  Verified: 484 passed; corpus diff is exactly those 49, no correctly-local article lost.
  **Known and NOT fixed by it:** "Banca Transilvania" moves from `local` to `regional` — still
  wrong, but that is historical regions used as brand names, a separate slice.
  CodeRabbit reviewed it (`CHANGES_REQUESTED`, 2 findings) and one was worth more than it asked:
  it wanted a test for the ambiguity guard in the village loop, and that test cannot be written —
  every `_AMBIGUE` name is also a UAT, so the loop's existing index check already skipped them all.
  The guard was unreachable; it was removed (`45c16e9a`) after checking the corpus diff is 49 with
  it and 49 without. Declined: a spec comment block above `_AMBIGUE` (§5.1 asks for a spec before
  code, not in the source) and Ruff PT006 (not enabled here; string-form parametrize is the style
  in 8 places across 5 test files).
  **NOT yet confirmed on live.** The classification runs in `process.py`, not at render, so
  `--render-only` cannot show it — the 49 articles move only on the next full pipeline run
  (cron `13 */2`). Verified as code and on the corpus; the live check is still owed.
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
