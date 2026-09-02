# Eficientizarea regulilor — analiză integrală și propuneri

> Măsurat 2026-09-02, sesiune **remote** (Linux, `/home/user/izz-ro`), pe `origin/main` la zi.
> Cerere: eficientizare **fără** pierdere de eficacitate, armonizare, flexibilitate, calitate.
> Continuă `specs/regim-reguli.md` (regimul L0/L1/L2) — nu îl înlocuiește.

## 0. Ce s-a verificat în plus față de auditul din 09-02 dimineața

Cele patru puncte lăsate atunci ca neverificate, acum închise:

| punct | verdict măsurat |
|---|---|
| 21 workflow-uri CI (~106 KB) | **cost zero în context** — nu se încarcă niciodată la model. Sunt *gardă*, nu *regulă*. Cele care aplică reguli pe PR: `tests.yml` (ruff+pytest), `semgrep`, `codeql`, `claude-code-review`, `gemini-review`, `visual`, `smoke` |
| `.claude/agents/` + `.claude/commands/` | citite; trimiterile `§` sunt valide **cu o excepție** (vezi P6). Frontmatter-ul lor **se injectează la fiecare tură**: 1.925 + 1.689 octeți |
| `~/.vibe/AGENTS.md` | **nu există în sesiunea remote** — e doar pe mașina locală. Idem `~/.claude/CLAUDE.md` (globalul de 32 KB): absent aici |
| `specs/regim-reguli.md` (341 linii) | citit integral. Regimul e deja proiectat și F1-F3.5 livrate; F4 e pilot livrat pe §13 |

Consecință directă: **raportul de dimineață (`notes/audit-reguli-2026-09-02.md`) nu există în repo** —
a fost scris pe mașina locală și n-a fost comis. Nu e citabil de aici.

## 1. Bugetul real de pornire — MĂSURAT AZI, în octeți

Toate cifrele din `stat -c %s` și din rularea efectivă a hook-ului, nu din memorie.

| strat | octeți | % | are plafon cablat? |
|---|---:|---:|---|
| `CLAUDE.md` | 23.835 | 65,7% | **DA** (24.576, `test_reguli.py`) |
| hook `SessionStart` (rulat, ieșire reală) | 8.829 | 24,3% | **NU** |
| ├─ mandat + §12a rezumat | 665 | | nu |
| ├─ `specs/STATE.md` | 4.369 | | DA (~40 linii, în antetul lui) |
| └─ registru, `tail -24` cu motiv | 3.712 | | **NU** |
| frontmatter agenți (4 + README) | 1.925 | 5,3% | **NU** |
| frontmatter comenzi (8) | 1.689 | 4,7% | **NU** |
| **TOTAL** | **36.278** | 100% | **78% acoperit** |

≈ 9.100 tokeni de reguli/stare, înainte ca sesiunea să facă ceva.

**[FAPT] Plafonul de 24 KB păzește 66% din suprafață.** Restul de 12.443 octeți (34%) nu e numărat
de nimeni și crește singur: `tail -24` din registru se îngroașă pe măsură ce se adaugă decizii.

## 2. Primele principii — de unde derivă tot restul

1. **F1.** Orice „regulă", indiferent de fișierul în care stă, ajunge în același loc: fereastra de
   context a sesiunii. Fișierul e ambalaj; contextul e resursa.
2. **F2.** Textul intrat în context la pornire rămâne acolo toată sesiunea. Nu există „descărcare".
3. **F3.** Deci o **mutare** dintr-un fișier de pornire în alt fișier de pornire economisește **zero**.
4. **F4.** Economisește doar ce **nu mai intră deloc** în sesiunile care n-au nevoie: ștergerea unui
   duplicat, compresia, sau livrarea condiționată de un declanșator mecanic.
5. **F5.** Singurul declanșator mecanic măsurat care aprinde o regulă la costul ei doar când e
   nevoie e hook-ul `PostToolUse` (`IZZ-0254`, verificat în #229).

### Criteriul de aur care rezultă

> O mișcare e eficientizare doar dacă textul **nu mai intră în context** în sesiunile care nu-l
> folosesc. Orice altceva e reorganizare, și trebuie declarată ca atare.

**Trei capcane care arată ca economie și nu sunt** (toate trei ar fi trecut neobservate):

| mișcare | economie reală | de ce |
|---|---|---|
| `CLAUDE.md` → hook `SessionStart` | **0** | ambele intră la pornire (F3) |
| `CLAUDE.md` → `description` de agent | **0** | e în promptul de sistem la fiecare tură (`IZZ-0252`) |
| `CLAUDE.md` → corp de agent | „economie" 100%, dar **regula dispare** | corpul se încarcă doar la spawn; 0 spawn-uri în 7 săptămâni (`IZZ-0252`) |

**Autocritică:** prima capcană era exact propunerea pe care voiam s-o fac (mută §12a din `CLAUDE.md`
în hook-ul care oricum îl rezumă). Ar fi arătat ca −1,6 KB și ar fi fost −0. O scriu ca să nu fie
re-propusă de altă sesiune.

## 3. Propuneri — ordonate după raport câștig/risc

### P1. Plafonul se mută de pe fișier pe **bugetul de pornire** — structural, cel mai important

**Problema:** garda numără un fișier (23.835 din 24.576) în timp ce 12.443 de octeți la fel de
scumpi nu-s numărați de nimeni. Asta face posibilă „economia fictivă" din §2: muți în hook, garda
zice verde, contextul e identic.

**Fixul:** `test_reguli.py` primește o gardă care însumează: `CLAUDE.md` + ieșirea reală a lui
`session-start.sh` + frontmatter-ul din `.claude/agents/*.md` și `.claude/commands/*.md`, contra unui
plafon declarat **într-un singur loc** (aceeași convenție ca plafoanele existente).
Valoare propusă: **40 KB** (azi 36.278 → 3.722 liberi, marjă ~10%).

**De ce 40 și nu 36 sau 48:** 36 ar fi plafon-la-zid, adică orice regulă nouă cere întâi o tăiere —
exact presiunea care a produs pierderea tăcută din 6 august. 48 e prea slab ca să constrângă ceva.
40 lasă loc pentru ~4 reguli noi înainte de următoarea discuție de buget.

**Risc:** ieșirea hook-ului e variabilă (registrul crește, STATE.md se rescrie) → testul poate deveni
instabil pe schimbări care n-au legătură cu regulile. **Mitigare:** garda rulează hook-ul o dată și
compară suma; dacă instabilitatea devine o problemă reală, se îngustează atunci, cu o măsurătoare —
nu preventiv (aceeași logică ca supra-declanșarea acceptată în `regim-reguli §4.3`).

**Câștig:** nu octeți, ci imposibilitatea de a raporta o economie care nu există. Ăsta e câștigul
care ține în timp.

### P2. Plafonează injecția registrului — 3.712 octeți, cea mai mare economie reală

`session-start.sh:62-66` injectează `tail -24` din deciziile închise, **cu motivul trunchiat**.

**[OPINIE] Motivul trunchiat la ~200 de caractere e mai rău decât absent:** dă senzația că știi de ce
s-a respins, fără să știi. Semnalul util e „există o decizie pe subiectul ăsta, caut-o", și el încape
în ID + titlu + status.

**Propunere, în două variante:**
- **(a) agresivă:** doar `ID · dată · status · titlu` → estimat ~1.500 o., **economie ~2.200**.
- **(b) calibrată — recomandată:** motivul rămâne **doar** pentru `masurat-fals` (astea induc activ
  în eroare: sunt lucruri care *par* adevărate), tăiat pentru `respins/anulat/abandonat` (acolo
  titlul + `registru.py find` ajung). Economie estimată ~1.200-1.500.

**De ce (b) și nu (a):** `masurat-fals` e categoria care a costat cel mai mult istoric — o sesiune
care re-descoperă o ipoteză deja infirmată pierde o zi. Titlul singur nu previne asta, fiindcă
ipoteza *sună* plauzibil; motivul e antidotul. La `respins`, în schimb, decizia e a proprietarului
și titlul e suficient ca semnal de „nu redeschide".

**Risc:** o sesiune care nu face `find` pierde contextul unei respingeri. **Contraexemplu unde P2 e
greșită:** dacă se dovedește că sesiunile *nu* rulează `registru.py find` (verificabil în transcripturi),
atunci injecția e singurul canal, iar tăierea ei reintroduce re-litigarea. **Nu propun P2 fără
verificarea asta.**

### P3. Șterge duplicatul mandatului — ~600 octeți, zero pierdere

Mandatul „cerut: X. Fac: Y." e integral în **două** locuri care intră **amândouă** la pornire:
`CLAUDE.md §0` (~700 o. din 1.579) și hook (665 o.). Se plătește de două ori, în aceeași sesiune,
pentru zero câștig de conformitate.

**Fix:** corpul rămâne în hook (vine primul, e prima linie citită — poziție mai puternică); în
`CLAUDE.md §0` rămâne capul de regulă cu numele **exact** (censul îl vede) plus o linie.

**Capcana de evitat, verificată:** hook-urile Claude **nu rulează** pentru executorii non-Claude
(Devin, OpenCode, Mistral). Am verificat `AGENTS.md`: mandatul **nu e acolo**. Deci mutarea în hook
l-ar face să dispară pentru ei. **Condiție de livrare: rândul intră simultan în `AGENTS.md`** (unde
costă doar la ei, nu în fiecare tură Claude).

### P4. A doua secțiune în L1 — §18 imagini (1.490 o.), condiționat

Pilotul §13 a mers. Următorul candidat, ales pe criteriu, nu pe mărime:

| secțiune | octeți | declanșator mecanic pe cale? | verdict |
|---|---:|---|---|
| **§18** imagini instituții | 1.490 | **da**: `tools/fetch_leadphotos.py`, `tools/fetch_portraits.py`, `generator/render.py` | **candidatul** |
| §17 cadență | 1.085 | slab: `build.yml`, dar cazul real („pipeline-ul e picat") e **conversațional** | nu |
| §12a inventar unelte | 1.650 | **nu** — se aplică la începutul oricărui task | nu |
| §16 verificare în două roluri | 2.770 | nu — orice schimbare vizibilă | **rămâne L0** |

**De ce §18 și nu §17 (cea mai mare tentație):** §17 se activează exact când *nu* atingi niciun
fișier — cineva spune „nu s-a publicat nimic de 4 ore". Un hook pe cale ratează fix cazul principal.
Mutată acolo, regula ar dispărea în scenariul ei propriu.

**Cu cârlig obligatoriu:** în `CLAUDE.md` rămâne un rând („imaginile instituțiilor: doar cu una din
cele 3 dovezi consemnate → `.claude/reguli/18-imagini.md`"), fiindcă §18 are și o componentă
conversațională (proprietarul propune o poză). Economie netă ≈ 1.270 o., **condiționată** de
P(sesiunea nu atinge zona de imagini).

**Precondiție de onestitate:** înainte de P4, verifică pe transcripturi reale că hook-ul §13
**chiar s-a aprins** de la pilot încoace. Dacă nu s-a aprins niciodată, §13 e o regulă *dispărută*,
nu mutată — și P4 ar repeta greșeala din 6 august cu ambalaj nou.

### P5. Frontmatter-ul agenților — 1.925 octeți/tură pentru 0 rulări în 7 săptămâni

Descrierile celor 4 agenți se injectează la fiecare tură (`IZZ-0252`). Rulări măsurate atunci: zero.

| opțiune | economie | ce se sacrifică |
|---|---:|---|
| (a) șterge 2 agenți (`frontend-auditor`, `pipeline-runner`) | ~840 | dublate oricum de `/audit` și §5.4 — dar pierzi paralelismul |
| **(b) scurtează toate descrierile la ≤120 o.** | **~1.200** | precizia declanșării: descrierea **e** mecanismul prin care modelul îi cheamă |
| (c) nu face nimic | 0 | — |

**[OPINIE] (b), și nu (a):** flexibilitatea cerută explicit înseamnă să nu tai capacități, ci costul
lor. (a) închide o ușă; (b) o lasă deschisă mai ieftin.

**Contraargumentul tare, pe care îl accept parțial:** dacă tai descrierea, agentul devine invizibil
și rulările rămân zero — doar că acum din vina ta. **Răspuns:** păstrează în cele ≤120 de octeți
exact declanșatorul (`cluster.py`, `templates/`, „does it still build?"), taie justificarea
(„Read-only: it measures and reports a verdict, it does NOT edit code") — aia e o regulă pentru
agent, deci locul ei e în **corpul** agentului, care se încarcă la spawn, unde chiar contează.

### P6. Drift real găsit — se repară acum, e mic

`.claude/agents/frontend-auditor.md:23` trimite la „`CLAUDE.md` §13 (»Current scores«)". **Dublu
moartă:** §13 nu mai e în `CLAUDE.md` (e `.claude/reguli/13-frontend.md`), iar „Current scores" nu
mai există nicăieri în afară de citarea asta — baseline-ul e în `specs/masuratori-frontend.md`.

Garda de trimiteri (`test_fiecare_cale_citata_exista`, `test_fiecare_trimitere_la_sectiune_are_tinta`)
acoperă **doar `CLAUDE.md`** — de-aia n-a prins-o. **Fix dublu:** corectează linia **și** extinde
garda la `.claude/agents/*.md` + `.claude/commands/*.md`.

## 4. Ce NU propun, deliberat

- **Nu propun „`CLAUDE.md` sub 20 KB" ca obiectiv.** Ținta din `regim-reguli §6` e țintită pe fișier,
  iar §2 arată de ce e o măsură greșită a lucrului care contează. Cu P1, obiectivul corect devine
  „bugetul de pornire sub plafon, cu 100% acoperire de gardă". Ajungerea sub 20 KB pe fișier ar cere
  mutarea lui §12a și §17, adică exact cele două fără declanșator mecanic: le-ar dizolva.
- **Nu propun tăierea lui §16** (2.770 o., cea mai mare secțiune). E cea mai scumpă și cea mai
  justificată: se aplică la orice schimbare vizibilă, iar istoricul ei e un bug raportat „rezolvat"
  în timp ce proprietarul îl vedea în continuare.
- **Nu propun plafon pentru `~/.claude/CLAUDE.md`** din sesiunea asta: nu există aici, deci n-am
  măsurat nimic azi. Recomandarea de acum trei ture rămâne validă, dar e o muncă de făcut pe mașina
  locală, cu cifrele de acolo.

## 5. Trei perspective

**Optimistă.** Regimul e deja proiectat și pilotul funcționează; P1+P6 sunt o zi de muncă și închid
gaura structurală (34% din suprafață nesupravegheată). P2+P3+P5 dau ~3-3,3 KB fără să șteargă nicio
regulă. Sistemul devine primul din proiect cu buget *complet* măsurat.

**Pesimistă.** ~5 KB economisiți ≈ 1.300 de tokeni ≈ sub 1% dintr-o sesiune. Fiecare mecanism nou e o
piesă care poate tăcea — hook-ul a murit deja o dată tăcut (`set -e`, 2026-08-23). Riști să adaugi
fragilitate pentru un câștig sub pragul de zgomot, în timp ce costul dominant (output de unelte, §19)
rămâne neatins.

**Inginerească (recomandarea).** Fă **P1 și P6** — sunt câștig structural, nu de octeți, și nu depind
de nicio ipoteză nemăsurată. Fă **P3** (duplicat curat, cu condiția `AGENTS.md`). Fă **P5(b)**.
**Nu face P2 până nu verifici** dacă `registru.py find` chiar se rulează, și **nu face P4 până nu
verifici** că hook-ul §13 chiar s-a aprins. Ordinea contează: P1 primul, fiindcă e garda care face
restul măsurabil.

## 6. Expertul rival — și răspunsul, punct cu punct

> „Optimizați bugetul greșit. Costul dominant nu sunt cei 36 KB de reguli, ci output-ul uneltelor:
> un `git log` nefiltrat sau `data/articles.json` depășesc de zece ori tot bugetul de reguli. Faceți
> micro-optimizare pe 1% și ignorați 60%."

1. **Corect ca ordin de mărime** — și e chiar motivul pentru care §19 există. Concesie reală.
2. **Dar nu e același tip de cost.** Cele 36 KB sunt **prefix**: în fiecare cerere a sesiunii. Un
   `git log` mare e într-una singură și iese din atenție. Persistența schimbă socoteala.
3. **Argumentul principal nu e economia, e atenția.** [INTERPRETARE] 36 KB de reguli e deja peste ce
   citește atent un om; presupunerea că un model le respectă uniform e nemăsurată — și istoricul
   proiectului (13 reguli pierdute tăcut, un fix raportat greșit ca rezolvat) sugerează că nu.
4. **Concesie practică:** garda din P1 ar trebui extinsă, într-o felie ulterioară, ca să numere și
   **bugetul de unelte** per sesiune. Acolo e cei 60% — iar rivalul are dreptate că acolo trebuie
   mers după.

## 7. Condiții în care analiza asta e greșită

- **Dacă se măsoară conformitatea** și e la fel de bună la 36 KB ca la 24 KB → argumentul de atenție
  cade, rămâne economia de ~1%, care nu justifică efortul. **Nu am putut măsura asta.**
- **Dacă hook-ul §13 nu s-a aprins niciodată** → L1 nu e un strat, e o groapă; P4 devine periculoasă
  și §13 trebuie readus în L0.
- **Dacă prompt caching acoperă prefixul la ~10% din cost** → economia monetară a lui P2/P3/P5 e a
  zecea parte din cea nominală; rămâne doar argumentul de atenție.
- **Dacă `registru.py find` nu se rulează în practică** → P2 devine dăunătoare, nu neutră.
- **Dacă apar mai mulți executori non-Claude** → orice regulă mutată în hook trebuie dublată în
  `AGENTS.md`, iar economia scade proporțional.

## 8. Contraexemple la regula generală „mută regulile condiționate în L1"

- **§7 „fără output stricat"** *pare* condiționată (doar pipeline), dar se aplică și unei decizii de
  design luate în conversație, fără nicio atingere de fișier. Mutată, ar dispărea exact acolo.
- **§16** pare cea mai bună țintă (e cea mai mare), dar declanșatorul ei e „orice schimbare vizibilă
  utilizatorului" — adică aproape tot. Mărimea nu e criteriu; **specificitatea declanșatorului este.**
- Regula nu e universală și nici nu trebuie să fie: **`regim-reguli §4.4` o spune deja mai bine** —
  o regulă intră unde îi poți numi garda.

## 9. Autoevaluare

**7,5/10.** Ce ține cifra sub 10:

- Toate cifrele de dimensiune sunt măsurate azi, aici (`stat`, rularea reală a hook-ului) — pe astea
  am încredere ~9,5/10.
- **Nu am putut măsura conformitatea** (dacă un fișier mai mic chiar produce respectare mai bună).
  E ipoteza pe care se sprijină jumătate din valoarea propunerilor și rămâne [INTERPRETARE].
- **Nu am verificat dacă hook-ul §13 s-a aprins vreodată** în sesiuni reale — n-am acces la
  transcripturile de pe mașina locală. De-aia P4 e condiționată, nu propusă direct.
- „0 rulări ale agenților în 7 săptămâni" e **citat din `IZZ-0252`**, nu re-măsurat azi.
- Comportamentul cache-ului pentru textul injectat de hook la mijlocul sesiunii e **inferență**, nu
  măsurătoare.
- Estimările de economie pentru P2 și P5 sunt calculate pe eșantion, nu pe implementare — pot să
  iasă cu ±30%.

**Cel mai slab punct al raționamentului:** presupun că „mai puțin text = mai bună respectare" fără
s-o fi măsurat vreodată în proiectul ăsta. Dacă e falsă, tot regimul L0/L1/L2 e efort pentru 1%.
**Unde aș greși cel mai probabil:** în estimarea economiei de la P2 — depinde de cât de lung e
motivul mediu, iar eu am măsurat suma, nu distribuția.

## 10. Addendum — măsurat accidental în timpul scrierii raportului (2026-09-02)

Comanda care a scris fișierul ăsta a **aprins hook-ul L1**: §13 a sosit în context, deși raportul e
un `notes/*.md` și nu atinge front-end-ul. S-a declanșat pe subșirurile `templates/` și
`generator/render.py` din **textul** raportului, prin brațul `Bash` (potrivire pe comandă).

Două lucruri se schimbă din asta, amândouă măsurate, nu deduse:

- **Precondiția lui P4 e ÎNDEPLINITĂ.** Hook-ul `PostToolUse` chiar livrează regula la model, în
  sesiune remote, la cald. §13 e o regulă *mutată*, nu dispărută. P4 nu mai e blocată de verificarea
  aia — rămâne condiționată doar de cârligul din L0.
- **Supra-declanșarea are acum un cost măsurat: 1.445 octeți, într-o sesiune cu zero atingeri de
  front-end.** Cazul „scrii *despre* reguli" nu fusese anticipat în `regim-reguli §4.3` — acolo
  exemplul era `ls templates/`. Decizia din 08-29 (se acceptă) rămâne corectă pe asimetrie, dar
  clasa de fals pozitiv e mai largă decât se credea: orice document care **citează** căi o aprinde.

  [OPINIE] Nu propun îngustarea filtrului. Un fals pozitiv de 1,4 KB pe o sesiune de audit e exact
  prețul pe care decizia din 08-29 l-a acceptat conștient; îngustarea ar cere excluderea căilor
  citate în heredoc-uri, adică parsare de shell — complexitate mult peste paguba.
