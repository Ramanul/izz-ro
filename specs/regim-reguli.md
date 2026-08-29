# Regimul regulilor — inventar, conflicte, armonizare, gestionare

> **Ce e:** auditul complet al tuturor regulilor proiectului (2026-08-29), conflictele găsite cu
> dovadă, și propunerea de regim care face tăierile inutile. **Nimic din el nu e implementat** —
> e spec, conform §5.1. Proprietarul confirmă ce se construiește.
>
> **De ce acum:** pe 2026-08-06 tăierea lui `CLAUDE.md` a pierdut 13 reguli fără ca nimic să
> semnaleze. Verificarea a costat o sesiune întreagă de arheologie pe git. `CLAUDE.md` e azi la
> 23.920/24.576 octeți — **97,3%** — deci următoarea regulă adăugată forțează următoarea tăiere.
> Problema nu e plafonul. E că nimic nu știe câte reguli avem.

## 1. Inventarul măsurat

**28 de purtători de reguli, 272 de enunțuri normative.** Numărate mecanic (bullets și liste
numerotate peste 25 de caractere), nu estimate.

| strat | fișiere | ce sunt |
|---|---|---|
| **Contract canonic** | `CLAUDE.md` (69 enunțuri, 23.920 o.) | se încarcă la FIECARE tură |
| **Contracte de rol** | `AGENTS.md` (22), `.claude/agents/README.md` (10) | executanți non-Claude, sub-agenți |
| **Normativ de domeniu** | `REGULI-SINTEZA.md` (13) | titluri/rezumate — `process.py` trebuie să-l implementeze |
| **Arhive normative** | `specs/masuratori-frontend.md` (2), `specs/istoric-operational.md` (9) | reguli mutate din CLAUDE.md, încă în vigoare |
| **Stare + reguli permanente** | `specs/STATE.md` (9) | 3 reguli „nu le repara" trăiesc doar aici |
| **Agenți** | 4 fișiere (29) | `clustering-tuner`, `editorial-guard`, `frontend-auditor`, `pipeline-runner` |
| **Comenzi** | 8 fișiere (72) | `/slice`, `/audit`, `/handoff`, `/delegate-*`, `/review-*` |
| **Injectate în context** | `.claude/hooks/session-start.sh` | mandatul + §12a + STATE.md + registrul, la fiecare pornire |
| **Aplicare mecanică** | `tests/test_reguli.py`, `.claude/settings.json`, `ruff.toml`, 20 workflow-uri | singurul strat care chiar oprește ceva |
| **Uman** | `REVIEW.md` (10), `moderation.yaml` | rutina zilnică a proprietarului |
| **Registru** | `specs/registru.tsv` + `specs/registru-decizii.md` (16) | ce s-a respins și de ce |

**Cifra care contează: 5 din 272.** `tests/test_reguli.py` are 15 teste, dar doar ~5 sunt gărzi
reale pe starea repo-ului (plafon CLAUDE.md, plafon STATE.md, TTL sincronizat, unicitatea unui
plafon, harta §21). Restul testează garda. **Sub 2% din reguli au un mecanism care le ține.**
Exact regulile fără mecanism sunt cele 13 pierdute pe 2026-08-06.

## 2. Conflicte găsite — ordonate după consecință

### K1. §16.3 interzice o verificare care se poate face — MĂSURAT AZI

`CLAUDE.md §16.3` spune că o sesiune remote **NU poate** ajunge la site și trebuie să cadă pe
„rămâne de confirmat pe live". Măsurat acum, `bash tools/verify_allowlist.sh`:

```
[BLOCAT DE PROXY] izz.ro                             CONNECT refuzat
[BLOCAT DE PROXY] www.izz.ro                         CONNECT refuzat
[OK]              izz-ro.andifreelancer2.workers.dev HTTP 200 (a raspuns originea)
```

Originea Worker servește site-ul real: 130.391 octeți, 195 de carduri, conținut din
2026-08-28T21:09Z. **Deci starea a treia e accesibilă din remote** — prin originea Worker, nu prin
`izz.ro`. Registrul o știe (`IZZ-0247`: allowlist-ul e PER-HOST), `CLAUDE.md` nu. Costul: fiecare
sesiune remote raportează „neconfirmat" pentru o verificare pe care o putea face.
**Caveat de consemnat în regulă:** originea Worker se publică prin `deploy-worker.yml`, care e
manual — poate rămâne în urmă cu un ciclu față de `izz.ro`.

### K2. Arhiva contrazice regula vie despre cadență

`specs/istoric-operational.md` §17: „**cron `13 */2` — la fiecare 2 ore**".
`build.yml:24` și `CLAUDE.md §17`: `13 * * * *` + poartă de 105 minute.
Arhiva e citată explicit din §17, deci o sesiune trimisă acolo primește cifra greșită — exact
eroarea pe care §17 spune să n-o mai re-diagnosticheze.

### K3. `§N` e un spațiu de nume folosit de două documente

`CLAUDE.md` și `REGULI-SINTEZA.md` numerotează amândouă `§1…§8`. În cod, uneori se spune al cui,
uneori nu:

| loc | ce scrie | e clar al cui? |
|---|---|---|
| `generator/guard.py:43` | „§7 din CLAUDE.md" | explicit |
| `generator/raport_copiere.py:3` | „§2.2 din REGULI-SINTEZA.md" | explicit |
| `generator/process.py:503` | „§2.2 (drept de autor)" | **ambiguu** |
| `generator/htmlart.py:21` | „tokenurile din styles.css (§8)" | **ambiguu** |

21 de fișiere trimit la „§7" fără să spună al cui document.

### K4. `TITLE_MAX_WORDS = 22` vs. prompturi care cer „6-16 cuvinte"

`REGULI-SINTEZA.md §6` declară nepotrivirea ca fiind „de decis" — din 2026-08-17, nedecisă. În
plus trimite la `config.py:230`; valoarea e la `config.py:306`. Un document normativ care își
consemnează propria contradicție și o lasă deschisă nu mai e normativ.

### K5. Trei canale de anunț concurente

`CLAUDE.md §14`: anunțul se scrie în `TASKS-B.md` + `specs/STATE.md`.
`COORD-DASHBOARD.md:7`: „intenția se anunță pe [issue #83] **ÎNAINTE** de a atinge fișiere".
`CLAUDE.md` nu pomenește issue #83 deloc (0 apariții). Fiecare fișier crede că e canalul.

### K6. §12b descrie o allowlist care nu există

§12b: „comenzile documentate de dev/build/lint/test nu cer confirmare". `.claude/settings.json`
conține **zero** intrări pentru `pytest` sau `ruff` — exact cele două comenzi pe care §4 le
documentează ca fiind canonice. Lipsesc și `git fetch`/`git pull`, cerute de §15.

### K7. §21 descrie invers relația cu `tools/log_slice.py`

§21: „`COORD-DASHBOARD.md` — **citit** de `tools/log_slice.py`, deci nu se mută."
`tools/log_slice.py:25`: `REPORT = .../COORD-DASHBOARD.md` — îl **generează și îl suprascrie**.
Concluzia („nu se mută") rămâne corectă; motivul scris e pe dos.

### K8. `.claude/commands/audit.md` trimite la o ancoră moartă

„The «before» baseline is the «Current scores» line in `CLAUDE.md §13`." Linia aia a fost mutată
în `specs/masuratori-frontend.md` pe 2026-08-06. Comanda nu mai are baseline.

### K9. `/slice` lărgește §10

`slice.md`: „…touches clustering/synthesis/legal/deploy config (**§10**)". §10 nu conține
clustering — clustering e §7. Comanda inventează o interdicție pe care contractul nu o are.

### K10. Regula anti-pierdere-de-date nu-l leagă pe Claude

`AGENTS.md` interzice categoric `git restore` / `git checkout --` / `git stash` / `git clean` /
`git reset` pe fișiere pe care nu le-ai creat („această regulă există fiindcă era să fie încălcată
pe 2026-07-18"). `CLAUDE.md`: **zero** apariții. Cea mai dură regulă anti-distrugere din repo îi
leagă pe executanți, nu pe manager — deși §19 documentează chiar incidentul cu agentul care a
mutat ramura de sub toți.

### K11. `COORD-DASHBOARD.md` e stătut de 5 săptămâni și e citat ca fapt

Generat 2026-07-25, ultimul slice raportat 2026-07-25; azi e 2026-08-29. `CLAUDE.md §19` citează
de acolo „sub-agenții costă ~5,6× per linie livrată" ca măsurătoare. Cifra vine din **3 slice-uri
cu agent**, toate dintr-o zi, un singur cont — iar fișierul însuși avertizează că raportul e vechi
când datele diferă.

### K12. `REVIEW.md` descrie un regim încheiat

„Lansare soft (primele 7 zile)" — proiectul are peste două luni. „Build-ul următor aplică
schimbarea în câteva minute" contrazice §17 (~2h). `README.md:36` trimite cititorul acolo.

### K13. Regula mandatului e duplicată fără gardă

`.claude/hooks/session-start.sh` hardcodează mandatul („cerut: X. Fac: Y."); `CLAUDE.md §0` are
propria versiune. Două copii, niciun mecanism care să le țină sincronizate.
`test_reguli.py::test_fiecare_plafon_e_declarat_intr_un_singur_loc` face fix asta — dar numai
pentru **cifre**, nu pentru text de regulă.

### K14. Cele 13 reguli pierdute pe 2026-08-06

Consemnate separat (audit 2026-08-29): 8 obligații reale + 5 întăriri, dispărute din tot repo-ul.
Nu se repetă aici; sunt clasa pe care regimul de mai jos o face imposibilă.

## 3. Armonizare — ce se repară și cum

Trei clase, cu tratament diferit. **Nu se atinge nimic din §10** (sinteză/atribuire, legal, deploy)
fără confirmare separată.

**A. Corecții de fapt (diff mic, verificabile azi) — 7 conflicte**

| # | fix |
|---|---|
| K1 | §16.3: „remote NU poate" → „`izz.ro`/`www` sunt blocate de proxy; **originea Worker răspunde 200** și e calea de confirmare, cu `?cb=`; verifică de fiecare dată cu `tools/verify_allowlist.sh`, nu din memorie" + caveatul de prospețime |
| K2 | `istoric-operational.md` §17: `13 */2` → `13 * * * *` + poartă 105 min, cu trimitere la §17 ca sursă unică |
| K4 | REGULI-SINTEZA §6: se decide 22 vs. 6-16 (propunere: 6-16 e ținta din prompt, 22 e plasa de siguranță — se scrie explicit așa) + linia corectă `config.py:306` |
| K6 | `.claude/settings.json`: se adaugă `pytest`, `ruff check`, `git fetch`, `git pull` — sau §12b se rescrie ca să nu mai promită ce nu e configurat |
| K7 | §21: „citit de" → „generat de `tools/log_slice.py`, deci nu se mută și nu se editează manual" |
| K8 | `audit.md`: baseline-ul → `specs/masuratori-frontend.md` |
| K9 | `slice.md`: „(§10)" → „clustering (§7) / sinteză, legal, deploy (§10)" |

**B. Decizii de proprietar (nu le iau eu) — 3**

- **K5** — care e canalul de anunț: `TASKS-B.md`+`STATE.md`, sau issue #83? Cel care pierde se
  șterge din fișierul lui, nu rămâne ca alternativă tăcută.
- **K11** — `COORD-DASHBOARD.md` se regenerează (`log_slice.py --report`) și se reia jurnalul, sau
  se îngheață explicit și §19 citează cifra cu „n=3, iulie 2026"?
- **K12** — `REVIEW.md` se actualizează la regimul de azi sau se marchează istoric și `README.md`
  trimite în altă parte?

**C. Reparate de regimul din §4, nu punctual — 4**

K3 (ambiguitatea `§N`), K10 (regula lipsă la manager), K13 (duplicat fără gardă), K14 (regulile
pierdute). Astea nu se repară cu un diff, fiindcă se vor reproduce. Vezi mai jos.

## 4. Regimul propus — patru straturi

Scopul e explicit: **nu «fără tăieri niciodată», ci «nicio tăiere care pierde ceva tăcut», plus un
buget care nu se mai umple.**

### 4.1 Identitate stabilă: ID de regulă, nu poziție

**Cauza rădăcină a tot ce e mai sus:** regulile sunt identificate prin *poziție* (`§13`), iar
poziția se schimbă la fiecare rescriere. De-aia `audit.md` trimite în gol, de-aia `§N` se ciocnește
între două documente, de-aia 13 reguli au dispărut fără să pice nimic.

Fiecare regulă primește un ID stabil, scris ca ancoră în linia ei:

```markdown
- **Fără output stricat.** `[R-014]` Pipeline-ul nu publică niciodată titluri brute…
```

Codul, agenții, comenzile și hook-ul citează **`R-014`**, nu `§7`. Secțiunile rămân doar
organizare vizuală și pot fi rearanjate liber. Cost: ~10 octeți per regulă (~700 pe tot L0).

### 4.2 Registrul de reguli — `specs/reguli.tsv`

Aceeași formă care a mers deja pentru decizii (`registru.tsv`), pentru același motiv: proza nu se
poate interoga.

```
id	sursa	sectiune	stare	garda	text_scurt
R-014	CLAUDE.md	7	activa	test:test_render_editorial	fara output stricat — sare itemul
R-041	CLAUDE.md	16	activa	doar-scrisa	masoara, nu deduce
R-052	—	—	retrasa	—	tura ultrathink (retrasa 2026-08-06, motiv: …)
```

Generat cu `tools/reguli.py sync` din ancorele `[R-nnn]`. Face două lucruri:

1. **Răspunde la „câte reguli avem și care s-au pierdut" cu un `diff`**, nu cu arheologie pe git.
   Munca de azi devine o comandă.
2. **Permite garda din 4.4:** o regulă care dispare din fișier dar are rând `activa` în registru →
   CI roșu: *„R-041 a dispărut din CLAUDE.md. Dacă e intenționat, treci-o `retrasa` cu motiv."*

Asta nu împiedică tăierea. Împiedică **pierderea tăcută** — singura problemă reală.

### 4.3 Trei niveluri de cost, nu un plafon unic

Plafonul de 24 KB e corect ca instrument, dar e aplicat pe un singur nivel, deci singura supapă e
tăierea. Regulile au însă frecvențe de utilizare foarte diferite:

| nivel | unde | ce intră | criteriu mecanic |
|---|---|---|---|
| **L0** | `CLAUDE.md` | reguli care schimbă acțiunea următoare **în orice tură** | se aplică la >1 tură din 5 |
| **L1** | skills / agenți / comenzi, cu declanșator | reguli condiționate de ce atingi | se aplică doar la o clasă de fișiere |
| **L2** | `specs/` + registru | cifre, istoric, ipoteze picate | se consultă, nu se respectă |

Tăierile de până acum au mutat **arhiva** din L0 în L2. Mișcarea următoare e alta: **regulile
condiționate din L0 în L1** — și L1 n-a fost niciodată folosit ca strat gândit, deși infrastructura
există (`.claude/agents/`, `.claude/skills/`, `.claude/commands/`).

Candidați măsurați, din L0 de azi: §13 front-end (1.069 o.), §17 cadență (1.011), §18 imagini
(1.204), §20 registru (928), §12a inventar de unelte (1.650) — **~5,9 KB**, adică 25% din fișier,
toate condiționate de un declanșator clar. Mutate ca skill-uri cu `description` care declanșează
automat, L0 coboară la ~18 KB și **regulile ajung mai des la sesiune decât acum**, fiindcă vin
exact când sunt relevante, nu diluate în 24 KB citite superficial.

### 4.4 Fiecare regulă își declară garda

Coloana `garda` ia una din patru valori:

- `test:<nume>` — un test o impune (plafoane, harta §21, TTL, atribuire)
- `ci:<workflow>` — un workflow o impune
- `hook` — e injectată în context la pornire
- `doar-scrisa` — nimic n-o ține

Și atunci întrebarea „cât de solid e sistemul de reguli" devine un `awk`: **azi, ~5 din 272 au
gardă mecanică.** Regulile `doar-scrisa` sunt exact populația din care s-au pierdut cele 13.

**Regula de aur care rezultă, și singura pe care o propun ca obligatorie:**
*o regulă nouă intră doar dacă îi numești garda.* Dacă e `doar-scrisa`, primește ID și rând în
registru, dar merge în L1/L2 — nu ocupă buget L0.

### 4.5 Ce se schimbă în `test_reguli.py`

Trei gărzi noi, aceeași formă ca cele existente:

1. `test_fiecare_regula_activa_exista_in_fisierul_ei` — anti-pierdere tăcută (K14).
2. `test_fiecare_trimitere_R_are_tinta` — orice `[R-nnn]` citat în cod/agenți/comenzi există și e
   `activa` (K3, K8).
3. `test_textul_duplicat_intre_hook_si_CLAUDE_md_e_identic` — extinde unicitatea de la cifre la
   text de regulă (K13).

## 5. Ce NU rezolvă asta

- Nu face regulile corecte — doar trasabile. O regulă greșită cu ID rămâne greșită.
- Nu înlocuiește citirea. `L0` tot trebuie citit; regimul doar îl ține mic destul cât să fie citit.
- Nu recuperează ce s-a pierdut înainte de ID-uri. Cele 13 reguli se repun manual, o singură dată.
- Costă o felie de construit (`tools/reguli.py` + 3 teste + ancorele) și o trecere de adnotare pe
  cele 272 de enunțuri. Adnotarea e mecanică și se poate delega.

## 6. Criterii de acceptare (dacă se aprobă)

- [ ] `python tools/reguli.py sync` produce `specs/reguli.tsv` cu ≥ 250 de rânduri, fiecare cu `garda`.
- [ ] `python tools/reguli.py find <subiect>` întoarce regula și garda ei în ≤ 5 rânduri.
- [ ] Ștergerea unei reguli `activa` din `CLAUDE.md` face CI roșu, cu ID-ul în mesaj.
- [ ] `CLAUDE.md` ≤ 18 KB după mutarea în L1, cu zero reguli `activa` pierdute (verificat prin `diff` pe registru, nu prin citire).
- [ ] Cele 13 reguli pierdute pe 2026-08-06 sunt repuse sau marcate `retrasa` **cu motiv**.
