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

**Updated:** 2026-08-07 (account A — eleven PRs landed today: #151–#161)

## Open — verified in code 2026-08-07, not carried over on trust

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
