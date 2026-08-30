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

**Updated:** 2026-08-30 (#226 + #227 + #228 fuzionate; F4 pilotat pe hook `PostToolUse`)

## Open

- **Regimul regulilor** (`specs/regim-reguli.md`) — F1/F2/F3/F3.5 **aterizate** (#226, #227,
  #228). F4 e **pilotat pe o singura sectiune**: §13 mutata in `.claude/reguli/13-frontend.md`,
  livrata de hook-ul `PostToolUse` (`.claude/hooks/reguli-l1.sh`). Ce ramane: restul candidatilor
  (§12a 1.743 o., §18 1.489, §17 1.084, §20 1.024) se muta doar dupa ce pilotul se dovedeste in
  uz real, nu doar in teste.
- **Doar documente, ramase:** #203 #204 (fiecare adauga un fisier NOU, doar `registru.tsv` intra
  in conflict — rebase si ateriza), #207, #214 (infra: rute + probe, are valoare reala).
  #202/#206/#218 **inchise 2026-08-29** cu motivul scris: complet inlocuite.
- **Arhiva paginilor expirate (issue #198)** — decizie de ARHITECTURA a proprietarului, intre 3
  optiuni. Diagnosticul (193 pagini moarte) e in issue; R2 e investigat in `IZZ-0250`. Obstacolul
  real, ca sa nu se re-descopere: `izz-ro` ruleaza assets-only, deci R2 nu se poate citi la
  runtime fara cod nou, iar hook-ul natural (`infra/failover-worker.js`) trateaza orice 404 ca final.
- **Din `specs/atribuire-cercetare-si-plan.md`** — E1 permalink decuplat (decizie proprietar),
  E3 focus score, E4 axe separate (decizie proprietar), E5 gold set ~150 + poarta CI.
- **Suita de teste: 626 din 647 s sunt setup-ul unei singure fixturi** (`output_randat`, care
  randeaza tot site-ul). Analiza, cele doua fundaturi si criteriile: `specs/randare-in-teste.md`.
  Nu re-masura.
- Cifre: randare 638 s / 34.898 fisiere, ~80.145 fisiere sub bugetul de 90.000,
  **CLAUDE.md 23.711/24.576 dupa F4** → `specs/istoric-executie.md`.

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
