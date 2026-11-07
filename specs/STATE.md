# STATE — project execution state

> Single source of truth for where we are. Manager-owned; executors read it. Keep this file short
> and factual; settled history belongs in `specs/istoric-executie.md`.
>
> **Hard cap: ~40 lines of content.** **Plafon de octeți: 6 KB.**
>
> Ambele plafoane se verifică mecanic (`tests/test_reguli.py`). Al doilea există pentru că hook-ul
> `SessionStart` tipărește fișierul integral la fiecare pornire de sesiune: un rând de 200 de
> caractere nu e „un rând", e context plătit de fiecare dată. Blocul dinainte de condensare:
> `specs/istoric-executie.md`, secțiunea „Mutat din STATE.md pe 2026-11-07".
>
> Where the rest lives: `specs/regim-reguli.md` — unified audit closure ·
> `specs/registru.tsv` — decisions · `CLAUDE.md` — canonical contract.

**Updated:** 2026-11-07 (rebranding #542 merged și LIVE; rămasă decizia de fonturi).

## Open
- **Rebranding „Hârtie curată" — #542 merged 7 nov, LIVE:** fazele 0–7 (tokeni +
  Newsreader/Inter, masthead, card 7→4 elemente, pagină de articol, coperți pe același serif,
  o foaie de stil, harta pe alamă, utilitare fără emoji, portrete re-encodate). Prima pagină
  593→139 KB brut / 109→36,7 KB gzip; articolul cel mai greu 553→193 KB. Cifre:
  `analiza/rebranding/PROPUNERE.md` §8, `specs/masuratori-frontend.md`. Rămas: decizia de
  fonturi (5 fețe/76 KB vs ținta 3/55 KB — variantele măsurate în §8.4).
- **Transformarea «prin prisma cărților» (`specs/plan-paradigma-izz.md`):** E0–E4 pe main (#511 merged · #512 merged · #521 merged); D6 fără profilare (#515 merged); `href` extern prin `guard.url_ostil` (#516 merged). `SILENCE_REJECTION_THRESHOLD` rămâne 0,34 (leagă 1 din 74). Curățenia urmelor vechi din browsere: după 2027-01-31 [IZZ-0437].
- **PWA + alerte push [IZZ-0430/0431] — PE MAIN (#434 merged):** fără namespace KV + 4 secrete (`infra/PUSH-SETUP.md`), rutele dau 503.
- **Media pe carduri [IZZ-0403/0404 → IZZ-0416]:** portrete PD/CC0, siluete de județ, `covers.py`; marcaj AI Act la prima expunere [IZZ-0420/0423]. Pozele noi apar pe măsură ce `fetch_leadphotos`/`fetch_eventphotos` rulează în build.
- **Harta [IZZ-0405, 0433, 0434]:** pini după precizie, proveniența în panoul județului, gesturi tactile. FAIL rămas: 2 puncte de frontieră, identic pe HEAD (#454).
- **FEREASTRA TTL — 11 zile (aprobată de proprietar, 25 oct):** garda brută 13.025 → 11.833 (plafon 12.600) pe `a7bf06ae`; testul de siguranță neschimbat. Măsurarea pierderii: `generator/config.py`.
- **Free-readiness — gazda ÎNCĂ PAID [IZZ-0313]:** [IZZ-0386, 0391, 0399, 0421, 0424].
- **`izz-failover` — SCOS DIN TRAFIC, 31 oct (decizie proprietar):** `izz.ro/*` stă pe `izz-ro` (`wrangler.jsonc`); revenire: `infra/README-failover.md`. Auditurile se fac pe `izz-ro.andifreelancer2.workers.dev`. Oglinda 3,73 GB vs 1 GB la GitHub — nerezolvat.
- #525 memory-ledger guard: separate review pending.

## Audit closure status
- **K1–K14:** re-verified in `specs/regim-reguli.md` — registru, nu substitut pentru teste. **Grounding:** blochează citate inventate și cifre străine, fails closed.
- **Coordination:** `handoff/` + `specs/STATE.md`. **Containment:** git destructiv și Edit pe control-plane refuzate [IZZ-0353]. **Journals:** takedowns șterse pe fiecare cale de publicare; ingest discards logged.
- **Near-verbatim copy:** >=15-word runs and transcribed titles block the gate. Open: calibration corpus, 2x determinism run. **Silence detection:** hourly. **Human gate:** `IZZ_REQUIRE_HUMAN_GATE`. **Main** `protected: true`, required status checks: NICIUNUL (API, 3 oct), force-push și ștergeri blocate, `enforce_admins` on [IZZ-0417].
- **Unified audit is mechanical:** `specs/audit-unificat.tsv` + `tools/audit_matrice.py` (+ `eroziune`) + `tools/cadenta_reala.py`; findings în `specs/audit-unificat.md` §5. Derivarea de stare o găsește `schedule` zilnic (#347). [IZZ-0351…0357, 0363…0367]

## Standing rules
- Cadence is the GitHub scheduler, not the 105-min gate: 25% firing, ~6 starts/day, median ~4h. Re-measure with `tools/cadenta_reala.py`; do not quote the number from memory. [IZZ-0364]
- Do not treat retired static-host origins as live origins; Worker origin is the fallback path.
- Use current handoff for coordination; every measurement needs its window and command [IZZ-0367].
- No live/GitHub/Cloudflare claim without proof. Capacity: `docs/cloudflare-free-capacity.md`.
