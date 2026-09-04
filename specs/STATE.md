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

**Updated:** 2026-09-03 (#252 merged: dim. 4 + dim. 7 pe main; CI verde, garzile trec)

## Open

- **F4 (#241, merged)**: §18 in L1. Urmatorii: §12, §14, §20; **§17 NU**.
- **K12 (`IZZ-0255`)**: rezumat zilnic, spec nescris; porneste de la `editorial-quality.yml`.
- **PR-uri deschise:** #247 prospetime 72h (`fix/home-fresh-72h-v2`, helper+wiring+6 teste,
  DEBLOCAT de #248 — CI-ul trece dupa ce aduce main in ramura). Owner: #207 #214 #235.
  (#278 merged; #253 merged; #252 merged; #250 merged; #248 merged; #244 merged; #225/#240 closed. Fiecare
  cere adnotarea lui, pe aceeasi linie — intr-o lista `#A/#B merged` garda o vede doar pe ultima.)
- **CI paralelizat (#248)**: numele jobului `pytest` NU se schimba. `ramanul-triage-blockers`
  (e1c8fbe2) e vie si arunca tacut articole legitime (`IZZ-0266`). Debitul e limitat de
  PLANIFICATORUL GitHub — 4,7 porniri/zi, nu 12 (`IZZ-0292`); sect. 17 ramane valabila.
- **PLASA pentru restructurare (`IZZ-0271`)**: `tools/echivalenta.py` amprenteaza `output/`;
  `tools/mutanti.py --regresie` (~10 s) — inainte de orice refactor pe cluster/select/geo/util/
  guard. Coverage 71%, mutanti ucisi 81%, `render.py` cel mai rau pe AMBELE axe (`IZZ-0280`/
  `IZZ-0281`). NEVERIFICAT: determinismul intre DOUA randari (2x10 min). Cuplarea reala nu e
  prin importuri — dosar `specs/arhitectura-cuplare.md`, NU re-cerceta.
- **Nefolosit (`tools/nefolosit.py`, dosar sect. 4f)**: `agents.py` STERS (`IZZ-0289`). Decizii
  proprietar: `process_cluster` §10 (`IZZ-0294`), 272 KB orfane masurate dar necuratate
  (`IZZ-0301`), §12 (`IZZ-0295`), F4 (`IZZ-0296`), Axa 3 (`IZZ-0297`), arhiva (`IZZ-0298`).
- **Garda anti-amanare (`tests/test_registru_amanari.py`, `IZZ-0293`)**: un rand `propus` cu
  `decident` = agent expira in 14 zile. Iesiri: fa-l, treci-l pe om, inchide-l cu motiv (un rand
  nou care il leaga il inchide). La scriere: 12 amanari catre mine -> 0.
- **Din `specs/atribuire-cercetare-si-plan.md`** — E1 + E4 cer decizia proprietarului.

## Standing rules that keep being rediscovered — do not "fix" these

- **`state.merge()` is dead code, NOT a live bug.** `state.py:143`; the only caller is
  `tests/test_state.py:14`. Dedup between fresh items happens inline at `main.py:227-236` (#158).
  The recurring "lying function" hunt keeps rereading it as a duplicate bug; touching it is an
  opportunistic refactor (§5.6).
- **Map: do not re-land the enlarged hit areas without a scroll guard.** Reverted 2026-08-15
  (`c6397735`), causation confirmed on device by the owner. Before retrying: suppress
  re-selection while a scroll is in flight. Full mechanism in the archive.
- **Attribution: `specs/atribuire-cercetare-si-plan.md` is the dossier — do not re-research it.**
  7 external systems, 8 causes, a 6-stage plan, paid for once. Run `tools/eval_atribuire.py`
  before and after **any** change to `geo.py`. Baseline 2026-08-08: category 25/39 (64%),
  place-on-badge 31/32 (97%). **Cifra aia NU mai e comparabila** (`IZZ-0268`): TTL-ul a expirat 44
  din cele 51 de randuri, deci o rulare de azi masoara 7 articole — alt esantion, nu alt rezultat.
  Covers are never redrawn on a first run (`IZZ-0163`, owner refused 08-06); `FORCE_REGEN=1` opts in.

## Where the rest lives

`specs/istoric-executie.md` · `specs/registru.tsv` + `python tools/registru.py find` ·
`specs/masuratori-frontend.md` · `specs/istoric-operational.md` · `../HANDOFF.md`.
