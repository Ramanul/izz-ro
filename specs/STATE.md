# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**

**Updated:** 2026-09-05

## Open

- **PR #282 — audit unified hardening (merged, d88f6dd2, 2026-09-05).** Control-urile matricei unificate sunt în `main`; CI verde pe HEAD final (pytest 20m56s, tests + ruff 16m16s). Required checks `pytest` + `tests + ruff` impuse pe `main` (strict, inclusiv admin).
- **Rămân externi:** Cloudflare WAF/DNS; rollback-ul real al drill-ului (modul `check` rulat pe `main`, 2026-09-05, cere confirmare manuală); verificarea live din medii cu domeniul blocat.
- **Detectare tăcere:** prima rulare reală a prins două defecte de integrare (POST implicit pe /commits; alerta lipsă la NECLAR), fix în curs de merge; monitor.yml rulează efectiv la ~4,5h (GitHub amână cron-urile programate), deci plafoanele sunt calibrate pe măsurătoare.

## Audit closure status

- **K1–K14:** closure is being re-verified mechanism-by-mechanism; `specs/regim-reguli.md` is the
  current reconciliation register, not a substitute for passing tests.
- **Grounding:** blocking for deterministic invented quotes and foreign numbers; missing/malformed
  grounding evidence fails closed.
- **Quality/release order:** grounding → QA → commit is enforced in `build.yml`.
- **Coordination:** live channel is `handoff/` + `specs/STATE.md`; historical dashboards stay historical.
- **Containment:** destructive git commands are denied and protected control-plane files are denied
  to direct Edit/Write operations; the hook contract is under test.
- **Takedown registry:** `moderation.yaml` accepts `takedowns` (URL -> motive); removal runs on every
  publish path, with an idempotent audit trail in `data/takedown_log.jsonl` (committed by the pipeline).
- **Near-verbatim copy:** >=15-word verbatim runs outside quotes in summaries and fully transcribed
  titles are grounding-gate blocking codes (`text_copiat`, `titlu_copiat`); thresholds are rule-derived
  (REGULI-SINTEZA 2.2), the calibration journal holds no real corpus yet.
- **Triage journal:** ingest discards (fetch losses, no-substance rejects, expired) land per run in
  `data/triage_log.jsonl`, committed with pipeline state.
- **Silence detection:** hourly `detectie-tacere.yml` checks last runs of build/monitor/smoke/feedcheck
  and the last content commit against ceilings; alert issue opens on silence and closes on recovery.
- **Human gate is a switch:** `IZZ_REQUIRE_HUMAN_GATE` is a repo variable (default false, armable from
  the GitHub UI without code changes); `hold_important` in `moderation.yaml` stays the per-config switch.
- **Bash writes are guarded:** the protected-edit PreToolUse hook covers Bash commands combining a
  control-plane path with a write indicator; read-only mentions and pipeline runs stay allowed.

## Standing rules

- Do not treat retired static-host origins as live origins; Worker origin is the fallback verification path.
- Do not use old task journals as normative coordination channels.
- Do not describe historical benchmark values as current measurements.
- Do not mark live, GitHub settings, or Cloudflare facts as solved based only on repository code.

## Where the rest lives

`specs/regim-reguli.md` — unified audit closure · `specs/istoric-executie.md` — settled history ·
`specs/registru.tsv` — decisions · `specs/masuratori-frontend.md` — measurements · `CLAUDE.md` — canonical contract.
