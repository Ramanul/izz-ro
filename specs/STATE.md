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
- **Downgrade blockers — CLEARED.** 0 Durable Object namespaces (the one thing refusing Paid -> Free);
  KV/R2/D1 exist, unbound, within free tiers. Open: Workers Builds minutes on Free — unreadable from
  session; if they run out, publishing moves to `deploy-worker.yml` AND git integration must go.
- **INGEST COLLAPSE — fix merged (#328).** Root cause: `FETCH_GLOBAL_DEADLINE_S=300` cut the last
  ~142 of 634 sources. Verify the recovery on live volume; levers stay owner's call. [IZZ-0317]
- **Cloudflare routes — on `izz-failover`, confirmed live 09-09** (overturns IZZ-0308): ~2.9k hits/day
  vs 100k Free, failover kept, assets routing owner's call. The ~48% error rate was a dashboard cron
  with no `scheduled()` — deleted, verified silent. [IZZ-0318/0319]
- **PR queue (open >24h):** #321 §5.4 guard · #324 Bash-guard hook (overlaps IZZ-0353) · #320 Lee
  audit · #297 Cronica vie — owner acceptance · #280 stale, close candidate.


## Audit closure status

- **K1–K14:** re-verified mechanism-by-mechanism in `specs/regim-reguli.md` — a reconciliation
  register, not a substitute for passing tests. **Grounding:** blocks deterministic invented quotes
  and foreign numbers, fails closed on missing evidence; order is grounding → QA → commit.
- **Coordination:** live channel is `handoff/` + `specs/STATE.md`. **Containment:** destructive git
  commands and direct Edit/Write on control-plane files are denied.
- **Journals:** `takedowns` in `moderation.yaml` removed on every publish path (trail in
  `data/takedown_log.jsonl`); ingest discards per run in `data/triage_log.jsonl`.
- **Near-verbatim copy:** >=15-word verbatim runs outside quotes and fully transcribed titles block the
  gate, thresholds from REGULI-SINTEZA 2.2, no calibration corpus yet; violations defer the item.
- **Silence detection:** hourly `detectie-tacere.yml`. **Human gate:** repo var `IZZ_REQUIRE_HUMAN_GATE`,
  default false. **Main** is `protected: true`; the required-checks list is unreadable from a session.
- **Bash writes are guarded:** the protected-edit hook covers Bash commands combining a control-plane
  path with a write indicator; fd-only redirects (`2>&1`, `/dev/null`) no longer count [IZZ-0353].
- **Unified audit (xlsx 2026-09-05) is a mechanical register now:** `specs/audit-unificat.tsv` +
  `tools/audit_matrice.py`, guarded by `tests/test_audit_matrice.py`; findings in
  `specs/audit-unificat.md`. Row 32 was a phantom: an unmerged branch inventoried as a live
  fail-closed gate, `masurat-fals` since IZZ-0266. Open: corpora + 2x determinism. [IZZ-0351/0352]

## Standing rules

- Free plan: `izz.ro` must be served by the assets-only Worker. Routing it through `izz-failover`
  turns every hit into a metered Worker request (100k/day) instead of a free static-asset hit.
- Do not treat retired static-host origins as live origins; Worker origin is the fallback verification path.
- Do not use old task journals as normative coordination channels.
- Do not describe historical benchmark values as current measurements.
- Do not mark live, GitHub settings, or Cloudflare facts as solved based only on repository code.
