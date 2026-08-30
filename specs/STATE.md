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
>
> **Nu se atinge in PR-uri de functionalitate.** Se actualizeaza pe `main`, dupa merge. Motivul e
> masurat (2026-08-30): din 10 PR-uri deschise, 5 erau blocate EXCLUSIV de conflicte pe fisierul
> asta — la #207, 7 linii din 594, adica 1%. Un fisier pe care fiecare sesiune il rescrie nu are
> ce cauta intr-o ramura de functionalitate.

**Updated:** 2026-08-30 (F1/F2/F3 aterizate; garda de PR fantoma; STATE.md scos din
ramurile de functionalitate — vezi antetul)

## Open

- **Regimul regulilor** — F1/F2/F3 aterizate (#226 (merged), #227 (merged)). Ramane **F4, plan
  nou**: F3.5 i-a picat premisa (IZZ-0252 → IZZ-0253). `CLAUDE.md` e la 24.532/24.576 — 44 liberi.
- **#225 blocat, trei decizii ale proprietarului:** +107 octeti peste plafon · sterge regula «Nu
  confunda unealta cu capacitatea.» (prinsa de cens) · IZZ-0250..0253 se ciocnesc, vor 0255+.
- **Doar documente:** #202 #206 #207 #214 #218 — toate conflictuale doar pe `specs/STATE.md`.
  #206 nu merita asa: 19/21 linii sunt STATE.md, iar titlul („main cannot deploy") e infirmat.
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
- Cifre (randare, ritm, regimul de ~80.145 fisiere sub 90.000) → `specs/istoric-executie.md`.

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
