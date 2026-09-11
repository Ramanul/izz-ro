# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-09-11 (foaia Eroziune aplicată; cadența re-măsurată, §17 corectată)

## Open

- **Workers Free — DONE, measured 2026-09-11.** Free-migration branch fully merged (0 commits
  outside main); deploy config assets-only; live serves **13.733 files = 69% of the 20.000 cap**;
  `ARTICLE_TTL_DAYS=21` is the lever. Blockers cleared: `izz-db` (0 tables), `izz-kv`, `izz-bucket`
  unbound, within free tiers. Still unreadable here: Workers Builds minutes. [IZZ-0313..0315, 0361]
- **INGEST COLLAPSE — fix in #328, merged.** Verify recovery on live volume; levers owner's call. [IZZ-0317]
- **`izz-failover` — KEEP; recommendation against closing [IZZ-0362].** Proxies to the primary Worker
  (1.5s timeout), falls back to the mirror. Metered on Free, but ~2.9k hits/day vs 100k — real cost,
  not binding. Not changeable from a session anyway: no MCP tool for routes, §10 owner-only.
- **CADENCE — the contract was wrong for 8 days [IZZ-0363/0364].** IZZ-0292 had already measured that
  the GitHub scheduler, not the 105-min gate, sets the rhythm; §17 never learned it. Re-measured on
  40 runs: 25% firing, ~6 starts/day, median gap ~4h, **0 of 39 intervals under the gate**. Real
  publishing rhythm is ~4h, not ~2h. Cron unchanged — owner/product call, §10. `tools/cadenta_reala.py`.
- **PR queue:** #333 audit (eroziune + cadență) open. Also #321 §5.4 · #324 Bash-guard (needs rebase
  over the merged IZZ-0353) · #320 Lee · #297 Cronica vie · #280 stale · #331 harta.

## Audit closure status

- **K1–K14:** re-verified mechanism-by-mechanism in `specs/regim-reguli.md` — a reconciliation
  register, not a substitute for passing tests. **Grounding:** blocks deterministic invented quotes
  and foreign numbers, fails closed on missing evidence; order is grounding → QA → commit.
- **Coordination:** live channel is `handoff/` + `specs/STATE.md`. **Containment:** destructive git
  commands and direct Edit/Write on control-plane files are denied; fd-only redirects no longer
  count [IZZ-0353]. **Journals:** takedowns removed on every publish path; ingest discards logged.
- **Near-verbatim copy:** >=15-word verbatim runs and transcribed titles block the gate; violations
  defer the item. Open: calibration corpus, 2x determinism run.
- **Silence detection:** hourly. **Human gate:** repo var `IZZ_REQUIRE_HUMAN_GATE`, default false.
  **Main** is `protected: true`; required-checks list unreadable here (403), rulesets: none.
- **Unified audit (xlsx 2026-09-05) is mechanical now:** `specs/audit-unificat.tsv` +
  `tools/audit_matrice.py` (+ `eroziune`) + tests; findings in `specs/audit-unificat.md`. Three
  phantoms found, two fixed in code (SSRF compensation named by `guard.py`; `published` UTC assumed
  by `state.save`). Content commits pushed with the default `GITHUB_TOKEN` trigger NO workflow, so
  state regressions surface only via a PR — owner call. [IZZ-0351…0357, 0363…0365]

## Standing rules

- Do not treat retired static-host origins as live origins; Worker origin is the fallback verification path.
- Do not use old task journals as normative coordination channels.
- Do not describe historical benchmark values as current measurements — cadence moved 29% in 8 days.
- Do not mark live, GitHub settings, or Cloudflare facts as solved based only on repository code.
