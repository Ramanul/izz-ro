# STATE — project execution state

> Single source of truth for "where we are". Manager-owned; updated at the end of every slice.
> Executors get it read-only. **Hard cap: ~40 lines of content.** When it grows past that, cut the
> settled history into `specs/istoric-executie.md` — do not let it accumulate here. It is read at
> the start of every session, so every stale line is paid for twice: in tokens, and in an executor
> re-implementing something that already shipped. `git fetch` immediately before rewriting it.
>
> **Cut on 2026-08-07** from 1330 lines. What that cost, stated so nobody repeats it: `## Open`
> listed as open work two things that had already shipped — the "synthesis produces fluent
> clickbait" item (fixed by `config.MIN_SUBSTANTA_CUVINTE = 5` + `main.py:73`) and the local-press
> wave (all 14 domains are in `config.SOURCES`). Everything below was **verified against the code
> today**, not copied forward.

**Updated:** 2026-08-13 (account A — W, X and Microsoft Clarity landed; see this line before older ones)

## Landed 2026-08-13 directly on `main` (account A — announce to B, per §14)
**`11c9a45a`** — item W below committed as-is (cascade Ollama fallback, JS-rendered town-hall
scraper, `_fallback_href` fix, `tools/scan_surse.py`). **`8590537f`** — item X below: the 8
permanently-red map tests fixed (rewritten against real identifiers) or deleted (2 files that
asserted on inline-JS tokens inside `.github/workflows/visual.yml`, a premise dead since the real
check moved into `tools/visual_check.py`). Suite: **829 passed, 8 xfailed, 0 failed** (was 8 failed).
**Item 4 (`WS-0025`, `# nosemgrep` on `render.py:15-16`) resolved by direct measurement, not
guessed:** installed semgrep locally (`pip install semgrep`, was "broken" only in the sense of
"not installed"), ran the exact rule `r/python.lang.security.use-defused-xml.use-defused-xml`
against a probe file with the identical import line but no suppression comment → **1 finding**;
same rule against `generator/render.py` (which has the full-ID suppression) → **0 findings**. The
suppression works. Not committed (nothing to change in code — the finding was already correct);
closing the line item here.

**`657bf769` — Microsoft Clarity (`y1to63p42e`), owner request** (`IZZ-0185`, `IZZ-0186`). Loads
only after opt-in, same gate as GA4 (`personalize.js:loadClarity`). **Three measured facts worth
not re-deriving:** (a) the bootstrap tag fires `muidsync()` → `c.clarity.ms/c.gif`, the Microsoft
**advertising** ID sync, and it triggers **only** on `ad_Storage:'granted'` — we pass `'denied'`,
and `c.clarity.ms` is deliberately **out of `img-src`** so the browser blocks the pixel even if
that flag regresses. **Do not "fix" that CSP omission.** (b) The tag config declares the upload
host as `k.clarity.ms`; the **real run uploaded to `n.clarity.ms`** — hence the wildcard
`*.clarity.ms`. Pinning exact hosts breaks Clarity silently in production. (c) Consent key bumped
`v2` → `v3`: session recording is a new processing *purpose*, not a new vendor. Verified in a real
browser both ways: refuse → **0 external requests**; accept → tag + lib + `n.clarity.ms/collect`,
`c.gif` count **0**, cookies `_clck`/`_clsk` only (no `_uet*`). Consent bar +20px on mobile
(157→177px). Suite **829 passed, 8 xfailed**. **Still open: CSP is not enforced by the local
static server — confirm the live `Content-Security-Policy` header on izz.ro after deploy.**

## Attribution — read this before touching classification or covers
**`specs/atribuire-cercetare-si-plan.md` is the dossier**: 7 external systems, 8 distinct causes,
a 6-stage plan. Do not re-research it; it was paid for once. Landed today, on top of #164/#165:
- `tools/eval_atribuire.py` — runs attribution against `specs/gold-geo-*.tsv` and prints two
  fractions. **Run it before and after any change to `geo.py`.** Baseline 2026-08-08:
  category 25/39 (64%), place-on-badge **31/32 (97%)**, up from 26/32 before `loc_din_sursa`.
- `geo.loc_din_sursa()` — locality decoded from a town-hall source slug, between title and county.
- `media/labels.json` — binds each cover to its visible text, so a changed label triggers a
  targeted redraw. **First run only marks existing images, never redraws them**: the owner refused
  regenerating old covers on 2026-08-06 (`IZZ-0163`). `FORCE_REGEN=1` remains the opt-in.
- Still open from the plan, in order: **E1 permalink decoupled from category** (owner decision —
  blocks all retroactive correction), E3 focus score instead of `max()`, E4 separate topic/place
  axes (owner decision), E5 gold set grown to ~150 + CI gate.
- `tests/test_sitemap_editorial.py` has **10 pre-existing errors** (verified with `git stash`,
  unrelated to the above). Full suite: 676 passed, 2 xfailed, 27 errors.

## Landed 2026-08-12 directly on `main` (account A — announce to B, per §14)

**`9f3e3ad2` — `guard.anomalie` (layer 8) was written and never called; now it runs.**
It sat green and unreachable in the working tree from 08-09 to 08-12 while two commits
already on `main` (`2585f467` and the Cajvana comment in `local_sources.py`) described it in
the present tense as catching the defacement. Same defect class as `hold_important` below —
a lying function, and the worse kind, because the incident report read as if the hole were
closed. Wired at all four points where the guard actually runs: the three `fetch.py`
ingestion paths and `moderation.apply`. The moderation one is what matters next time — it
runs on every build, so a defacement already in `articles.json` disappears at the next
rebuild instead of waiting for a human to hand-add the slug. That wait was Cajvana's two
days live. **Measured before wiring: 3 flagged out of 3130 `ro`-source titles (0.10%), all
three hostile, 0 false positives.** Tests target the WIRING, verified by mutation (stub the
layer → "Hacked by Chinafans" passes both paths). `IZZ-0170`.
**Scope, stated so nobody reads it as more:** the proposed anomaly baseline had three axes —
language, cadence, topic mix. **This is one.** A defacement written in Romanian still passes,
and cadence (8 articles at exact 3-hour intervals, the strongest tell at Rovinari) is still
measured by nothing. `specs/securitate-ingestie.md` §5.1 now says so. **Cadence is next.**

**`4f78c901` — the gold set gets a second gate: geographic level.** `geo.clasifica` had no
frozen gate at all; it was measured only by `tools/eval_atribuire.py`, which reads
`articles.json` and erodes with the TTL — **17 of the 40 gold rows have already expired**.
The new test reads title+teaser from the TSV (new `teaser` column, because
`process._text_clasificabil` feeds both). **Its weakness is measured, not assumed:**
`clasifica`→`None` fails 15/15, but `clasifica`→always-`local` fails only **1/15**, because
14 of 15 evaluable cases are `local`. It is a wide-meshed net in one direction, not proof,
until E5 grows the set with `zonal`/`regional` cases from non-official sources. `IZZ-0171`.

**`stash@{0}` in the izz clone is superseded in full — do NOT pop it (`IZZ-0172`).** The
2026-08-11 journal says it holds the gold-geo work; it does not. It holds `method.md`,
`terms.md` and `tools/gen_images.py` at a pre-`67e44e1e` state, i.e. the **old art. 50
wording** ("niciun redactor nu aprobă fiecare text înainte să apară", "verificare umană
ulterioară publicării") that `IZZ-0165` corrected precisely because it gave the exemption's
conditions away. A pop reverts the legal fix. `gen_images.py` is stale too (`_semnatura`,
`_load_labels`, `media/labels.json` all landed). Dropping it is destructive — owner's call.

## Open — verified in code 2026-08-12; W/X landed 2026-08-13 (see Landed section above), Y verified

**Y. `state.merge()` is dead code but NOT a live bug — do not "fix" it.** Defined at
`state.py:95`; the only caller is `tests/test_state.py:14`. Dedup between fresh items **does**
happen, inline at `main.py:227-236` (#158), and the comment at `main.py:220-222` already says so.
Re-verified 2026-08-13 because the standing "lying function" hunt keeps rediscovering it and
reading it as a live duplicate bug. Touching it would be an opportunistic refactor (§5.6).

**A. News map — SHIPPED directly on `main` (2026-08-12, owner + GPT, outside any Claude
session), closes the old gap below.** `/static/harta-stiri/` is a real news map: 473 articles
placed in 37 counties, dataset built by `tools/build_harta_data.py` from `articles.json` +
`geo.py` (`loc_din_titlu`, `loc_din_sursa`) + SIRUTA, county-level dot on the same Natural
Earth SVG that `/surse/` already used. In primary nav (`templates/base.html`). Verified
**live** on 2026-08-12: `map.json` → 200, 35 counties with markers, 473 items in the list.
`tools/visual_check.py` (Playwright, real browser) now covers it, incl. a mobile pass —
this closes what the paragraph below asked for.

**A1. Tap targets too small — real, separate from A2, NOT the "mari probleme" bug.**
24 of 42 county shapes are under 44px (WCAG/Apple/Material minimum) on a 390px viewport,
smallest 9×15px; the 35 news-count bubbles are ~11.7×11.7px. Measured with
`tools/visual_check.py`. Not fixed — owner decision on approach (bigger bubbles / invisible
larger hit-area / drop direct county-tap on mobile for the existing search+list). `IZZ-0176`.

**A2. FIXED, owner-confirmed on device 2026-08-12 (`e3832692`).** The map smeared into
6-7 stacked copies on real touch scroll. Root cause found from a phone screen recording
(OpenCV frame extraction, since headless/emulated scroll never reproduced it): `buildMap()`
recreated the `<canvas>` DOM node on every redraw, which on real Android compositing let old
and new elements paint over each other mid-scroll. Fix: `ensureCanvas()` creates the element
once and every redraw resizes/repaints that same node. `backdrop-filter` stays closed as an
explanation (falsified earlier); ChatGPT's ~20-commit SVG→Canvas rewrite did NOT fix this —
its own "regression tests" assert on identifiers that don't exist in the shipped file (8/12
fail when run), so its "verified" fixes were never really verified (`IZZ-0177`).
**A3. FIXED same session (`3d85a3a8`, `e8f9ddf0`) — tapping felt "stuck on one county."**
Two separate causes, both real: click handler picked the FIRST marker within hit-radius, not
the closest (overlapping bubbles in small/dense counties kept resolving to whichever county
came first in `map.json`'s key order — verified with București/Ilfov, centers 4px apart on a
375px viewport, each now resolves correctly). Second: the only way back to all counties was a
toolbar button ABOVE the map card, which scrolls off-screen on mobile once zoomed in, with no
affordance on the map itself — added a `.map-back` button anchored to the map card, shown only
when a county is selected. Now picks
the nearest. Verified: tapped into Sibiu, cross-checked the 28-item news list against the
county stat — correlation between selection and the right-hand list is correct.
**Taxonomy rename, owner decision 2026-08-12 (`b645e65c`) — category `zonal` → `judetean`,
including the URL slug**, an explicit exception to the 2026-07-17 rule that slugs never
change. 295 already-published `/zonal/` articles migrated to `judetean` in `articles.json`;
`render.py` now writes a Cloudflare `_redirects` wildcard (`/zonal/* → /judetean/:splat`,
301) so old indexed links don't 404. Full detail: `sessions/A/2026-08-12-2255-harta-canvas-reuse-fix.md`.

0c. **Old gap this replaces, kept one cycle for the record:** as of 2026-08-08 the only map
was the static SVG on `/surse/` (39 county links, no JS) — the owner said explicitly
"în surse apare, dar acolo să caute cititorii? [...] vrea o hartă care selectează
ȘTIRI, nu surse" — cannot delete the paragraph's substance without erasing why A above
exists. Geometry source stays **Natural Earth (public domain)** via `tools/build_harta.py` —
GADM was rejected on purpose (forbids redistribution/commercial use, repo is public); do not
swap it back.

0. **#165 LANDED (`9ad5d287`) — kept here because the mechanism must not be reintroduced.**
   `state._resync_pinned` ran on every `load()` and overwrote the ingestion-time classification
   with the *source's* declared rubric. Two mechanisms, opposite rules; the older one ran last and
   won. **663 of 1247** articles from geographically-pinned sources sat on a rubric their own text
   contradicts (390 `local`→`zonal`, 229 `local`→`regional`, 36 `zonal`→`regional`). Practical
   consequence: **a county paper could never publish a `local` story**, however explicitly the text
   named the commune. Verified three independent ways, incl. live (`/local/` 404, `/zonal/` 200 for
   the same slug). No retroactive migration — the 663 keep their permalinks and expire in ~7 days.

0b. **`hold_important` is a promise the code does not keep — and it is now load-bearing for AI Act
   art. 50.** `moderation.yaml` documents it as "true = clusterele C/importante așteaptă aprobare
   înainte de publicare". All the flag actually does is `generator/main.py:359-360`: a `print`
   saying "de tratat la randare". **Nothing gates anything.** Set it to `true` and C clusters
   publish exactly as before, while the operator believes they are held. This is not a missing
   feature, it is a lying one. It matters beyond hygiene because art. 50's exemption turns on
   "human review or editorial control" + "editorial responsibility" (`IZZ-0165`), and this flag is
   the only mechanism in the repo that could implement pre-publication review. **Plan written, not
   executed, awaiting owner "go"** — 3 slices (make the flag gate; a review queue; an approval log
   as the documented evidence the Commission asks for), in
   `sessions/A/2026-08-09-0632-art50-corectie-si-hold-important-negasit.md`. Slice 1 alone is
   legally sufficient if the owner actually reads before approving. **Do not automate the review
   itself** — the exemption exists because a human reads and takes responsibility; automating it
   destroys the thing it is meant to prove.

1. **Cernavodă / national-stakes local events — the real classification gap, and the only one left
   that needs AI.** 39 geo-axis articles name Cernavodă, 30 from national sources, **all 39 pass
   `_locul_e_subiectul`**, so #156 removes zero. The owner's rule ("LOCAL = where it happens") has
   no notion of a local event with national stakes. **Owner authorised the AI route.** Design + dry
   test + acceptance criteria are written and unrun, handed to account B:
   `handoff/to-B/2026-08-07-raza-nationala-si-ce-a-ramas.md`. Cheap alternatives already killed by
   measurement: `WS-0029` (multi-source coverage, 453/1301 = 35% false positives) and the entities
   route (national-institution lists rot).
2. **LANDED 2026-08-13 (`5dc92ca7`) — deducere personală is now degressive, per art. 77
   Cod Fiscal (Legea 227/2015, modif. OG 16/2022), zero persoane în întreținere.** Formula quoted
   from two independent citations of the actual statutory text (agree on numbers, internally
   consistent: 20%→0% over 40 steps of 0,5pp = the stated 2.000 lei / 50-lei-per-step band):
   20% la salariul minim brut, scade 0,5pp la fiecare 50 lei peste minim, 0% peste minim+2.000 lei.
   `static/calc-salariu.js` + `templates/calculator.html` (paragraful explicativ, care mai spunea
   "1.950 lei" — greșit, plafonul real e 2.000) actualizate. **Verificat local, în browser**: la
   brut=5.000 (minim 4.325) → deducere 584 lei (era 865 flat), la brut=7.000 (peste plafon) →
   deducere 0. **Nerezolvat: cifra "~2.699" din nota veche de mai jos nu a putut fi reprodusă.** La
   brut = salariul minim exact, formula corectă dă ACELAȘI rezultat ca varianta flat (20% e 20%
   indiferent de metodă) — 2.616 lei, deci bug-ul degresivității nu explică acel număr. Fie sursa
   citată folosea un salariu minim diferit de referință, fie o altă metodologie; nu invent o a doua
   explicație fără sursă. Cine a scris nota inițială (dacă știe sursa exactă a cifrei 2.699) o poate
   clarifica.
3. **Model C is not batched** — `process_cluster` is one AI call per cluster while B batches 10.
   Gate is already instrumented: read `stats["deferred"]` over 2–3 real runs before building it.
   Do not re-litigate the threshold (`build.yml` overrides the budget to 18, not the default 12).
   **Still blocked 2026-08-13**: needs real `stats["deferred"]` numbers from GitHub Actions build
   logs, and `gh` is not authenticated in this environment (`gh auth status` → not logged in) —
   cannot fetch them. Not guessed.
4. **`WS-0025` — RESOLVED 2026-08-13, see "Landed" above.** The suppression on
   `generator/render.py:15-16` works (measured: `semgrep` installed locally, same import line
   fires 1 finding without the comment, 0 with it, on the exact registry rule).
5. **Owner decisions pending, do not decide these alone:** photos on cards (CC-BY attribution ·
   top-anchored crop, `WS-0022`) · `/surse/` map (deferred with an explicit bar: static SVG, text
   links, no JS, no layout shift, pa11y still 0) · interactive guides (which interactivity, and the
   figures behind it — §10 territory).
6. **Blind window, structural, affects every classification fix:** the category is computed **once,
   at ingestion**, and never recomputed. Any geo/topic fix reaches only new articles; existing ones
   heal by expiry (~7 days). Retroactive migration is **rejected** — the category is part of the
   permalink. State this whenever reporting a classification fix; do not re-propose the migration.
   **Corrected 2026-08-08:** "never recomputed" was wrong in one direction that mattered —
   `_resync_pinned` *rewrote* it on every `load()` (item 0). The blind window is real; the claim
   that nothing touches a stored category afterwards was not.

## Merged 2026-08-08 (account A — announce to B, per §14)

**#162** `STATE.md` cut 1330 → 69 lines, history moved not deleted · **#164** the cover badge takes
the place named by the TITLE, not the source's county — 249/463 `local` and 71/475 `zonal` were
printing the literal word "LOCAL" because national sources have no county in `config.SOURCES`;
badge-on-category drops −52% on both, plus 230 labels refined from county to locality.
Gemini's finding on `eticheta_judet` was checked by running the code and is **false**
(`IZZ-0159`) — do not "fix" it.

**`2262249f`** legal pages now state that AI output is published automatically, with **no
pre-publication human sign-off** — the old "cu supraveghere umană" could be read as approval before
publishing, which is exactly the AI Act art. 50 exemption we do NOT qualify for (in force
2026-08-02). Also states images are NOT AI-generated (programmatic covers + Wikimedia), where
art. 50 is stricter. **No per-article label** — §7 forbids per-article methodology notices;
that stays in `/legal/method/` only. Owner decision needed if a visible per-article label is ever
wanted, since it would require revoking §7 (`IZZ-0164`).

**`67e44e1e` corrects the above** (`IZZ-0165`). Art. 50's exemption reads "human review **or**
editorial control" + "editorial responsibility for the publication" — it does **not** say "before
publication"; the secondary source we worked from had added that. So the first wording ("no editor
approves each text before it appears") was giving away the exemption's own conditions for free.
Now the pages state automatic publication **and** continuous editorial control + responsibility.
**Open, owner only:** the Commission requires *substantive* review — "an editor who reads, revises
and takes responsibility" qualifies, a spell-check does not. Whether the daily pass clears that bar
is a fact about our process, not something code can answer. If it does, no per-article label is
owed at all and §7 stays untouched.

## Merged 2026-08-07 (account A — announce to B, per §14)

Eleven PRs: **#151** defusedxml + semgrep ratchet 4→2 · **#152** JSON-LD `@graph` · **#153**
town-hall diacritics · **#154** Moldova-the-country off `regional` · **#155** sport off the
geographic axis · **#156** a named place claims the axis only if the story is ABOUT it (188/1075
leave, 17.5%) · **#157** the 404 page stops lying · **#158** one story from two feeds is no longer
two pages · **#159** the model's raw topic is saved as `ai_cat` · **#160** a UAT swallowed by a
compound proper noun (`Casa Albă`, `Curtea de Apel București`, `Bursa de Valori București`) no
longer opens the axis · **#161** docs-only: the real publish cadence is an hourly cron plus a
105-minute gate, not `13 */2`. Full measurements and the routes rejected on numbers:
`specs/istoric-executie.md`.

**Measured 2026-08-07 and closed as a dead end — do not spend a slice on it:** the `_COMPUSE_NEGEO`
queue #160 left open. The remaining candidates are either sports clubs (`CFR Cluj` 65 geo-axis
articles, `Universitatea Craiova` 27, `Farul Constanța` 26, `U Cluj` 12, `FC Botoșani` 12), already
covered by #155's `ai_cat != "sport"` guard — **and unmeasurable today: only 1 club article in the
corpus post-dates #155** — or legitimate institution+place compounds where the pattern is dominantly
correct (`Primăria Brașov` 8, `Consiliul Județean Cluj` 11, `Primăria Sebeș` 6). Re-measure in ~7
days, once the corpus has rolled over, not before.

## Where the rest lives

`specs/istoric-executie.md` (everything above, verbatim — measurements, killed hypotheses, the
bot-challenge diagnosis, owner answers) · `specs/registru.tsv` + `python tools/registru.py find`
(decisions, incl. what was rejected and why) · `specs/masuratori-frontend.md` (Lighthouse/CLS) ·
`specs/istoric-operational.md` (cadence, delegation, autonomy history) · `../HANDOFF.md` (the
cross-account state, ~30 lines).
