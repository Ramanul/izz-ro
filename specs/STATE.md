# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-09-12 (#333 merged; prospețimea mirror-ului nu e verificată de nimeni)

## Open

- **Pages `izz-ro` e un ZOMBI care revendică `izz.ro` [IZZ-0366, IZZ-0368].** Are atașate
  `izz-ro.pages.dev` **și `izz.ro`**; ultim build reușit 21 aug, apoi 17 eșecuri (#211 merged).
  DNS apex+www → Pages, dar rutele Worker au precedență. 2 sisteme cred că dețin apexul. §10.
- **Workers Free — DONE, measured 2026-09-11.** Assets-only; live serves **13.733 files = 69% of the
  20.000 cap**; `ARTICLE_TTL_DAYS=21` is the lever. Blockers cleared: `izz-db` (0 tables), `izz-kv`,
  `izz-bucket` unbound, within free tiers. Unreadable here: Workers Builds minutes. [IZZ-0313..0315, 0361]
- **`izz-failover` — KEEP [IZZ-0362]; marja e DECLARAT NECUNOSCUTĂ [IZZ-0367, IZZ-0369].** Ambele
  cifre publicate („2.9k/zi", „1.5k/zi") sunt retrase: prima fără fereastră, a doua fără `Analytics:Read`.
- **INGEST COLLAPSE — fix in #328, merged.** Verify recovery on live volume; levers owner's call. [IZZ-0317]
- **REDUNDANȚA: prospețimea mirror-ului nu e verificată [IZZ-0370].** `monitor.yml` (*/10) probează
  toate trei originile dar **doar cu cod HTTP**; `release-probe` compară commitul din `/build.json`
  dar **sare peste mirror**. Ținta failover-ului e singura origine a cărei prospețime n-o verifică
  nimeni — exact eșecul pentru care a fost scris `verify_release.py`. Remediul atinge §10.
- **Rezerve `ALT_ORIGIN` divergente — inert [IZZ-0371].** 3 workflow-uri au ca fallback gazda retrasă
  `izz-ro.pages.dev`, 4 au `workers.dev`. Nu se activează: repo var e setată (verificat în logul
  rulării 34664617862). Devine real doar dacă variabila dispare.
- **PR queue — 8 deschise:** #333 audit, merged [`cc9a7793`] · #331 hartă · #330, #329 dependabot ·
  #324 (needs rebase peste IZZ-0353) · #321 §5.4 · #320 Lee · #297 Cronica vie · #280 CSS.

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
