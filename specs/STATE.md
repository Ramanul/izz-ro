# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-09-11 (auditul unificat verificat si mutat in registru mecanic; ingest fix #328 mergeuit)

## Open

- **Workers Free — branch `claude/cloudflare-free-migration-2sqeju`.** Cap back to 20.000
  files/version from 22 Sept. Measured: 51.896 files before (259%), 16.732 after (84%). Figures and
  rejected alternatives: `specs/cloudflare-free-2026-09.md`. [IZZ-0313..0315]
- **Downgrade blockers — CLEARED.** 0 Durable Objects; KV/R2/D1 unbound, within free tiers. Open:
  Workers Builds minutes on Free — unreadable here; if spent, publishing moves to `deploy-worker.yml`
  AND the git integration must be disconnected.
- **INGEST COLLAPSE — fix in #328, merged.** Root cause: `FETCH_GLOBAL_DEADLINE_S=300` cut the last
  ~142 of 634 sources. Verify the recovery on live volume; levers stay owner's call. [IZZ-0317]
- **Cloudflare routes — on `izz-failover`, confirmed live 09-09** (overturns IZZ-0308): ~2.9k hits/day
  vs 100k Free, failover kept, assets routing owner's call. The ~48% error rate was a dashboard cron
  with no `scheduled()` — deleted, verified silent. [IZZ-0318/0319]
- **PR queue (open >24h):** #321 §5.4 · #324 Bash-guard (overlaps IZZ-0353) · #320 Lee · #297 Cronica vie · #280 stale.


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

- Free plan: `izz.ro` must be served by the assets-only Worker. Routing it through `izz-failover`
  turns every hit into a metered Worker request (100k/day) instead of a free static-asset hit.
- Do not treat retired static-host origins as live origins; Worker origin is the fallback verification path.
- Do not use old task journals as normative coordination channels.
- Do not describe historical benchmark values as current measurements.
- Do not mark live, GitHub settings, or Cloudflare facts as solved based only on repository code.
