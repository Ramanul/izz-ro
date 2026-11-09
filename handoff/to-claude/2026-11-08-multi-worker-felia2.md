# Multi-Worker Free — unde am rămas (2026-11-08)

Plan complet: `specs/multi-worker-free-2026-11.md` (5 felii, §4; rezultate §9–§11). Decizii: IZZ-0453 (R2 respins), IZZ-0454 (plan), IZZ-0455 (felia 0).

## Făcut
- **Felia 0** — confirmat pe live: ruta mai specifică câștigă; un fișier lipsă din ciob NU cade pe principal.
- **Felia 1** — #567 merged (d98ea3d1d): `generator/shard.py` împarte `output/` în 23 de cioburi, 0 fișiere pierdute; fără efect live.
- **Felia 2** — PR #568 (`feat/shard-felia-2`), CI verde pe b53333c77: `deploy-worker.yml` publică `config.SHARDS_LIVE` înaintea principalului și verifică `build.json` pe originea ciobului.
  - Pilot `izz-ro-cat-auto` publicat manual și confirmat pe live (13 adrese, aceleași coduri).
  - **OPRIT 8 nov seara** (`wrangler delete`), la cererea proprietarului: fără merge, ciobul ar fi rămas înghețat. După ștergere, live identic cu înainte.
  - Consultări: consult-merge-567, consult-felia2-design, consult-felia2-diff (rezerva Argon).

## Reluat 9 nov — felia 2 LIVE
Pașii 1–4 de mai jos sunt făcuți: merge `3d817ac11`, deploy-worker verde (rutele s-au legat din CI),
sonda pe 13 adrese identică cu înainte. Detalii: spec §11–§14. **Felia 3, loturile 1-3 (`ai`..`economic`) LIVE** (#569, #570, #571, `c7da73f68`, run `42588777721`, 81 adrese identice). **Rămâne:** felia 3 lotul 4 (`extern`, `sport`, cere „da”) și
verificarea în Analytics că invocările scriptului nu cresc. Reamintirea de vineri: pornește de aici.

## Următorul pas (13 nov) — ISTORIC, făcut pe 9 nov
1. Fetch + rebase #568; CI verde pe head; scoate-l din `## Open` în STATE.md înainte de merge.
2. Merge (`--match-head-commit`), apoi `gh workflow run deploy-worker.yml -f confirmare=deploy`. Urmărești rularea până la capăt.
3. **Riscul nedovedit:** tokenul din GitHub poate să nu aibă dreptul de a lega rute. Dacă pasul „Publica cioburile live” pică, principalul nu se publică: revert #568 imediat.
4. Verde → sonda pe 13 adrese (`/auto/`, `/auto`, paginare, articole, imagini, feed, expirat, inexistent, `/politic/`, `/`).
5. Apoi feliile 3–5 (§4): restul cioburilor, scoaterea categoriilor din principal, plafonul.

Nu delega feliile 2–4 la arena: ating deploy și rute (zonă protejată §10).

## Cerut tot pe 8 nov (separat de Multi-Worker)
- **Pagina de articol repetă de 4 ori că textul e generat automat** (eticheta de sus, bulina „Titlu sintetizat automat”, caseta gri, blocul „Transparență și corecții”). Proprietarul o găsește enervantă (N2). Propunere: O singură propoziție sub rezumat + sursa + „Raportează o eroare” + link spre politica de corecții. Înainte: `python tools/registru.py find transparenta` (poate fi decizie veche), iar forma finală o aprobă proprietarul (zonă legală §10; AI Act art. 50 cere un avertisment, nu patru).
