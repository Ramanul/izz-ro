# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-09-15 (#347 + #341 aterizate: poarta de stare, apoi mandatul permanent de merge)

## Open

- **Pages `izz-ro` e un ZOMBI care revendică `izz.ro` [IZZ-0366, IZZ-0368].** Are atașate
  `izz-ro.pages.dev` **și `izz.ro`**; ultim build reușit 21 aug, apoi 17 eșecuri (#211 merged).
  DNS apex+www → Pages, dar rutele Worker au precedență. 2 sisteme cred că dețin apexul. §10.
- **Free-readiness — gazda e ÎNCĂ PAID (100.000) până 22 sep; 20.000 e ținta adoptată devreme
  [IZZ-0313].** Randat 09-14 la TTL=20: 14.336 fișiere (72%), supapa inactivă. **Măsurat 09-15:**
  fereastra are 11.250 articole din podeaua de 12.800, iar ingestul median e **960/zi** față de
  590/zi pe care s-a dimensionat spec-ul — echilibrul cere TTL ≈ **13 zile**, nu 20; podea roșie
  ~09-17. `izz-kv`/`izz-bucket` nelegate; minutele de Workers Builds necitibile. [IZZ-0386, 0361]
- **`izz-failover` — KEEP [IZZ-0362]; marja e DECLARAT NECUNOSCUTĂ [IZZ-0367, IZZ-0369].** Ambele
  cifre publicate („2.9k/zi", „1.5k/zi") sunt retrase: prima fără fereastră, a doua fără `Analytics:Read`.
- **REDUNDANȚA — REPARAT [IZZ-0370 → IZZ-0372].** Rămâne de curățat: manifestul mirror-ului
  poartă `GITHUB_SHA`, nu content-sha — o linie `BUILD_COMMIT_SHA` în jobul `mirror`, blocată de
  hook (capacitate), NU de §10, care nu acoperă workflow-uri [IZZ-0373].
- **PR queue — 7 deschise:** #344 TTL · #343 payload · #340 PRODUS · #336 registru · #320 Lee ·
  #297 Cronica · #280 CSS. Aterizările: în `specs/registru.tsv`, nu aici — o listă de PR-uri moarte
  în `## Open` reaprinde garda de fantome la fiecare merge.
- **Issues triate 2026-09-13 [IZZ-0381…0383]:** #83 închis (blocaje moarte; §14 l-a înlocuit).
  **#198 arhiva rămâne decizie de proprietar** (R2 e singura care scapă structural; #214 a murit
  nemergeuit). #233 canal · #271 scope — deschise prin design.

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
  Derivarea de stare o găsește `schedule` zilnic (#347), nu următorul PR. [IZZ-0351…0357, 0363…0367]

## Standing rules

- Cadence is the GitHub scheduler, not the 105-min gate: 25% firing, ~6 starts/day, median ~4h.
  Re-measure with `tools/cadenta_reala.py`; do not quote the number from memory. [IZZ-0364]
- Do not treat retired static-host origins as live origins; Worker origin is the fallback path.
- Do not use old task journals as normative coordination channels.
- Every measurement gets its window and its command, or it is not a measurement [IZZ-0367].
- Do not mark live, GitHub settings, or Cloudflare facts as solved based only on repository code.
