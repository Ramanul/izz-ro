# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-10-03 (IZZ-0415 CI pe eșantion aterizat prin #407; IZZ-0416 portrete pe carduri + marcaj AI Act în #408; protecțiile main verificate prin API [IZZ-0417])

## Open
- **`ai_gateway` — aterizat pe main prin #390, merged (mai demult și #387, merged):**
  gateway AI local $0; cheile doar în `.env`; docs: `ai_gateway/FREE_AI_SETUP.md`.
  Cataloagele free churn-uisază: 2 oct, `llama-3.3-70b*`/`kimi-k2` dispăruți, `qwen-3.8-27b` nou la ambii.
- **Pages `izz-ro` ZOMBI revendică `izz.ro` [IZZ-0366, 0368]:** ștergerea = decizie proprietar [IZZ-0395].
- **PRODUS P1 — homepage fără nicio fotografie [IZZ-0403]:** mecanismul e IMPLEMENTAT în #408 (portretul
  entității pe card, între poza de lead și arta desenată; 0→17 img pe sample-ul de 3 oct, test `test_card_portrete`).
  Corecție de cifră: rata de potrivire e **34% azi (68/200)**, nu 73% cât s-a măsurat pe 13 sept.
- **PRODUS P2 — copertile arată amatoricesc [IZZ-0404]** (verdict proprietar); `htmlart`/`covers.py`.
- **PRODUS P3 — harta: markere fără ierarhie vizuală [IZZ-0405]:** 482 evenimente, clickuri cablate; e afordanța, nu funcția.
- **FEREASTRA TTL a trecut de buget [IZZ-0400]:** 11.967 vs prag 12.800; `ARTICLE_TTL_DAYS` = decizie proprietar [IZZ-0401].
- **Free-readiness — gazda ÎNCĂ PAID până 22 sep [IZZ-0313]:** ingest median 960/zi vs 590 dimensionat; TTL=20
  trebuie scurtat spre ≈13 zile, altfel podea roșie [IZZ-0386, 0391, 0399].
- **`izz-failover` — KEEP [IZZ-0362]; marja NECUNOSCUTĂ [IZZ-0367, 0369]:** ambele cifre publicate retrase.
- **REDUNDANȚA — ÎNCHISĂ [IZZ-0370 → IZZ-0373]:** `BUILD_COMMIT_SHA` e în jobul `mirror`, prin #347 merged.
- **RECIDIVE — roșul de STARE separat de cel de COD [IZZ-0388…0391]; Owner: podeaua roșie peste 640 art./zi [IZZ-0391].**
- **Coliziuni de ID reparate la ALOCARE [IZZ-0392]; IZZ-0400 aterizat prin #344 merged.**
- **PR queue — 0 deschise.** Aterizările din 2 oct (toate merge-uite): în `specs/registru.tsv`, nu aici.
- **Issues triate 09-13 [IZZ-0381…0383]:** #83 închis. **#198 arhiva = decizie de proprietar**
  (R2 singura structurală). #233 canal · #271 scope — deschise prin design.

## Audit closure status

- **K1–K14:** re-verified in `specs/regim-reguli.md` — a reconciliation register, not a substitute
  for passing tests. **Grounding:** blocks invented quotes and foreign numbers, fails closed.
- **Coordination:** live channel is `handoff/` + `specs/STATE.md`. **Containment:** destructive git
  commands and direct Edit/Write on control-plane files are denied; fd-only redirects no longer
  count [IZZ-0353]. **Journals:** takedowns removed on every publish path; ingest discards logged.
- **Near-verbatim copy:** >=15-word runs and transcribed titles block the gate. Open: calibration
  corpus, 2x determinism run. **Silence detection:** hourly. **Human gate:** `IZZ_REQUIRE_HUMAN_GATE`.
  **Main** is `protected: true`; **required status checks: NICIUNUL** (verificat prin API,
  3 oct — GET `/branches/main/protection` răspunde 200; întâiul 403 era alt endpoint/context);
  force-push și ștergeri blocate, `enforce_admins` on, rulesets: none. [IZZ-0417]
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
