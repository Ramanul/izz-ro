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
> Garda `incalcari_pr_fantoma` in `tests/test_pr_fantoma.py` pica daca `## Open` numeste un PR
> care are deja commit de merge pe main (fara adnotarea `(merged)`).

**Updated:** 2026-09-02 (#248 pe main: main-ul reparat, CI 29m39s -> 15m32s, Siria-tara != Siria-comuna)

## Open

- **F4 (#241, merged)**: §18 in L1. Urmatorii: §12, §14, §20; **§17 NU**.
- **K12 (`IZZ-0255`)**: rezumat zilnic, spec nescris; porneste de la `editorial-quality.yml`.
- **Axa 3** — spec `specs/anomalie-linkuri.md` (`IZZ-0259`), NEimplementat deliberat (R3).
- **Arhiva (#198)** — `IZZ-0260`/`IZZ-0261`: blocata pe decizia de arhitectura + `izz-failover`.
- **Trafic** — sonda `trafic.yml` scrisa; de citit daca tokenul CLOUDFLARE are scope analytics.
- **Home fresh 72h — PR #247** (`fix/home-fresh-72h-v2`): helper + wiring + 6 teste.
  DEBLOCAT de #248; CI-ul lui trece dupa ce aduce main in ramura.
- **PR-uri deschise:** #247 (prospetime 72h), #250 (plasa de echivalenta). Owner: #207 #214 #235.
  (#248 merged; #244 merged; #225/#240 closed. Fiecare PR cere propria adnotare — intr-o
  lista `#A/#B merged` garda o vede doar pe ultima.)
- **CI paralelizat (#248)**: 29m39s -> 15m32s. Numele jobului `pytest` NU se schimba.
  `ramanul-triage-blockers` (e1c8fbe2) e vie si arunca tacut articole legitime (`IZZ-0266`).
- **PLASA pentru restructurare (#250, `IZZ-0271`)**: `tools/echivalenta.py` amprenteaza
  `output/`, deci o refactorizare se poate DOVEDI neutra fara sa citesti 8.515 linii.
  NEVERIFICAT, in ordinea asta: (1) determinismul intre DOUA randari, 2x10 min; (2) coverage
  — `pip install pytest-cov && pytest --cov=generator`. Cuplarea reala NU e prin importuri:
  16 chei fac punte in `articles.json`, `title` e scris de 2 module si citit de 12.
- **Din `specs/atribuire-cercetare-si-plan.md`** — E1 + E4 cer decizia proprietarului.

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
  place-on-badge 31/32 (97%). **Cifra aia NU mai e comparabila** (`IZZ-0268`, masurat 2026-09-02):
  TTL-ul a expirat 44 din cele 51 de randuri ale setului de aur, deci o rulare de azi masoara 7
  articole si da 86% — alt esantion, nu alt rezultat. Unealta cere set de aur reimprospatat.
  Covers are never redrawn on a first run (`IZZ-0163`, owner refused
  2026-08-06); `FORCE_REGEN=1` is the opt-in.

## Where the rest lives

`specs/istoric-executie.md` · `specs/registru.tsv` + `python tools/registru.py find` ·
`specs/masuratori-frontend.md` · `specs/istoric-operational.md` · `../HANDOFF.md`.
