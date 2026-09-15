# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-09-14 (recidivele CI: roșul de stare separat de cel de cod — PR #347 draft)

## Open

- **Pages `izz-ro` e un ZOMBI care revendică `izz.ro` [IZZ-0366, IZZ-0368].** Are atașate
  `izz-ro.pages.dev` **și `izz.ro`**; ultim build reușit 21 aug, apoi 17 eșecuri (#211 merged).
  DNS apex+www → Pages, dar rutele Worker au precedență. 2 sisteme cred că dețin apexul. §10.
- **Free-readiness — host is STILL PAID (100.000) until 22 Sep; 20.000 is a chosen target,
  adopted early [IZZ-0313].** Rendered 2026-09-14 at `ARTICLE_TTL_DAYS=20`: **14.336 files =
  72%**, valve idle. `izz-db`/`izz-kv`/`izz-bucket` unbound. [IZZ-0386, IZZ-0313..0315, 0361]
- **`izz-failover` — KEEP [IZZ-0362]; marja e DECLARAT NECUNOSCUTĂ [IZZ-0367, IZZ-0369].** Ambele
  cifre publicate („2.9k/zi", „1.5k/zi") sunt retrase: prima fără fereastră, a doua fără `Analytics:Read`.
- **REDUNDANȚA — ÎNCHISĂ [IZZ-0370 → IZZ-0373].** `BUILD_COMMIT_SHA` e în jobul `mirror` (#347).
- **RECIDIVE — roșul de STARE separat de cel de COD [IZZ-0388…0391; #347 merged].** Era 10/19
  roșu pe main fără commit vinovat. **Owner:** podeaua revine roșie peste 640 art./zi [IZZ-0391].
- **Coliziuni de ID în registru — 4 incidente, reparate la ALOCARE [IZZ-0392].** `IZZ-0385` e viu
  în #344 cu alt titlu decât pe main: de renumerotat ACOLO, înainte de aterizare.
- **PR queue — 8 deschise:** #344 TTL · #343 payload · #341 mandat · #340 PRODUS · #336
  registru · #320 Lee · #297 Cronica · #280 CSS. Aterizările: în `specs/registru.tsv`, nu
  aici — o listă moartă reaprinde garda de fantome la fiecare merge.
- **Issues triate 2026-09-13 [IZZ-0381…0383]:** #83 închis. **#198 arhiva rămâne decizie de
  proprietar** (R2 scapă structural; #214 a murit nemergeuit). #233 · #271 — deschise prin design.

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
