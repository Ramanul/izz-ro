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

> **F1 LIVRAT 2026-08-29.** Cele 7 corecții de fapt din tabelul A sunt aplicate, iar cele 13 reguli
> pierdute sunt repuse — **fiecare la nivelul ei**, nu toate în `CLAUDE.md`, fiindcă nu încăpeau:
> 934 de octeți necesari contra 656 disponibili. Zece au intrat în `CLAUDE.md` scrise concis, restul
> în sateliți (`specs/masuratori-frontend.md`, `specs/registru-decizii.md`,
> `.claude/commands/slice.md`). Ca să încapă, trei bucăți de arhivă pură au fost mutate din
> `CLAUDE.md` în `specs/istoric-operational.md` — inclusiv antetul care conținea cifra greșită
> „~11 KB" și §21 care conținea „82 KB / treisprezece", ambele corectate acolo cu valorile
> măsurate. Rezultat: **24.390/24.576 octeți, 186 liberi**, toate gărzile verzi.
>
> Ce dovedește felia asta: F1 a consumat aproape tot bugetul rămas doar ca să repare și să repună.
> Nicio regulă nouă nu mai încape fără F4. Ordinea F2 → F3 → F4 rămâne cea propusă în §4.

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

### 4.1 + 4.2 — LIVRATE ALTFEL în #227. Planul de mai jos a fost măsurat și abandonat.

**Cauza rădăcină rămâne valabilă:** regulile sunt identificate prin *poziție* (`§13`), iar poziția
se schimbă la fiecare rescriere. De-aia `/audit` trimitea în gol, de-aia `§N` se ciocnește între
două documente, de-aia 13 reguli au dispărut fără să pice nimic.

**Ce propunea planul inițial:** o ancoră `[R-nnn]` în fiecare regulă, plus `specs/reguli.tsv`
generat de un `tools/reguli.py` nou.

**De ce a picat, măsurat în #227, nu presupus:** 70 de enunțuri × 8 octeți = **560 de octeți** în
`CLAUDE.md`, care după F1 are **186 liberi** din 24.576. Ancorele nu încap, iar ridicarea
plafonului ca să încapă niște ancore ar inversa exact scopul exercițiului.

**Ce s-a livrat în loc:** amprenta e **capul îngroșat al regulii** — numele ei — care costă zero
octeți fiindcă e deja scris. Censul celor 47 de reguli cu nume stă ca `frozenset` în
`tests/test_reguli.py`, nu într-un fișier nou: **zero registre noi**, într-un proiect a cărui
boală e că adevărul stă în prea multe locuri. Ca o regulă să dispară din `CLAUDE.md` trebuie
ștearsă și din test — act vizibil, în același diff, văzut de același reviewer.

Două consecințe de reținut, ambele deliberate:

- **Garda merge într-un singur sens** — prinde dispariția, nu apariția. O regulă nouă se vede
  oricum în diff. Efectul practic: nicio ordine de aterizare a două PR-uri nu face CI roșu pe
  merge-ul altcuiva.
- **O reformulare a numelui pică garda.** Intenționat: numele unei reguli e identitatea ei.
  Consecință operațională, valabilă acum: **editează corpul unei reguli cât vrei, dar nu-i
  schimba capul îngroșat** fără să actualizezi censul în același commit.

### 4.3 Trei niveluri de cost, nu un plafon unic

Plafonul de 24 KB e corect ca instrument, dar e aplicat pe un singur nivel, deci singura supapă e
tăierea. Regulile au însă frecvențe de utilizare foarte diferite:

| nivel | unde | ce intră | criteriu mecanic |
|---|---|---|---|
| **L0** | `CLAUDE.md` | reguli care schimbă acțiunea următoare **în orice tură** | se aplică la >1 tură din 5 |
| **L1** | skills / agenți / comenzi, cu declanșator | reguli condiționate de ce atingi | se aplică doar la o clasă de fișiere |
| **L2** | `specs/` + registru | cifre, istoric, ipoteze picate | se consultă, nu se respectă |

Tăierile de până acum au mutat **arhiva** din L0 în L2. Mișcarea următoare e alta: **regulile
condiționate din L0 în L1**. Candidații, măsurați pe fișierul de azi: §13 front-end (1.069 o.),
§17 cadență (1.011), §18 imagini (1.204), §20 registru (928), §12a inventar de unelte (1.650) —
**~5,9 KB**, un sfert din fișier, toate condiționate de un declanșator clar.

#### Ce transportă L1 — REPLANIFICAT 2026-08-29, după ce premisa inițială a picat

Versiunea inițială a paragrafului ăstuia spunea: mută-le ca agenți cu `description` care se
aprinde automat. **Fals, măsurat în #227** (`IZZ-0252`), pe amândouă jumătățile:

- `description`-ul unui agent e injectat în promptul de sistem la **fiecare tură**, verbatim
  identic cu fișierul de pe disc — deci mutarea acolo economisește **zero octeți**;
- corpul agentului (2,0-2,7 KB) chiar e deferat, dar se încarcă **doar la spawn**, iar spawn-ul e
  o decizie a modelului, nu un mecanism: zero rulări ale celor patru agenți în șapte săptămâni.

Deci §13 mutat în `frontend-auditor` **ar dispărea**, nu s-ar declanșa. Aia e chiar eroarea din
6 august, cu alt ambalaj.

Din cele patru mecanisme măsurate, două transportă efectiv o regulă:

| mecanism | se aprinde singur? | cost/tură | verdict |
|---|---|---|---|
| `description` de agent | e deja în context mereu | plin | economisește zero (`IZZ-0252`) |
| corp de agent | doar la spawn, decis de model | 0 | regula dispare (`IZZ-0252`) |
| `CLAUDE.md` imbricat pe director | mecanic, dar **doar** pe `Read`/`Edit`/`Write` | 0 | real, orb la `cat`/`sed` (`IZZ-0253`) |
| **hook `PostToolUse`** | **mecanic, pe orice unealtă** | 0 | **ăsta e L1** (`IZZ-0254`) |

**Deci L1 = hook `PostToolUse` cu filtrare pe cale**, nu agent. Patru lucruri de respectat, toate
măsurate în #227, nu deduse:

1. Hook-ul trebuie să iasă cu **`exit 2` și să scrie pe `stderr`** — `exit 0` + `stdout` **nu
   ajunge la model**. Un hook care doar face `echo` pe succes e invizibil, deci regula nu sosește.
2. Trebuie pus în **`.claude/settings.json`** (comis), ca hook-ul `SessionStart`.
   `settings.local.json` e în `.gitignore` — un hook de acolo nu există pentru nimeni altcineva.
3. Brațul pe `Bash` e potrivire de subșir pe textul comenzii, deci **supra-declanșează**: un
   `ls templates/` aprinde §13 deși e o citire. De acceptat conștient sau de îngustat în script.
4. `CLAUDE.md` imbricat rămâne util ca al doilea strat, dar **nu singur**: o sesiune care citește
   cu `cat`/`sed`/`grep` nu-l aprinde niciodată.

**Supra-declanșarea de la punctul 3 se acceptă — decis 2026-08-29.** Asimetria decide, nu gustul:
un `ls templates/` care aprinde §13 costă ~1 KB de context degeaba, o dată; un filtru strict care
ratează felia care chiar schimba front-end-ul costă o regulă neaplicată — exact eșecul pe care tot
regimul îl previne. Prima greșeală e mică, măsurabilă și reversibilă; a doua e invizibilă până
face pagubă. Deci brațul pe `Bash` rămâne larg, iar dacă zgomotul devine o problemă reală, se
îngustează **atunci**, cu o măsurătoare a cât de des se aprinde degeaba — nu preventiv.

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

### 4.5 Ce s-a schimbat efectiv în `test_reguli.py`

Livrat în #227: **15 → 33 de teste.** Patru gărzi de fapte canonice (secțiuni, constante, cron,
căi) plus censul celor 47 de reguli cu nume, fiecare cu testul ei de auto-verificare care dovedește
că garda chiar poate să pice. A găsit drift real la prima rulare: `handoff.md:64` trimitea la un
`sessions/README.md` inexistent.

Ce **nu** acoperă, spus explicit ca să nu pară protecție mai largă decât e:

- Gărzile prind **citate cu sintaxă proprie** — `§7`, `NUME = 22`, un cron sau o cale în
  backtick-uri. Proza liberă („cadența e la două ore") rămâne neacoperită. Aceeași limită ca la
  garda de TTL — știută, nu scăpată.
- Censul acoperă doar `CLAUDE.md`. **Nu e extins la sateliți**, și de-aia: măsurat, `AGENTS.md`
  are 22 de enunțuri dar **2** capete îngroșate — censul ar acoperi 2 din 22 și ar sugera o
  protecție inexistentă. Convenția `- **Nume.**` ține doar în `CLAUDE.md`. **Consecință: cele trei
  reguli pe care F1 le-a mutat în sateliți sunt, azi, neprotejate.**

## 5. Ce NU rezolvă asta

- Nu face regulile corecte — doar trasabile. O regulă greșită, cu nume, rămâne greșită.
- Nu înlocuiește citirea. L0 tot trebuie citit; regimul doar îl ține mic destul cât să fie citit.
- **Nu acoperă sateliții.** Vezi §4.5 — trei reguli repuse de F1 stau azi în afara censului.
- Nu prinde proza liberă, doar citatele cu sintaxă.

## 6. Unde suntem — 2026-08-29

| felie | ce e | stare |
|---|---|---|
| **F1** | 7 corecții de fapt + 13 reguli repuse | **livrat**, #226 fuzionat |
| **F2** | gărzi de fapte canonice | **livrat**, #227 (draft, verde) |
| **F3** | censul celor 47 de reguli cu nume | **livrat**, #227 |
| **F3.5** | dovada declanșatorului | **livrat**, #227 — a ucis premisa lui F4 |
| **F4** | mutarea în L1 | **replanificat pe hook** (§4.3), nestartat |

**Criterii pentru F4, când se face:**

- [ ] Hook-ul e în `.claude/settings.json` comis, iese cu `exit 2` + `stderr`, și e dovedit că
      mesajul chiar ajunge la model — nu presupus din faptul că scriptul a rulat.
- [ ] `CLAUDE.md` scade sub 20 KB, cu **zero** capete de regulă dispărute din cens.
- [ ] Fiecare regulă mutată își poartă limita cunoscută scrisă lângă ea (supra-declanșarea pe
      `Bash`, orbirea la `cat`/`sed`).
- [ ] Se mută **o singură secțiune** ca pilot, măsurată înainte/după, înainte de restul.

## 7. Ipoteze picate în cursul auditului — a nu se redeschide

- **`#D6AD33` din `templates/base.html` NU e un drift față de `--gold`.** L-am raportat greșit ca
  încălcare de §8 pe 2026-08-29. Comentariul de deasupra liniei explică: e valoarea plată care
  reprezintă auriul **metalic** (gradient) din iconițe, iar `<meta name="theme-color">` și
  manifestul nu pot referi un gradient. Nu e o culoare hardcodată în locul unui token — e o
  categorie pe care tokenul n-o poate exprima. **Nu-l „repara".**
