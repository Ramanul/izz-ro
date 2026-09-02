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

**Updated:** 2026-09-02 (#241: bugetul de pornire sub garda, §18 in L1, `IZZ-0265`)

## Open

- **F4 CONTINUAT (#241, draft).** §18 e a doua regula in L1, verificata prin rulare. Plafonul
  s-a mutat de pe FISIER pe SUPRAFATA de pornire (`CLAUDE.md` + hook + frontmatter agenti si
  comenzi): o mutare intre straturi NU economiseste — toate intra in aceeasi sesiune. Buget
  36.278 -> 34.936 o., plafon 37 KB, garda acopera 100% (era 78%). Urmatorii: §12 (2.259 o.),
  §14 (1.795), §20 (1.024); **§17 NU** — fara declansator pe cale s-ar dizolva. `IZZ-0265`.
- **K12 decis (`IZZ-0255`)**: rutina nu se rescrie, se construieste mecanismul (rezumat zilnic
  „ce e nou, ce e riscant"). **Specul nu e scris**; porneste de la `editorial-quality.yml`.
- **Axa 3 a garzii de anomalie** — spec in `specs/anomalie-linkuri.md` (`IZZ-0259`), NEimplementat
  deliberat: R3 cere praguri masurate, iar corpusul de gazde-destinatie nu exista. Pasul 1 e un
  job pe runner. Cauza mecanica: `clean_html()` scoate `href`-urile inainte de `guard.verdict()`.
- **Arhiva (#198)** — `IZZ-0260`: decide NUMARUL de fisiere, nu marimea starii. 3,23 fisiere/
  articol, deci optiunile 2 si 3 mor in 7-24 de zile pe plafonul de 100.000 assets; R2 e singura
  care scapa. **Blocat pe #214**, care da ruta catre `izz-failover`.
- **Trafic** — sonda `.github/workflows/trafic.yml` scrisa; rulabila abia dupa aterizarea lui
  #229. Raspunde masurat daca tokenul CLOUDFLARE existent are scope de analytics.
- **PR-uri deschise:** #203 #204 #207 #214 **#241**. **#225** are doua blocaje: cinci ID-uri refolosite
  si o regula redenumita din censul F3.
- **Din `specs/atribuire-cercetare-si-plan.md`** — E1 + E4 cer decizia proprietarului, E3 focus
  score, E5 gold set ~150 + poarta CI.

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
