# 2026-08-16, 11:47 (cont A) — a doua zi pe item 3: metrica reparată a ajuns în CI, două citiri din trei

> Sesiune de continuare, pornită de la un raport de dimineață. Nu s-a scris niciun rând de cod.
> Tot ce urmează e măsurătoare + un commit docs-only (`77471838`).
> Jurnalul precedent care contează: `2026-08-15-2326-inventar-taskuri-calculator-gresit-si-a1-revenit.md`.
> Commit-urile de context, de azi-dimineață, deja descrise în mesajele lor: `b6d856b7`, `991fa74e`.

## Punctul de plecare

Item 3 din `specs/STATE.md` („Model C is not batched") are o poartă proprie: **nu se decide
batching-ul până nu se citește `stats["deferred"]` pe 2-3 rulări reale**. Poarta fusese, ea însăși,
stricată — `deferred` aduna două mărimi opuse — și s-a reparat azi-dimineață în `b6d856b7`, cu o a
doua corecție în `991fa74e` (plafonul comparat trebuia să fie `ai_budget - upgrade_reserve`).

Ce nu se știa la începutul sesiunii: dacă reparația a apucat să ruleze în CI. Ultimul build citit
rulase pe `2c776929`, adică *înainte* de ea.

## Ce s-a măsurat

`gh run list --workflow build.yml` + `gh run view <id> --log`, filtrat la sursă pe liniile de raport
(§19 — nu se trage logul întreg în context).

**Rulările `build.yml` de azi, cu SHA-ul lor:**

    31934693614  e36d8b92  07:45:20Z  7s       -> sarita de poarta de cadenta
    31932736726  23f807e7  06:59:05Z  13m34s   -> BUILD REAL, a doua citire
    31929665943  23f807e7  05:43:10Z  5s       -> sarita de poarta
    31927569381  991fa74e  04:50:10Z  15m37s   -> BUILD REAL, PRIMA citire cu metrica reparata
    31923719511  2c776929  03:13:05Z  6s       -> inainte de reparatie (cel citit ieri)

Deci **da**, reparația a ajuns în CI: `31927569381` a rulat pe `991fa74e`. Durata scurtă (5-7s) e
semnătura porții de cadență (105 min), nu un eșec.

**Cele două citiri curate:**

    rulare         citite   noi   B   C   apeluri   amanate   fara substanta
    31927569381      386     68  44   5    10/18       0            19
    31932736726     1387    152  11  17    18/18      84            24

## Ce spun cifrele

**`31927569381` închide aritmetic în ambele direcții**, deci e o citire în care am încredere mare:
5 apeluri pentru clusterele C + `ceil(44/10)` = 5 loturi B = **10** = `ai_calls` raportat; și
19 respinse + 44 B + 5 C = **68** = `new`. Presiune pe buget: zero (10 din 18).

**Capcană de citire, notată ca să nu piardă nimeni o oră pe ea:** la `deferred: 0` **nu se
tipărește nicio linie** — `_print_report` are `if stats.get("deferred"):`, care e fals la 0. Absența
liniei „Amanate" *este* zeroul. Nu e un build vechi, fără reparație.

**`31932736726` e cazul opus și numește levierul exact.** Din cod (`generator/main.py:154-171`):
clusterele C se procesează **primele** și costă **un apel fiecare**; B merge în loturi de
`BATCH_SIZE = 10`. Cu 17 clustere C → 17 din cele 18 apeluri, a mai încăput exact un lot B de 10,
și 84 de iteme au trecut la rularea următoare. Confirmare independentă a ordinii: mostra de 12
articole din raport e **12/12 model C** (`processed_new[:12]`), fiindcă C se adaugă primul în listă.

Contrafactual, pe cifrele acelei rulări: C în loturi de câte 3 → 6 apeluri în loc de 17, rămân 12
apeluri pentru B = 120 de sloturi, adică **amânarea ar fi fost zero**.

## De ce decizia NU s-a luat, deși pare limpede

Trei motive, în ordinea greutății:

1. **Cele două citiri se contrazic** (0 vs 84) și diferă de **3,6× la volumul citit** (386 vs 1387).
   Explicația simplă „C mănâncă bugetul, cronic" are o rivală la fel de simplă: „build-ul de la
   06:59 recupera un vârf". A treia citire e exact ce separă cronicul de episodic. Poarta item-ului
   cere 2-3 rulări; sunt 2.
2. **`CLAUDE.md` §10** pune logica de sinteză Model C pe lista „a nu se atinge fără instrucțiune
   explicită". Măsurătoarea se poate termina autonom; modificarea nu se poate începe.
3. Batching-ul la C nu e același lucru cu cel de la B: B rescrie articole independente, C sintetizează
   multi-sursă cu atribuire (§7). Un prompt cu N clustere deodată riscă contaminare între ele — sinteza
   clusterului A citând surse din B. Ar cere contract de ieșire strict + verificare per cluster.
   *(interpretare, nu măsurătoare — nu s-a testat nimic în direcția asta)*

`python tools/registru.py find batching` → **0 rânduri**. Nu e o re-litigare; subiectul e nou în registru.

## Două defecte de instrument, găsite și NEreparate deliberat

- **`deferred: 0` nu tipărește nimic** (mai sus). Pentru o decizie care se ia comparând loguri între
  rulări, „absent" și „zero" arată identic. O linie de cod + un test.
- **`>> Fara substanta: 23` vs `Respinse DEFINITIV (fara substanta): 24`**, în aceeași rulare
  (`31932736726`). Numitori diferiți: prima se tipărește în `process_new`, *după* ce sursele oficiale
  au fost scoase; a doua se calculează în `run()` pe lista întreagă. Deci un item oficial era sub
  pragul de substanță. Nu e un bug de calcul, e două cifre care arată ca aceeași cifră.

**Nereparate pentru că se schimbă instrumentul între citirea 2 și citirea 3.** Nu ar corupe comparația
(prima doar *adaugă* o linie unde nu era niciuna), dar e exact obiceiul care strică o măsurătoare, și
§5 cere „go" oricum.

## Starea la final

- `specs/STATE.md` item 3: actualizat cu ambele citiri, mecanismul, și ce trebuie să stabilească a
  treia — commit **`77471838`**, docs-only, pushat pe `main`. `main` local == `origin/main`.
- **Supraveghere armată** (`Monitor`, task `bro21ob7x`, persistent): script
  `scratchpad/astept-citirea-3.sh`, verifică `build.yml` la 2 minute, iese la primul build real SAU
  la primul build eșuat, și raportează separat porțile de cadență care sar. La 08:46:45Z a raportat
  deja o poartă sărită (`31937319979`) — corect, poarta se deschide pe la 08:57Z.
- Așteptarea: cron la `:13`, deci build real probabil la **09:13Z**, cifra pe la **09:26Z**.

## Ce urmează, pentru cine prinde firul

1. Citește a treia măsurătoare (`Buget AI:` / `Amanate (` / `Respinse DEFINITIV` din log).
2. Dacă amânarea e >0 și cu buget epuizat și pe a treia → presiunea e cronică, propunerea de batching
   la C merge la proprietar **ca propunere**, cu §10 citat.
3. Dacă e 0 → presiunea e episodică, iar levierul ieftin (bugetul de apeluri, `MAX_AI_CALLS_PER_RUN`)
   se discută înaintea oricărei atingeri a sintezei.
4. Oricum ar ieși: **nu se scrie cod pe Model C fără „go" explicit.**
