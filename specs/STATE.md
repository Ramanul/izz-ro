# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.**
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-10-27 (E1 surse + E3 hartă publicate prin #521; 14ad9f2a confirmat pe izz.ro/www).

## Open
- **Transformarea «prin prisma cărților» (`specs/plan-paradigma-izz.md`):** E0–E4 pe main (#511 merged, #512 merged, 23.10) — roluri epistemice + clone, sinteza dialectică verificată per propoziție (3 stări), confirmări încrucișate pe card, roluri în `sources-box`, /sub-prag/, contor de subtracție, capăt pe /azi/, nota de actualizare, memoria subiectelor (12 luni, fără stări judiciare); /principii/ și /legal/method/ fără doctrină (garda `tests/test_garda_anti_doctrina.py`). **D6 fără profilare (#515 merged):** fără profil dedus, GA4, Clarity, bară de consimțământ; rămâne județul ales explicit; curățenia urmelor vechi se scoate după 2027-01-31 [IZZ-0437]. **href extern (#516 merged):** orice `href` cu date din afară trece prin `guard.url_ostil` la randare (filtrul `href_extern`; închide constatarea Semgrep de pe #512). **E1/E3 publicate (#521 merged):** hartă + observații prospective; limite și probe: `specs/editorial-integration.md`; pragul `SILENCE_REJECTION_THRESHOLD` MĂSURAT pe 3 rulări CI: leagă 1 din 74, rămâne 0,34 (`specs/plan-paradigma-izz.md` §5). **#517 merged:** 101 primării ro_hu reapar (sărite din 06.09); amânări pe cauze (`amanare_*`, `b_*`, `oprire_*` în `data/triage_log.jsonl`); lot B tolerant. **Reîncercare C (#518 merged):** 6/9 recuperate pe 4 rulări CI, amânări C 26%→10%; /sub-prag/ pe cauză. Măsurat 23.10 (Lighthouse 13.5 mobil, 3 rulări): articol dialectic Perf 93/95/94 vs. 93/95/95 pe main, A11y/BP/SEO 100; pa11y 0 erori pe paginile noi, home și /surse/ (2 defecte vechi reparate).
- **Editorial transformation:** A/B/C/D published via #476 (merged), #477 (merged), #489 (merged) and #497 (merged); E persistent dossiers and explained relations are included in this release at pilot scale. Live release requires the exact build SHA plus the visible dossier/search checks. F explained selection (#501 merged) is published at pilot scale; release 7f672e26 confirmed on izz.ro/www, 25 Oct. Reader autonomy follows D6 (#515 merged); map lens and prospective source observations (#521 merged) are live at 14ad9f2a on izz.ro/www. Broader coverage remains unfinished.
- **Audite externe:** 3 oct ÎNCHIS [IZZ-0426] (#425 merged, #426 merged; `ai_gateway` pe main, $0, cheile în `.env`) · 4 oct verificat mecanic [IZZ-0432] — 3 confirmate / 2 parțiale / 2 false pozitive (bara de consimțământ și manifestul PWA existau): `notes/analiza-audit-extern-2026-10-04.md`; pe main prin #438 (merged, 6 oct): A1 gardă de diacritice + A2 semnătura editorială/E-E-A-T. #499 (merged) «guard degraded AI output and diacritics», integrat 25 oct.
- **PWA + alerte push [IZZ-0430/0431] — PE MAIN (#434 merged):** SW la `/sw.js`, buton instalare, alerte VAPID; fără namespace KV + 4 secrete (`infra/PUSH-SETUP.md`) rutele dau 503. Verificarea Content-Type a manifestului e mecanizată (P0.1 în #438) — de rulat pe live.
- **PRODUS P1/P2 — media pe carduri [IZZ-0403, 0404 → IZZ-0416; #414 merged]:** portrete PD/CC0 + siluete județ,
  `covers.py` editorial; 16 oct: portret doar pt. omul din titlu, decupat pe față, `sw.js` v2 (`specs/istoric-executie.md`). **17 oct:** #490 merged · #491 merged · #492 merged · #493 merged · #494 merged — local/județean fără ziua lunii, forma UAT/județului în aur; articol cu foto de arhivă a omului din titlu; card cu CC BY + credit complet, o dată pe pagină; lead de localitate CC BY per QID cu motiv de miss; poze oficiale doar neutre (listă albă pe sursă). Href-urile de credit cer https absolut. Pozele noi apar pe măsură ce `fetch_leadphotos`/`fetch_eventphotos` rulează în build. **Marcaj AI Act la prima expunere [IZZ-0420]:** trust-label «generat automat» pe card +
  meta digitalSourceType + pictograma UE Basic — amendament §4.3 adoptat, veto neexercitat [IZZ-0423].
- **PRODUS P3 — harta: markere fără ierarhie vizuală [IZZ-0405]:** 482 evenimente, clickuri cablate; e afordanța, nu funcția. **Atribuire geo, 16 oct [IZZ-0433]** + **17 oct [IZZ-0434]:** pini corecți, nivel = precizie; o culoare după locul știrii, proveniența în panoul județului; telefon: pinch, fără chenar de focus, harta în primul ecran, filtrele în sheet. `harta_dom_check`: GESTURI TACTILE verde; FAIL rămas = 2 puncte de frontieră, identic pe HEAD (#454).
- **FEREASTRA TTL — 11 zile (aprobată de proprietar, 25 oct):** pe a7bf06ae garda brută scade de la 13.025 la 11.833 (plafon 12.600). Testul de siguranță rămâne neschimbat; măsurarea pierderii și precedentul sunt în config.py.
- **Free-readiness — gazda ÎNCĂ PAID până 22 sep [IZZ-0313]:** [IZZ-0386, 0391, 0399] [IZZ-0421, 0424].
- **`izz-failover` — KEEP [IZZ-0362]; marja NECUNOSCUTĂ [IZZ-0367, 0369]:** ambele cifre publicate retrase.
- **REDUNDANȚA — ÎNCHISĂ [IZZ-0370 → IZZ-0373]:** `BUILD_COMMIT_SHA` în jobul `mirror`, #347 merged. **RECIDIVE —
  roșul de STARE separat de cel de COD [IZZ-0388…0391]; Coliziuni de ID la ALOCARE [IZZ-0392].**
- **Audit og:image #431 (merged) [IZZ-0429]:** 11.114/11.114 pe randarea declarată, fix static pentru hartă; CI main verde (runs 37150541651, 37150541665). Fără probă HTTP live; auditul dă 0 la output lipsă — follow-up deschis. Coada: `gh pr list`.
- **Issues triate 09-13 [IZZ-0381…0383]:** #83 închis. **#198 arhiva = decizie de proprietar**
  (R2 singura structurală). #233 canal · #271 scope — deschise prin design. PR #513 (merged): politica extensiei, în afara transformării editoriale.

## Audit closure status

- D release: #497 merged, CI and release verifier passed; exact build SHA and versioned update script confirmed on izz.ro/www. Empty production corrections catalog; synthetic cases test-only. E adds persistent documentary dossiers with evidence-backed relations; Gemini Argon Maximum and Google Search AI Argon reviews produced reproduced regressions. Release evidence belongs to the current PR checks and the release verifier; a model opinion is not execution evidence. Evidence: specs/editorial-corrections.md and specs/editorial-dossiers.md.
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
- Use current handoff for coordination; every measurement needs its window and command [IZZ-0367].
- Do not mark live, GitHub settings, or Cloudflare facts as solved based only on repository code.
