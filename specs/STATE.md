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

**Updated:** 2026-08-08 evening (account A — #162/#164/#165 landed; attribution dossier + badge
locality fix + image label manifest landed directly on `main` under an explicit owner mandate)

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

## Open — verified in code 2026-08-07/08, not carried over on trust

**A. County map — SHIPPED on `/surse/` (#166), but it is NOT what the owner asked for.**
The deferred item said "`/surse/` map" and that is what was built, to its bar (static SVG,
text links, no JS, `aspect-ratio` reserves height, 39 county links + 3 inert shapes).
Geometry: `data/harta_judete.json` from **Natural Earth (public domain)** via
`tools/build_harta.py` — GADM was rejected on purpose, same borders but it forbids
redistribution and commercial use and this repo is public. Do not swap the source back.
**The gap, owner's words (2026-08-09): "în surse apare, dar acolo să caute cititorii?"**
He wants a map that selects **NEWS**, not sources. Verified in code why that cannot be built
on what exists: articles carry **no county** — only `category` (`local|zonal|regional`;
663/513/247 today). The place is computed at render time for the cover badge and thrown away.
There are **no per-county pages** either, only the three category pages.
So the real slice is: persist the county at ingestion → generate `/judet/<slug>/` →
re-point the map. **Consequence to state up front, not discover later:** the category is
computed once at ingestion (Open 6), so a county field populates only for NEW articles — the
map would start sparse and fill over ~7 days as the current stock expires. Not a bug; it is
how the pipeline is built. **The front-end audit for #166 was never run** (session ran out of
budget): `/surse/` was Perf 81 / A11y 100 / pa11y 0 before, and the page grew 53 → 100 KB from
inlining. If Perf dropped, raise `TOLERANTA` in `tools/build_harta.py` — no other code moves.

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
2. **Salary calculator takes the personal deduction as a flat 20%** (`static/calc-salariu.js:53`) —
   understates art. 77 Cod Fiscal at low incomes: 4.325 brut returns 2.616 where sources say ~2.699.
   **Not something to invent — something to READ**, same route that fixed the minimum wage. Quote
   the deduction table from the act, then implement. If the act cannot be read, publish nothing.
3. **Model C is not batched** — `process_cluster` is one AI call per cluster while B batches 10.
   Gate is already instrumented: read `stats["deferred"]` over 2–3 real runs before building it.
   Do not re-litigate the threshold (`build.yml` overrides the budget to 18, not the default 12).
4. **`WS-0025`, blocked.** The `# nosemgrep` on `generator/render.py:15` does not suppress; two
   hypotheses, undistinguishable today (no code-scanning alerts to query, local semgrep broken).
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
