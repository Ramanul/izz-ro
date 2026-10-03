# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-10-03 (IZZ-0415 CI pe eșantion prin #407; IZZ-0416 media cardurilor PD/CC0 prin #414; IZZ-0420 marcaj AI Act în #411; protecțiile main verificate prin API [IZZ-0417]; audit extern triat + rezolvat prin #425, #426 [IZZ-0426])

## Open
- **Audit extern 3 oct — ÎNCHIS [IZZ-0426]** (#425, #426 merged) · **`ai_gateway` pe main** (#390, #387): $0, cheile în `.env`.
- **PWA + alerte push [IZZ-0430, IZZ-0431] — PR DESCHIS, fără merge:** SW la `/sw.js`, buton instalare fix, alerte VAPID în KV. **Blochează pe tine:** namespace KV + 4 secrete (`infra/PUSH-SETUP.md`); fără ele rutele dau 503 și site-ul merge ca azi.
- **Pages `izz-ro` ZOMBI — CONFIRMAT ȘTERS [IZZ-0411]:** `izz-ro.pages.dev` returnează `000` [IZZ-0366, 0395].
- **PRODUS P1/P2 — media pe carduri [IZZ-0403, 0404 → IZZ-0416; #414 merged]:** portrete PD/CC0 + siluete județ,
  `covers.py` editorial. **Marcaj AI Act la prima expunere [IZZ-0420]:** trust-label «generat automat» pe card +
  meta digitalSourceType + pictograma UE Basic — amendament §4.3 adoptat, veto neexercitat [IZZ-0423].
- **PRODUS P3 — harta: markere fără ierarhie vizuală [IZZ-0405]:** 482 evenimente, clickuri cablate; e afordanța, nu funcția.
- **FEREASTRA TTL — DECIZIE EXECUTATĂ [IZZ-0421, 0424, 3 oct]:** tripwire-ul a crapat pe starea reală
  (20.543 în fereastră vs 12.600, după ce #408 (merged) a adus datele reale); TTL 20 → 11, apoi 12 după
  tăietura a 4 surse tech-en fără vizitatori măsurați (Q5). Marja actuală: 10.665 în fereastră (~2 zile).
  Se re-evaluează la 13 când ingestul median coboară sub ~900/zi (automatizare lunară activă).
- **Free-readiness — gazda ÎNCĂ PAID până 22 sep [IZZ-0313]:** [IZZ-0386, 0391, 0399] [IZZ-0421, 0424].
- **`izz-failover` — KEEP [IZZ-0362]; marja NECUNOSCUTĂ [IZZ-0367, 0369]:** ambele cifre publicate retrase.
- **REDUNDANȚA — ÎNCHISĂ [IZZ-0370 → IZZ-0373]:** `BUILD_COMMIT_SHA` în jobul `mirror`, #347 merged. **RECIDIVE —
  roșul de STARE separat de cel de COD [IZZ-0388…0391]; Coliziuni de ID la ALOCARE [IZZ-0392].**
- **Audit og:image #431 (merged) [IZZ-0429]:** 11.114/11.114 pe randarea declarată, fix static pentru hartă; CI main verde (runs 37150541651, 37150541665). Fără probă HTTP live; auditul dă 0 la output lipsă — follow-up deschis. Coada: `gh pr list`.
- **Issues triate 09-13 [IZZ-0381…0383]:** #83 închis. **#198 arhiva = decizie de proprietar**
  (R2 singura structurală). #233 canal · #271 scope — deschise prin design.

## Audit closure status

- **K1–K14:** re-verified in `specs/regim-reguli.md` — a reconciliation register, not a substitute
  for passing tests. **Grounding:** blocks invented quotes and foreign numbers, fails closed.
- **Coordination:** `handoff/` + `specs/STATE.md`. **Containment:** git destructiv și Edit pe control-plane
  refuzate [IZZ-0353]. **Journals:** takedowns șterse pe fiecare cale de publicare; ingest discards logged.
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
