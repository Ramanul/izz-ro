# STATE — project execution state

> Single source of truth for "where we are". Manager-owned; updated at the end of every slice.
> Executors get it read-only. **Hard cap: ~40 lines of content.** When it grows past that, cut
> the settled history into `specs/istoric-executie.md` — do not let it accumulate here. It is
> read at the start of every session, so every stale line is paid for twice: in tokens, and in
> an executor re-implementing something that already shipped. `git fetch` immediately before
> rewriting it.
>
> **Cut on 2026-08-21** from 656 lines, the second time. What it cost, stated so nobody repeats
> it: two sections were headed `Open PR` while both PRs were already **merged** (#196 on 08-20,
> #197 on 08-21), and the 195-line `## Open` section was almost entirely SHIPPED/FIXED/REVERTED
> history with two live rules buried in it. That is the same failure the 08-07 cut documented.
> **A section is `Open` only if a PR is open or a decision is pending — check, don't assume.**

**Updated:** 2026-08-30 (F1+F2+F3 aterizate pe `main` — #226 #227 #228; F4 replanificat pe hook
`PostToolUse` si predat contului A)

## Open

- **F4 — stratul L1 e hook `PostToolUse`, nu agenti** (`IZZ-0252` masurat-fals, `IZZ-0254` e
  inlocuitorul; plan replanificat in `specs/regim-reguli.md`). F1/F2/F3 sunt pe `main`; F4 e
  predat contului A prin `handoff/to-A/2026-08-29-izz-f4-hook-postooluse.md`, fiindca B n-are
  hook-uri. `CLAUDE.md` e la 24.532 din 24.576 octeti: nicio regula noua nu incape fara F4.
- **K12, decizie proprietar** — `REVIEW.md` descrie un regim incheiat: se actualizeaza la cel de
  azi, sau se marcheaza istoric si `README.md` trimite altundeva? (K5 si K11 rezolvate in #228.)
- **PR-uri deschise:** #203 #204 #207 #214, doar documente. **#225 nu poate ateriza asa cum e**,
  doua blocaje masurate azi: cele cinci randuri de registru refolosesc `IZZ-0250`..`IZZ-0254`,
  luate deja pe `main` de alt continut; si redenumeste o regula din censul F3
  (`tests/test_reguli.py`, 'Nu confunda unealta cu capacitatea'). Ambele in acelasi commit.
- **Arhiva paginilor expirate (issue #198, deschis de proprietar 08-21)** — diagnostic complet
  acolo (193 pagini moarte in Search Console); cere alegerea proprietarului intre 3 optiuni.
  R2: bucket `izz-bucket` exista, gol, neconectat in cod (`IZZ-0250`), plafonul gratuit acopera
  arhiva. Obstacol real: `izz-ro` ruleaza assets-only, deci R2 nu se poate citi la runtime fara
  cod nou; hookul natural e `izz-failover`, care azi trateaza orice 404 ca 404 final.
- **Din `specs/atribuire-cercetare-si-plan.md`** — E1 permalink decuplat (decizie proprietar),
  E3 focus score, E4 axe separate (decizie proprietar), E5 gold set ~150 + poarta CI.

## Standing rules that keep being rediscovered — do not "fix" these

- **`state.merge()` is dead code, NOT a live bug.** `state.py:95`; the only caller is
  `tests/test_state.py:14`. Dedup between fresh items happens inline at `main.py:227-236` (#158).
  The recurring "lying function" hunt keeps rereading it as a duplicate bug; touching it is an
  opportunistic refactor (§5.6).
- **Map: do not re-land the enlarged hit areas without a scroll guard.** Reverted 2026-08-15
  (`c6397735`), causation confirmed on device by the owner. Before retrying: suppress
  re-selection while a scroll is in flight. Full mechanism in the archive.
- **Attribution: `specs/atribuire-cercetare-si-plan.md` is the dossier — do not re-research it.**
  7 external systems, 8 causes, a 6-stage plan, paid for once. Run `tools/eval_atribuire.py`
  before and after **any** change to `geo.py`. Baseline 2026-08-08: category 25/39 (64%),
  place-on-badge 31/32 (97%). Covers are never redrawn on a first run (`IZZ-0163`, owner refused
  2026-08-06); `FORCE_REGEN=1` is the opt-in.

## Where the rest lives

`specs/istoric-executie.md` (everything cut from here, verbatim — measurements, killed
hypotheses, the bot-challenge diagnosis, owner answers) · `specs/registru.tsv` +
`python tools/registru.py find` (decisions, incl. what was rejected and why) ·
`specs/masuratori-frontend.md` (Lighthouse/CLS) · `specs/istoric-operational.md` (cadence,
delegation, autonomy history) · `../HANDOFF.md` (the cross-account state, ~30 lines).
