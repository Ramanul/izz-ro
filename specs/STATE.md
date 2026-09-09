# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-09-09 (migrare Free merged #326; ruta pe izz-failover confirmata; cron fantoma sters)

## Open

- **Workers Free — branch `claude/cloudflare-free-migration-2sqeju`.** Plafonul redevine 20.000
  de fisiere/versiune din 22 septembrie. Masurat: 51.896 fisiere inainte (259%), 16.732 dupa
  (84%); arta se deseneaza in pagina, `ARTICLE_TTL_DAYS=21`, og:image propriu doar pe fereastra
  recenta. Cifre si alternative respinse: `specs/cloudflare-free-2026-09.md`. [IZZ-0313..0315]
- **Downgrade blockers — CLEARED.** 0 Durable Object namespaces on the account (the one thing that
  refuses Paid -> Free); KV `izz-kv`, R2 `izz-bucket`, D1 `izz-db` (0 tables) exist, are unbound and
  fit the free tiers. Open: Workers Builds minutes on Free — unreadable from session; if they run
  out, publishing moves to `deploy-worker.yml` AND the git integration must be disconnected.
- **INGEST COLLAPSE — separate from the Free migration, not caused by it.** Published volume fell to
  ~5% on 09-05: 730–1052 articles/day on 09-01..09-04, then 43–183/day; `sitemap-news.xml` live holds
  6 articles for 09-09. Category sorting is correct — there is simply no fresh content. ~5 pipeline
  runs/day (not ~12), 49–85 min each, 4 failures in 12, all `release-probe` (Cloudflare needs >25 min
  for 51.896 files). Levers (`MAX_AI_CALLS_PER_RUN=40`, `PRAG_MIN=105`) are in `build.yml` — protected,
  owner's call. [IZZ-0317]
- **Cloudflare routes — on `izz-failover`, confirmed live 09-09** (`x-izz-origin: primary`, overturns
  IZZ-0308): ~2.9k hits/day vs 100k Free, failover kept; assets routing stays owner's call. The ~48%
  error rate was a dashboard cron with no `scheduled()` (08-22) — deleted, verified silent. [IZZ-0318/0319]


## Audit closure status

- **K1–K14:** re-verified mechanism-by-mechanism in `specs/regim-reguli.md` — a reconciliation
  register, not a substitute for passing tests. **Grounding:** blocks deterministic invented quotes
  and foreign numbers, fails closed on missing evidence; order is grounding → QA → commit.
- **Coordination:** live channel is `handoff/` + `specs/STATE.md`; historical dashboards stay historical.
  **Containment:** destructive git commands and direct Edit/Write on control-plane files are denied.
- **Journals:** `takedowns` in `moderation.yaml` removed on every publish path (trail in
  `data/takedown_log.jsonl`); ingest discards per run in `data/triage_log.jsonl`.
- **Near-verbatim copy:** >=15-word verbatim runs outside quotes and fully transcribed titles block the
  gate, thresholds from REGULI-SINTEZA 2.2, no calibration corpus yet; violations defer the item.
- **Silence detection:** hourly `detectie-tacere.yml`. **Human gate:** `IZZ_REQUIRE_HUMAN_GATE`
  repo variable, default false.
- **Bash writes are guarded, with declared gaps:** PreToolUse blocks a control-plane path paired with a
  write indicator; behaviour under test (`tests/test_agent_protected_edits.py`), wiring separately
  (`tests/test_hooks_cablaj.py`). Shell-expansion forms (backslash, glob) stay open by design — substring match.

## Standing rules

- Free plan: `izz.ro` must be served by the assets-only Worker. Routing it through `izz-failover`
  turns every hit into a metered Worker request (100k/day) instead of a free static-asset hit.
- Do not treat retired static-host origins as live origins; Worker origin is the fallback verification path.
- Do not use old task journals as normative coordination channels.
- Do not describe historical benchmark values as current measurements.
- Do not mark live, GitHub settings, or Cloudflare facts as solved based only on repository code.
