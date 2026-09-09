# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-09-09 (migrare pe Workers Free: arta in pagina, TTL 21, plafon 20.000)

## Open

- **Workers Free — branch `claude/cloudflare-free-migration-2sqeju`.** Plafonul redevine 20.000
  de fisiere/versiune din 22 septembrie. Masurat: 51.896 fisiere inainte (259%), 16.732 dupa
  (84%); arta se deseneaza in pagina, `ARTICLE_TTL_DAYS=21`, og:image propriu doar pe fereastra
  recenta. Cifre si alternative respinse: `specs/cloudflare-free-2026-09.md`. [IZZ-0313..0315]
- **De verificat de proprietar INAINTE de downgrade:** Cloudflare refuza trecerea Paid -> Free
  cat timp exista un namespace Durable Object cu backend key-value (docs, citit 09-09). Codul
  deployat al lui `izz-failover` nu exporta nicio clasa DO, deci probabil nu mai exista niciunul,
  dar namespace-urile nu sunt listabile din sesiune: de confirmat in Workers -> Durable Objects.
- **De verificat dupa 22 septembrie:** minutele Workers Builds pe Free (necitibile din sesiune).
  Daca se epuizeaza, publicarea se muta pe `.github/workflows/deploy-worker.yml` (Actions e
  gratuit pe repo public) SI se deconecteaza integrarea git — altfel publica amandoua.
- **Cloudflare routes — OWNER DECISION:** `izz.ro/*` points straight at `izz-ro` since 09-06
  (IZZ-0308), so automatic failover is off. On Free that is the cheap routing (static-asset hits
  are unmetered); `izz-failover` would meter every hit against 100k/day.

## Audit closure status

- **K1–K14:** re-verified mechanism-by-mechanism in `specs/regim-reguli.md` — a reconciliation
  register, not a substitute for passing tests. **Grounding:** blocks deterministic invented quotes
  and foreign numbers, fails closed on missing evidence; order is grounding → QA → commit.
- **Coordination:** live channel is `handoff/` + `specs/STATE.md`; historical dashboards stay historical.
- **Containment:** destructive git commands and direct Edit/Write on control-plane files are denied;
  the hook contract is under test.
- **Journals:** `moderation.yaml` `takedowns` (URL -> motive) removed on every publish path with an
  idempotent trail in `data/takedown_log.jsonl`; ingest discards per run in `data/triage_log.jsonl`.
- **Near-verbatim copy:** >=15-word verbatim runs outside quotes and fully transcribed titles block the
  gate (`text_copiat`, `titlu_copiat`), thresholds from REGULI-SINTEZA 2.2, no calibration corpus yet;
  violations defer the item, not the release.
- **Silence detection:** hourly `detectie-tacere.yml` checks build/monitor/smoke/feedcheck and the last
  content commit; alert issue opens on silence, closes on recovery. **Human gate:**
  `IZZ_REQUIRE_HUMAN_GATE` repo variable (default false); `hold_important` is the per-config switch.
- **Bash writes are guarded:** the protected-edit PreToolUse hook covers Bash commands combining a
  control-plane path with a write indicator; wiring under test (`tests/test_hooks_cablaj.py`).

## Standing rules

- Free plan: `izz.ro` must be served by the assets-only Worker. Routing it through `izz-failover`
  turns every hit into a metered Worker request (100k/day) instead of a free static-asset hit.
- Do not treat retired static-host origins as live origins; Worker origin is the fallback verification path.
- Do not use old task journals as normative coordination channels.
- Do not describe historical benchmark values as current measurements.
- Do not mark live, GitHub settings, or Cloudflare facts as solved based only on repository code.
