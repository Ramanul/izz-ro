# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-09-13 (backlog de PRODUS, prima oară — 75% din commit-uri nu atingeau site-ul)

## Open

- **Pages `izz-ro` e un ZOMBI care revendică `izz.ro` [IZZ-0366, IZZ-0368].** Are atașate
  `izz-ro.pages.dev` **și `izz.ro`**; ultim build reușit 21 aug, apoi 17 eșecuri (#211 merged).
  DNS apex+www → Pages, dar rutele Worker au precedență. 2 sisteme cred că dețin apexul. §10.
- **PRODUS P1 — homepage-ul n-are NICIO fotografie [IZZ-0382].** Măsurat 13 sep pe build-ul local:
  0 `<img>` pe homepage; „imaginile" sunt blocuri HTML/CSS generate. Dar **56 din ultimele 76 de
  articole (73%) au entitate cu portret REAL** deja în `output/portraits/` — deci zero fișiere noi
  și zero cost de plafon. Cardurile nu fac potrivirea; doar paginile de articol o fac (`render.py:971`).
- **PRODUS P2 — coperțile generate arată amatoricesc [IZZ-0383].** Verdict proprietar: „desene de
  copii mici". Un dreptunghi cu rubrica + data, fără legătură cu subiectul. `htmlart`/`covers.py`.
- **PRODUS P3 — harta: markere fără ierarhie vizuală [IZZ-0384].** 482 evenimente, dar un marker de
  66 și unul de 1 arată aproape identic. Clickurile SUNT cablate (29 `addEventListener`) — problema
  e afordanța, nu funcția. Datele afișau „actualizat 11 sept" pe un build din 13 sep.
- **REDUNDANȚA — REPARAT [IZZ-0370 → IZZ-0372].** Rămâne de curățat: manifestul mirror-ului
  poartă `GITHUB_SHA`, nu content-sha — o linie `BUILD_COMMIT_SHA` în jobul `mirror`, blocată de
  hook (capacitate), NU de §10, care nu acoperă workflow-uri [IZZ-0373].
- **PR queue — 4 deschise:** #336 registru IZZ-0313 · #320 Lee · #297 Cronica vie · #280 CSS.
  Ieșite: #337 merged, #333 merged, #331 merged, #330 merged, #329 merged; #324 și #321
  închise nemergeuite.

## Audit closure status

- **K1–K14:** re-verified in `specs/regim-reguli.md` — a reconciliation register, not a substitute
  for passing tests. **Grounding:** blocks invented quotes and foreign numbers, fails closed.
- **Coordination:** live channel is `handoff/` + `specs/STATE.md`. **Containment:** destructive git
  commands and direct Edit/Write on control-plane files are denied; fd-only redirects no longer
  count [IZZ-0353]. **Journals:** takedowns removed on every publish path; ingest discards logged.
- **Near-verbatim copy:** >=15-word runs and transcribed titles block the gate. Open: calibration
  corpus, 2x determinism run. **Silence detection:** hourly. **Human gate:** `IZZ_REQUIRE_HUMAN_GATE`.
  **Main** is `protected: true`; required-checks list unreadable here (403), rulesets: none.
- **Unified audit is mechanical now:** `specs/audit-unificat.tsv` + `tools/audit_matrice.py`
  (+ `eroziune`) + `tools/cadenta_reala.py` + tests; findings in `specs/audit-unificat.md` §5.
  Content commits pushed with the default `GITHUB_TOKEN` trigger NO workflow, so state regressions
  surface only via a PR — owner call. [IZZ-0351…0357, 0363…0367]

## Standing rules

- Cadence is the GitHub scheduler, not the 105-min gate: 25% firing, ~6 starts/day, median ~4h.
  Re-measure with `tools/cadenta_reala.py`; do not quote the number from memory. [IZZ-0364]
- Do not treat retired static-host origins as live origins; Worker origin is the fallback path.
- Do not use old task journals as normative coordination channels.
- Every measurement gets its window and its command, or it is not a measurement [IZZ-0367].
- Do not mark live, GitHub settings, or Cloudflare facts as solved based only on repository code.
