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

**Updated:** 2026-08-15 (account A — inventory sweep across sessions; see this line before older ones)

## Landed 2026-08-17 on `main` (account A — announce to B, per §14)

**`main` was never verified. Fixed at the cause, not the symptom — #183 (`9912ca65`), `IZZ-0235`.**
`tests.yml` ran on `pull_request` only, so `main` could sit broken indefinitely and **every new PR
was born red**, with its author having every reason to blame their own change. That is exactly what
happened: the red run this morning was on `ci(security): pin claude-code-action`, which touches no
Python at all. Two dead imports were sitting in `main` — `process_cluster` in `generator/main.py:18`
and `pytest` in `tests/test_deferred_cauze.py:23`.

**This was the second occurrence in three days.** `IZZ-0231` (#180, 14 Aug) carries the same title —
"main pică ruff, deci checkul `pytest` era roșu pe TOATE PR-urile deschise" — and fixed it by
cleaning three files under `tools/`. The cause was untouched, so `main` broke again in 72 hours with
different files. Do not fix this by cleaning files a third time.

`push: branches:[main]` added with a `paths` filter (`**.py`, `requirements.txt`, `ruff.toml`,
`tests.yml`). This does **not** reverse the documented "deliberat nu pe push" decision — that
decision protected the 2-hourly content commits, which touch only `data/*.json` and stay filtered
out. The registry holds no decision restricting *lint* on push; `IZZ-0124`/#128 added the gate, it
did not narrow it. Lint is 2s, the suite ~90s — both numbers from the workflow's own comment.
`tests.yml` sits inside its own `paths` filter, so the merge tripped the new guard itself: the
`push` run on `main` came back **success**. `CLAUDE.md` §4 corrected in the same PR — it claimed
"deliberat nu pe push" (now false) and "Lint / type-check: neconfigurate" (false since 4 Aug —
`ruff.toml` exists and CI runs it).

## Landed 2026-08-16 on `main` (account A — announce to B, per §14)

Suite **926 passed, 8 xfailed** (was 900; +22 from the gold rows, +4 from the recovered Mistral
test — the arithmetic closes exactly).

**The most useful thing today was work NOT done.** `STATE.md` said "Cadence is next"; the cadence
axis had been measured dead the same day it was written (`IZZ-0174`). The stale pointer cost a
slice before `securitate-ingestie.md` §5.1 and `registru.tsv` caught it. Corrected in place, with
all four reasons moved up here — the spec is not read at session start, this file is.
**The axis still open is topic mix, not cadence.**

**`03c73a46` — gold set +11 rows, level gate 12× tighter (E5).** The gate's own comment recorded
its weakness: `clasifica`→always-`local` failed **1** test of 15, because 14 of 15 evaluable rows
were `local`. Added `#41-#51`, all `judetean`, all from **non-official** sources — the only ones
that reach `clasifica` in production (`_cazuri_nivel()` excludes `pl_`/`cj_`/`pr_` because
`process_official` never touches `category`). Labels are hand-judged per article on title+teaser.
**Measured by mutation: always-`local` now fails 12, was 1.** All 11 agree with today's code, so
they are regression protection, not documented bugs — nothing new entered `CUNOSCUTE_NIVEL`.
Guard threshold raised from "at least one" to **8**, verified both ways: with the new rows 69 pass;
with the set cut back to 40 rows the guard fails by itself and asks to be refilled.
**Four candidates deliberately NOT frozen, worth a look:** a solar eclipse classified `judetean`
(looks like a false positive), Dobrogea wind output (subject is the national grid, not the region),
"zona seismică Vrancea" (geological region, not the county), and **"Curtea de Apel București"** —
exactly the compound-noun class #160 targets, so it may be a live miss.

**`a89396bf` — the Mistral PR gate test, recovered from an abandoned branch.** The fix had landed
on `main`; its test had not (one of the 4 "to recover" branches from yesterday's triage). Not a
copy: the branch called the `$GITHUB_ENV` flag `PUSHED`, `main` shipped it as `HAS_CHANGES`, so the
test was adapted to the real name without weakening it. It runs the **actual script** of the commit
step rather than reading the YAML. Mutation: dropping `env.HAS_CHANGES == 'true'` from `Open PR`
fails exactly 1 of 4. Added `/mingw64/bin` to the subprocess PATH — Git-Bash on Windows keeps `git`
there; additive, inert on `ubuntu-latest`.

**`18da4eae` — `harta-data.yml` was the last workflow on soft tags.** All three actions
(`checkout`, `setup-python`, `setup-node`) pinned to SHA, matching every other workflow. It matters
here specifically: the job has `contents: write` and commits the map dataset, and a tag can move
under us without anything showing in a diff. `setup-node` also went v4 → v7, closing the dependabot
proposal; its SHA was verified against **two** GitHub API endpoints, not taken from the agent that
did the inventory. `grep "uses: .*@v[0-9]*$"` now returns nothing repo-wide.

**`03df37c5` — a claim in `tests/conftest.py` was true in one run and false across two
(`IZZ-0195`).** The docstring said no test can see half of someone else's render. `output/` is a
fixed shared path and "reset output" empties it with no lock, so two `pytest` processes on the same
clone — a session and a subagent each running the suite — do exactly that. **Measured: concurrent
run → 899 passed / 27 errors** in `test_sitemap_editorial`, `test_pagination`, `test_pagina_404`;
those same files run alone → 12 passed; the whole suite run alone afterwards → **926 passed, 0
errors**. It reads exactly like a real regression and is none. Not fixed in code (a lock would
complicate the fixture for a case CI never hits — each job has its own runner); documented instead,
with the instruction to check for a concurrent run *before* investigating. Parallel agents need
`isolation: "worktree"` (§19).

## Landed 2026-08-15 on `main` (account A — announce to B, per §14)

Three slices, `8fb9c148` → `bf55ae9f`, from an inventory of every unfinished task across all
sessions. Suite **900 passed, 8 xfailed** (was 876 — the 24 new tests are all from these slices).

**`8fb9c148` — `hold_important` now actually gates. Closes item 0b below.** The flag was a
*lying* one: `moderation.yaml` documented it as "clusterele C/importante așteaptă aprobare
înainte de publicare" and all it did was `print` at `main.py:359`. Set to `true`, C syntheses
published exactly as before while the operator believed they were held. The gate lives in
`moderation.apply` because that runs on **both** the full build and `--render-only`. Approval
is the new `approved` list in `moderation.yaml`, same shape as `blocklist_urls`/`featured`, so
it stays editable from the browser on GitHub. Holding is **last** in the cascade: a blocked or
guard-caught article is *rejected*, not "awaiting approval", or the queue fills with garbage.
Measured on real data: `true` → **451 C syntheses held**, output 2749 → 2427. Tests target the
WIRING (mutation: gate removed → 4 fail), not the presence of a config key.
**Scope, stated so nobody reads it as more:** when a C synthesis is held, the underlying B
article surfaces in its place — that is why the drop is 322, not 451. The gate holds
*syntheses*, not all AI-processed content. Owner chose slice 1 only; the review queue and the
approval log (slices 2-3) remain unbuilt.

**`0f9fe2d3` — the public salary calculator was computing the personal deduction wrong.**
Not a refactor: `static/calc-salariu.js` used `Math.floor((brut - salariuMinim) / 50)`, but the
table in **art. 77 alin. (4)** opens each band at **+1 leu**, not +0: `salariul minim` = 20,00%,
`minim + 1 … + 50 lei` = 19,50%, `minim + 51 … + 100 lei` = 19,00%. With `floor`, a gross of
minimum+1 leu got 20,00% instead of 19,50% — deduction too high, tax too low, **net displayed
larger than the real one**. The two formulas agree only on exact multiples of 50 above the
minimum, so the error hit **49 of every 50** possible salaries. Source:
https://www.noulcodfiscal.ro/titlu-4/capitol-3/articol-77.html
Also added the **alin. (2)** cap (deduction limited to taxable income), absent entirely: below
minimum wage the page printed "Deducere personală: 865 lei" over a taxable income of 650.
The 14 tests do **not** reimplement the formula (that would check a copy against a copy) — they
**extract the calculation block from the shipped `.js` and run it in node**, row by row against
the statutory table. Mutation (`ceil`→`floor`): 5 fail, exactly on the band openings.
**Provenance: recovered from PR #163**, per the check `TASKS-B.md` asked for. **`STATE.md` item 2
credited `5dc92ca7`, which is an ORPHAN commit — not on any branch.** The real one is
`2d0df92f` (identical message, 4h later; a rejected push, redone). PR #163 can now be closed as
recovered, **not** as superseded — it was right about the formula.

**`bf55ae9f` — county tap targets reach the 44px minimum (item A1). PARTIAL, read the limit.**
`hitDistance` puts a 22px CSS floor on bubble reach (was 15.8px); `countyAtPoint` grows the
edge tolerance from 5px to 22px **in steps**, stopping at the first step that catches anything —
because at 22px the small counties' zones genuinely overlap and `find` returns the *first* in
array order, which is exactly the "map feels stuck on one county" bug fixed on 2026-08-12 for
bubbles (`closestHit`). The growing ring gives the nearest county by construction.
Measured in a real browser at 375px, same points before and after, east of Constanța (open sea,
inside no polygon): 0/4/8/12px → **nothing** before, **CONSTANȚA** after; 16-24px → nothing both.
The old code caught nothing *even on the shape's own edge*.
**A1 part 2 landed separately as `ab4dd8b8`** — see its own entry below.

**`ab4dd8b8` — small counties now take priority when tapped (A1 part 2, owner decision).**
The first attempt the same day was reverted: it collected every match at a growing "ring" and
tie-broke by size, so a *distant* small county could win over the one actually containing the
point (Cluj's own interior resolved to Sălaj). The rewrite uses the standard mapping-library
convention instead: **query in ASCENDING shape size, first match wins** — the equivalent of
hit-testing top-down through the render stack with small shapes on top (OpenLayers
`forEachFeatureAtPixel`, Leaflet with SVG). A distant county simply cannot match, so that whole
failure mode is gone. **Polygons are now queried BEFORE the bubbles**: while `closestHit` ran
first, the small-county step never executed for the very pair it was written for, because the
București and Ilfov bubbles sit ~4px apart (IZZ-0177) and "nearest bubble" returned first.
**The steal cap is measured, not guessed.** 44px is geometrically impossible for an 8.6px
enclave without destroying its neighbours — București would need 17.7px per side while the
surrounding counties are only 8-11px deep themselves. Swept 22/14/10/8/6/4/3px against each
county's deepest interior point: 22px breaks 5 counties, 10px breaks 2, at 6px and below only
Ilfov remains. On **usable area** (px² of a county that still selects itself) 6px wins there too:
București **59 → 448px² (×7.6)**, Ilfov **323 → 549px² (×1.7)**, Călărași 1511 → 2010, Dâmbovița
1057 → 1676, Ialomița 985 → 1083; Cluj 1502 → 1073 and Giurgiu 1361 → 1086 lose 20-29% but stay
above 1000px². Even Ilfov — the county București steals from — comes out ahead.
Verified in a real browser at 375px against **40 of 42** counties, using each county's true
interior point (the point farthest from its own boundary). **Do not test with bbox centres**:
Cluj's bbox centre lies 3.9px from the Sălaj border and manufactures regressions that do not
exist. The two remaining: Ilfov at its single deepest point only (its overall area still grows),
and Teleorman, which has **0 articles** and is correctly not selectable.
**What this does NOT achieve:** București reaches ~448px² (a ~21px square), not 44px. For
enclaves the standard cartographic answer is a separate inset box or dot beside the map
(Datawrapper & co. do this for DC, Bremen, Hamburg) — **owner decision, not a constant to tune.**

**Also closed by verification, no code needed** (checked in the tree, not taken on trust):
`tools/feed_check.py` already imports the production fetcher (`generator.fetch._fetch_one_guarded`,
line 32), so the 24 July commitment to validate `claude/feedcheck-real-fetcher` before merge is
**moot**; `liternet` has a working URL in `config.py`. All four `TASKS-MISTRAL.md` tasks were
already done — tasks 1-3 are in `.github/workflows/mistral.yml`, task 4 was the verification
inventory, run today (suite green, `--render-only` 2749 articles). The old note about
"`tests/test_sitemap_editorial.py` has 10 pre-existing errors" is **stale** — the suite is clean.
`requirements-dev.txt` added: `pytest`/`ruff`/`pytest-randomly` existed nowhere in the repo, CI
installed them ad-hoc, and on a fresh machine `pytest` failed with "No module named".

**Branch backlog triaged — 67 remote branches unmerged (was 58 on 14 Aug).** Full table:
account A's session scratch, summarised here. **55 LANDED** (content already in `main`, mostly
rewritten rather than cherry-picked — `git cherry` alone called 29 of them unmerged and was wrong
about 25), **8 DEAD**, **4 TO RECOVER**: `fix/deducere-personala-transe` (now recovered, above),
`claude/mistral-session-blocked-kn73vk` (carries `tests/test_workflow_mistral_pr_gate.py`, absent
from `main` — the workflow fix landed, its test did not), and two dependabot bumps
(`claude-code-action` 1.0.190 — needs a security re-read, `main` is pinned to `be7b93b1`
deliberately; `setup-node-7`, routine).

## Landed 2026-08-14 directly on `main` (account A — announce to B, per §14)

**`148b2c80` — harta știrilor, feliile 1-7 din `specs/harta-imbunatatiri-2026-08-14.md`
(`IZZ-0193`, `IZZ-0194`).** Confirmat pe deployat, nu doar local: **26/26 verificări verzi**
rulate contra preview-ului Cloudflare, plus 872 de teste Python. Garda e
`tools/harta_dom_check.py` — rulează cu serverul pornit din **rădăcina repo-ului**
(`index.html` are căi absolute; servit din `static/harta-stiri/` dă 404 la CSS/JS și pagina
apare goală).

Trei bug-uri care contează pentru oricine atinge harta mai departe:
- **`isPointInPath` citește punctul în PIXELI DE CANVAS, nu în unități viewBox** — transformarea
  se aplică CĂII, nu punctului. Există acum două funcții separate, `pointForEvent` (viewBox,
  pentru buline) și `devicePointForEvent` (pixeli, pentru poligoane). **Nu le uni la loc.**
  Greșeala se ascundea pe desktop (canvas ~820px ≈ viewBox 1000) și rupea telefonul (364px).
- **Selectorul de județ de la tastatură se prăbușea la un buton** după prima selecție, fiindcă
  se construia din `state.visible` (deja filtrat). De aceea `filtered()` are `ignorePlace`.
- **Toleranțele de atins trebuie exprimate în pixeli CSS**, convertite la folosire. În unități
  viewBox se evaporă exact pe ecran mic.

**Neverificat, declarat ca atare:** localitățile suprapuse. Markerii se grupează pe cheie de
coordonate exactă, iar datele curente au **0 puncte partajate**, deci calea de cod nu se poate
declanșa. Garda o raportează `NEVERIFICAT` la fiecare rulare — nu o converti în verde.

**Deschis, decizia proprietarului:** analiza GPT (44 de pagini, 14 aug) recomandă rescrierea
stratului de randare pe **D3 + SVG**. Teza „am atins limita arhitecturii" se sprijinea pe faptul
că mobilul e cel mai slab punct — cauza reală s-a dovedit conversia de coordonate de mai sus,
șase linii. Argumentul rămâne valid doar pe accesibilitate (fiecare județ = element DOM real).
De tratat ca proiect separat, nu ca reparație.

**`b3bbf6d9` — the `@claude` workflow now checks WHO wrote the text, not just that it says
`@claude` (`IZZ-0189`).** `.github/workflows/claude.yml` runs with `contents: write` and the
owner's subscription token; its `if:` was a pure substring match, so on a public repo any
account could have made an issue body the prompt for a job that can commit to `main`.
**It was not exploitable** — read at the pinned SHA `be7b93b1`: `run.ts:190` calls
`checkWritePermissions()` before the trigger check and throws, and `checkHumanActor()` runs in
both tag and agent modes. **But do not restate that as "one check protects us":**
`checkWritePermissions()` returns `true` unconditionally for any actor ending in `[bot]`, with
no API lookup, so bots are stopped by `checkHumanActor()` alone — two functions in third-party
pinned code, invisible in our diff. The gate now also requires `author_association` ∈
{`OWNER`,`COLLABORATOR`}. **Measured on real payloads:** `Ramanul`→`OWNER` 94/94,
`dependabot[bot]`→`CONTRIBUTOR`, every other bot→`NONE`. `MEMBER` is excluded on purpose (repo
is User-owned; under an org it would admit members without write access here). Of 622 historical
runs, 601 were already skipped here; of the 21 that executed, 10 were the owner and 11 were
bot-triggered but never reached the agent (their step exited 0, while `checkHumanActor()` would
have called `core.setFailed()`). **Net loss of function: zero**, except `issues: assigned` on
someone else's issue — comment instead. `tests/test_workflow_claude_gate.py` (43 tests) mirrors
the expression out of the YAML rather than restating it; verified by mutation (guard removed →
7 fail, allowlist widened with `CONTRIBUTOR` → 4 fail). Suite **872 passed, 8 xfailed**.
**Verified locally, not yet on live** — no `@claude` event has fired against the new file.
**Residual risk this does NOT close, named so nobody reads it as closed:** the owner himself
inviting the agent onto untrusted content (e.g. `@claude apply your fixes` on a stranger's fork
PR) still feeds attacker-written text to a job with `contents: write`. That is inherent to the
tool, documented in the action's own `docs/security.md`, and needs a design decision, not a flag.

**`e6988406` — third-party comments no longer reach the `@claude` prompt (`IZZ-0191`).** The gate
above stops a stranger *starting* the agent; it does nothing about the owner starting it **on top
of** hostile content (`@claude apply your fixes` on someone else's fork PR). Uses the mitigation
the action's own `docs/security.md` names for this — `include_comments_by_actor`, set to the owner
plus `claude[bot]` so threads keep continuity. Verified in the pinned source that it filters only
the comment history (`fetcher.ts filterCommentsByActor`); the triggering comment takes a separate
path, so invoking still works. **Do not read this as closed:** PR title, body and diff still reach
the model — sanitized (hidden HTML, invisible chars, image alt text) but present, and no input
filters them. **The structural backstop is branch protection on `main`, which is unset** and would
need a bypass actor for the ~2h content bot — owner decision, not a workflow edit.
`claude-code-review.yml` untouched on purpose (`contents: read`, read-only tools, reading the diff
is its job).

**`41428e6e` — `visual-live` was red for a dead selector, not a defect (`IZZ-0192`).** Red on every
run from 2026-08-13T03:05 to today. `renderList()` stopped emitting `.news-item` on 2026-08-12
(`80b79b6a`) and now builds bare `<li><a>`; the guard still waited for `#news-list .news-item`.
**Reproduced locally against `izz-ro.pages.dev` before touching anything:** `map.json` 200 (348KB),
0 console errors, 0 failed requests, canvas present — only the list selector never matched. The
site was fine throughout. Now asserts `#news-list li a` and prints the count. **Third instance of
this pattern here** (see the 8 map tests below), so the reasoning is written into the file: assert
on an id from `index.html` plus an HTML tag, never on a CSS class. Verified live, desktop + mobile:
all green, "lista are articole (120)".

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
(157→177px). Suite **829 passed, 8 xfailed**. **Confirmed on live**: CSP header carries
`*.clarity.ms`, live run uploads to `k.clarity.ms` while the local run used `n.` — both hosts
occur in the wild, so the wildcard was load-bearing, not caution.

**`8c5464b9` — analytics only report from production hosts** (`IZZ-0187`). Neither GA4 nor Clarity
distinguishes izz.ro from a local copy: the same tag on `http.server` sent **real sessions into the
production accounts** (measured — localhost:8766 test sessions landed in the Clarity panel).
`HOSTURI_PRODUCTIE = ['izz.ro','www.izz.ro']`, allowlist not blocklist. **Moving the site to a new
domain means adding it there, or analytics goes silent.** Verified: consent accepted on
localhost → `clarity`/`gtag` undefined, 0 external requests, personalization still working.

**Noticed, not fixed (N4, pre-existing, out of this slice's scope):** Cloudflare injects its own
inline script (`__CF$cv$params`) into every HTML response, and the site's own CSP — which has no
`'unsafe-inline'` — blocks it on every page load. Verified it is not Clarity's doing: the console
error appears with Clarity absent, and the hash differs per request because the injected script
carries a per-request id. Cloudflare Web Analytics still works through the explicit
`beacon.min.js` tag in `base.html`, which CSP allows.

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
and topic mix is measured by nothing.
**CORRECTED 2026-08-16 — the line that used to end this paragraph said "Cadence is next". It was
already false the day it was written, and it cost a slice today before `securitate-ingestie.md`
§5.1 and `registru.tsv` caught it.** The cadence axis was measured **the same day** (2026-08-12)
and is **dead on the data we have**: `IZZ-0174`, status `masurat-fals`. Four reasons, in the order
the hypotheses fell: (a) **regular intervals** — Rovinari ranks **17th of 21**, i.e. *more*
irregular than legitimate town halls (cv 1.67 vs median 1.36), because the warez is interleaved
with real notices, so the *combined* stream is not regular; the 3-hour spacing exists only inside
the warez subset, which cannot be isolated without already knowing which items are warez —
circular; (b) **sustained throughput** — Rovinari is 1/70 at 9 items, but #2-#3 are legitimate town
halls at 8, so a threshold of 9 is a curve through n=1, and at 6 it flags 5 sources of which 4 are
legitimate; (c) **confound** — `config.MAX_PER_SOURCE = 8` caps items per fetch, so observed
throughput measures **our fetch schedule**, not the source; (d) **decisive** — Cajvana has
max24h = **1**, so a single-article defacement is invisible to any cadence measure by construction,
which is exactly the case layer 8 exists for. **Do not reopen without a NEW signal.** What was
built instead, because the data supported it, is layer 9 (source quarantine, §R6a) — already shipped.
The open axis is **topic mix**, not cadence.

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

**A1. REVERTED 2026-08-15 (`c6397735`) — DO NOT RE-LAND WITHOUT A SCROLL GUARD.**
Both hit-test slices (`bf55ae9f`, `ab4dd8b8`) went live and the owner reported on device that
**the map started smearing into stacked copies again** — the A2 symptom, fixed on 2026-08-12 and
confirmed on his phone then. `ensureCanvas` is intact, so the *original* cause did not return.
But our two commits were the only code to touch `static/harta-stiri/*.js` since (bot commits
only touch `data/map.json`), and live had them.
**CAUSATION CONFIRMED by the revert** (owner re-checked on device after `c6397735` reached live:
smearing gone). One variable changed, symptom followed it both ways — so this is no longer a
hypothesis about which commits are responsible. What remains unproven is the *mechanism* below;
the responsibility of the hit-test enlargement is established.
**Mechanism, plausible but still unobserved:** the enlarged hit areas (22px bubbles, 10px base
tolerance, small-county priority) mean a stray touch during a scroll, which used to hit nothing,
now selects a county → `applyState` → `buildMap()` recomputes `canvas.style.height` from the new
view's aspect (`cssWidth * view.height / view.width`), so the canvas **changes height mid-scroll**.
The 10px tap-vs-drag guard does not cover it: the finger need not move past the threshold.
**Reverted rather than patched because the artefact cannot be reproduced here** — it does not
appear headless or under emulated scroll; the 2026-08-12 diagnosis needed a phone screen
recording and OpenCV frame extraction. Shipping a targeted fix we cannot watch fail would be
exactly the §16 violation of reporting "fixed" without observing the symptom disappear.
**Before retrying, in this order:** (1) suppress re-selection while a scroll is in flight,
(2) keep the canvas height stable across zoom so no reflow happens mid-gesture, (3) only then
re-land the hit-test work, and (4) get owner confirmation **on device** — not from a desk test.
The measurements are not lost: the sweep, the per-county usable-area numbers, and the two
test-harness traps are in the Landed section above and in the two reverted commits.
**What DID survive and is live: the county picker now meets the 44px target** (`min-height`,
was 36px). That is pure CSS on DOM buttons below the map, cannot touch the canvas, and it
already serves A1's actual need — București is untappable on the canvas at 8.6px, but has a
real 123×44px button there. For a genuine 44px target *on the map*, the standard cartographic
answer is an inset box beside it (Datawrapper & co. for DC, Bremen, Hamburg) — owner's call.
Original measurement kept below.
~~Tap targets too small — real, separate from A2, NOT the "mari probleme" bug.~~
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

0b. **RESOLVED 2026-08-15 (`8fb9c148`) — slice 1 only; see the Landed section above. Slices 2-3
   (review queue, approval log) remain unbuilt, owner's call.** Kept below because the mechanism
   must not be reintroduced, and because the legal reasoning is still the reason it exists.
   ~~`hold_important` is a promise the code does not keep — and it is now load-bearing for AI Act
   art. 50.~~ `moderation.yaml` documents it as "true = clusterele C/importante așteaptă aprobare
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
2. **CORRECTED 2026-08-15 (`0f9fe2d3`) — the formula below was DEGRESSIVE BUT WRONG: it used
   `floor` where art. 77 alin. (4) opens each band at +1 leu, so it over-credited 49 of every 50
   salaries. See the Landed section above. Also: the SHA cited here, `5dc92ca7`, is an ORPHAN
   commit and is not on `main`; the real one is `2d0df92f`.** Original note kept below.
   ~~LANDED 2026-08-13 (`5dc92ca7`) — deducere personală is now degressive, per art. 77
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
   clarifica.~~
3. **Model C is not batched** — `process_cluster` is one AI call per cluster while B batches 10.
   Gate is already instrumented: read `stats["deferred"]` over 2–3 real runs before building it.
   Do not re-litigate the threshold (`build.yml` overrides the budget to 18, not the default 12).
   **UNBLOCKED 2026-08-16 — owner installed and authenticated `gh` (2.97.0). The logs were read,
   and the gate itself turned out to be wrong (`b6d856b7`).** Six real builds:

       run             fara substanta   deferred   budget used
       31920738670           27            27         11/18
       31915086605           28            28         15/18
       31909820457           29           107         18/18
       31898707192           30           254         18/18

   In the two runs where the budget was **not** exhausted, `deferred` equalled the
   substance-reject count **exactly** — 27 of 27, 28 of 28. Real budget pressure: **zero**,
   reported as "buget AI epuizat". The counter was adding two opposite quantities: items left out
   because the budget ran out (they come back and get processed) and items rejected for lacking
   substance (rejected before clustering and before the budget, so they come back and are rejected
   again, forever). Fixed: the substance rejects are counted and reported separately, and the
   message now *derives* the cause from the numbers instead of asserting it.
   **True budget pressure, after the fix: 0, 0, 78, 224.** It is real but smaller than it looked.
   **The batching decision is still NOT taken** — it needs 2-3 runs with the corrected number, per
   this item's own rule. Do not decide it off the pre-fix figures.
   **First two clean readings (2026-08-16). They DISAGREE, so the third one decides:**

       run           fetched  new   B   C   ai_calls  deferred  substanta
       31927569381     386     68  44   5    10/18       0          19
       31932736726    1387    152  11  17    18/18      84          24

   `31927569381` closes arithmetically both ways — 5 C calls + ceil(44/10) B batches = 10 =
   `ai_calls`; 19 + 44 + 5 = 68 = `new`. Zero budget pressure. **At `deferred: 0` NO line is
   printed** (`if stats.get("deferred")` is falsy at 0) — read the absence as 0, do not mistake it
   for a pre-fix build.
   `31932736726` names the lever exactly: **17 C clusters × 1 call = 17 of the 18**, C processed
   first (`main.py:155`; the 12-article sample is 12/12 C), so a single B batch of 10 ran and 84
   items slipped to the next run. Batching C at 3 clusters/call takes 17 → 6 and zeroes the
   deferral on this run's numbers.
   **What reading 3 must settle: chronic or episodic.** The two runs differ 3.6× in `fetched`
   (386 vs 1387) and the pressure appeared only in the big one, so it may be a catch-up spike
   rather than the steady state.
   **Blocked by §10 regardless of the numbers:** Model C synthesis logic is do-not-touch without
   explicit owner instruction. The measurement can be finished autonomously; the change cannot be
   started.
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
