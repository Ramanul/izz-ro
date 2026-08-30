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

**Updated:** 2026-08-29 (F2 = garzile de fapte canonice; F3.5 a picat premisa lui F4;
R2 investigat pentru arhiva — vezi mai jos)

## Open

- **Regimul regulilor** (`specs/regim-reguli.md`, doar pe #226) — F1 = **#226** (verde, asteapta
  merge). F2+F3 (garzi de fapte canonice + censul celor 47 de reguli cu nume) = **#227**, verde.
  F3.5 a picat premisa lui F4 (IZZ-0252); inlocuitorul e IZZ-0253, iar F4 vrea plan nou.
- **Doar documente** (conflictul din registru rezolvat de #222, nemaiverificate individual azi):
  #202 #203 #204 #206 #207 #214 #218.
- **Archiva paginilor expirate (issue #198, deschis de proprietar 08-21)** — diagnostic complet
  deja facut acolo (193 pagini moarte in Search Console). Necesita alegerea proprietarului intre
  3 optiuni; R2 investigat azi (IZZ-0250/0251-adiacent): bucket `izz-bucket` exista deja pe cont
  (creat intentionat de proprietar la trecerea pe Cloudflare Paid), gol, neconectat in cod.
  Plafon gratuit 10GB/1M scrieri/10M citiri/luna — suficient pentru arhiva. Obstacol real:
  `izz-ro` ruleaza assets-only (fara `main`), deci R2 nu poate fi citit la runtime fara cod nou;
  hook-ul natural e `izz-failover` (infra/failover-worker.js), care azi trateaza orice 404 ca
  404 final. Ramane decizie de arhitectura, nu implementare mecanica.
- **Din `specs/atribuire-cercetare-si-plan.md`** — E1 permalink decuplat (decizie proprietar),
  E3 focus score, E4 axe separate (decizie proprietar), E5 gold set ~150 + poarta CI.
- Cifrele masurate azi (randare 638 s / 34.898 fisiere, 822 articole/zi, regim stabilizat
  ~80.145 fisiere sub bugetul de 90.000, CLAUDE.md 23.920/24.576) → `specs/istoric-executie.md`.

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
