# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-09-11 (#332 audit unificat MERGED; plan Free reverificat; izz-failover masurat)

## Open

- **Workers Free — DONE, measured 2026-09-11.** The free-migration branch is fully merged (0 commits
  outside main); the deploy config is assets-only; live serves **13.733 files = 69% of the 20.000
  cap**. `ARTICLE_TTL_DAYS=21` is the lever that holds it there. [IZZ-0313..0315, IZZ-0361]
- **Downgrade blockers — CLEARED, re-measured 2026-09-11:** `izz-db` (0 tables), `izz-kv`,
  `izz-bucket` exist, unbound, within free tiers. Open: Workers Builds minutes — unreadable here.
- **INGEST COLLAPSE — fix in #328, merged.** Verify recovery on live volume; levers owner's call. [IZZ-0317]
- **`izz-failover` — KEEP; recommendation against closing [IZZ-0362].** Read its code 09-11: proxies
  to the primary Worker (1.5s timeout), falls back to the mirror, adds edge TTL. Metered on Free, but
  ~2.9k hits/day vs 100k. Not changeable from a session anyway: no MCP tool for routes, §10 owner-only.
- **PR queue:** #332 audit unificat — MERGED [IZZ-0360]. Open: #321 §5.4 · #324 Bash-guard (now
  overlaps the merged IZZ-0353, needs rebase) · #320 Lee · #297 Cronica vie · #280 stale · #331 harta.


## Audit closure status

- **K1–K14:** re-verified mechanism-by-mechanism in `specs/regim-reguli.md` — a reconciliation
  register, not a substitute for passing tests. **Grounding:** blocks deterministic invented quotes
  and foreign numbers, fails closed on missing evidence; order is grounding → QA → commit.
- **Coordination:** live channel is `handoff/` + `specs/STATE.md`. **Containment:** destructive git
  commands and direct Edit/Write on control-plane files are denied.
- **Journals:** takedowns removed on every publish path (`data/takedown_log.jsonl`); ingest
  discards per run in `data/triage_log.jsonl`. `published` is normalized to UTC on load + save.
- **Near-verbatim copy:** >=15-word verbatim runs and transcribed titles block the gate; violations
  defer the item. Open: calibration corpus, 2x determinism run.
- **Silence detection:** hourly. **Human gate:** repo var `IZZ_REQUIRE_HUMAN_GATE`, default false.
  **Main** is `protected: true`; required-checks list unreadable here (403), rulesets: none.
- **Bash writes are guarded** by the protected-edit hook; fd-only redirects no longer count [IZZ-0353].
- **Unified audit (xlsx 2026-09-05) is a mechanical register now:** `specs/audit-unificat.tsv` +
  `tools/audit_matrice.py` + `tests/test_audit_matrice.py`; findings in `specs/audit-unificat.md`.
  Row 32 was a phantom; two more in code, both fixed — a nonexistent SSRF compensation named by
  `guard.py`, and `published is uniform UTC` assumed by `state.save` but broken by the WP-JSON
  path, mis-ordering 159 articles. Content commits pushed with the default `GITHUB_TOKEN` trigger
  NO workflow, so `data/*.json` regressions surface only via a PR — owner call. [IZZ-0351…0357]

## Standing rules

- Free plan: routing `izz.ro` through `izz-failover` meters every hit (100k/day) instead of serving a
  free static-asset hit. Measured 09-11: ~2.9k/day, so the cost is real but not binding — watch it.
- Do not treat retired static-host origins as live origins; Worker origin is the fallback verification path.
- Do not use old task journals as normative coordination channels.
- Do not describe historical benchmark values as current measurements.
- Do not mark live, GitHub settings, or Cloudflare facts as solved based only on repository code.
