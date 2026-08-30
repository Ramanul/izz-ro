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
> Asta nu mai e doar scris: `tests/test_reguli.py` pica daca `## Open` numeste un PR care are deja
> commit de merge pe `main`. Un PR integrat poate aparea aici doar adnotat `#NNN (merged)`.
>
> **Nu se atinge in PR-uri de functionalitate** (regula adusa din #230). Se actualizeaza pe `main`,
> dupa merge. Motivul e masurat (2026-08-30): dintre PR-urile deschise, cele blocate erau blocate
> EXCLUSIV de conflicte pe fisierul asta — la #207, 7 linii din 594 — in timp ce #232 si #234, care
> nu-l ating, au ramas curate. Un fisier pe care fiecare sesiune il rescrie n-are ce cauta intr-o
> ramura de functionalitate.

**Updated:** 2026-08-30 (coada de PR-uri triata: #232 si #234 verzi, #231 fantoma, #230 absorbit)

## Open

- **Coada de PR-uri, verificata pe GitHub azi:** deschise **#207 #214 #225 #230 #231 #232 #234**.
  Verzi si gata de merge: **#232** (mecanismul K12 + pasul 1 al axei 3 + interogarea de trafic
  agregata) si **#234** (agentii portati pe Codex) — niciunul nu atinge STATE.md, de-aia sunt
  curate. **#231 e fantoma:** F4 a aterizat prin #229 (merged), ramura e cu 29 de commit-uri in
  urma si un merge al ei ar sterge 8.265 de linii. **#230 e absorbit** de PR-ul acestei sesiuni.
- **F4: pilotul (§13) a aterizat prin #229 (merged).** `CLAUDE.md` la 23.835 octeti, 741 liberi.
  Urmatorii candidati masurati: §12 (2.259 o.), §14 (1.795), §18 (1.489), §17 (1.084), §20 (1.024).
- **Arhiva (#198)** — `IZZ-0260`: decide NUMARUL de fisiere, nu marimea starii. 3,23 fisiere/
  articol, deci optiunile 2 si 3 mor in 7-24 de zile pe plafonul de 100.000 assets; R2 e singura
  care scapa. **Blocat pe #214**, care da ruta catre `izz-failover`.
- **#225 blocat pe decizii de proprietar:** cinci ID-uri de registru refolosite si o regula
  redenumita din censul F3. Ramura e cu 52 de commit-uri in urma.
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
