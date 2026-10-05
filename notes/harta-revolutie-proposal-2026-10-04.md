# Harta știrilor — revoluție, nu retuș

**Data:** 2026-10-04 · **Tip:** studiu + propunere, **fără implementare** · **Autor:** sesiune Arena (agent),
branch `arena/01a10582-izz-ro`, plecat din `0c01b21`
**Cerere:** diagnostic pe trei planuri (grafic, funcțional, intuitivitate) pentru `/harta/`, apoi o propunere de
revoluție completă a experienței — altă cartografie, alt model de interacțiune, altă structură de date — cu
minim 3 direcții distincte (cost/risc/ce pierdem/dependențe), recomandare explicită și un contract de realitate.
**Constrângeri:** 0 lei, static, fără backend, fără servicii plătite; biblioteci open-source permise cu țintă de
KB mici; se păstrează regulile site-ului (numai localizări determinate, Zero Zgomot, exactitatea UAT).

> **cerut:** studiu + propunere, fără implementare, livrat ca document + PR fără merge.
> **fac:** citesc harta ca produs (cod, date, capturi, istoric), măsor ce se poate măsura pe starea comisă,
> reproduc pe live defectul dovedit, scriu propunerea în `notes/` și o deschid în PR.
> **nu fac:** nicio linie de cod de produs, nicio schimbare în `main`, niciun refactor oportunist.

**Stările de dovadă folosite în document** (aceleași trei ca în `CLAUDE.md` §16.4, plus una proprie):
**citit** = am citit fișierul/linia; **măsurat** = am rulat o comandă și am cifra; **captură** = am privit
imaginea din `notes/harta_diag/`; **confirmat pe live** = am cerut URL-ul public prin intermediar în această
sesiune. Ce nu am putut verifica e marcat `[NEVERIFICAT]` cu motivul.

---

## 0. Metoda și ce am putut verifica

### 0.1 Ce am citit (complet)

| Ce | Unde |
|---|---|
| pagina | `static/harta-stiri/index.html` (96 linii) |
| stilul | `static/harta-stiri/harta-stiri.css` (116 linii / 13.629 B) |
| motorul | `static/harta-stiri/harta-stiri.js` (2.148 linii / 102.400 B) |
| datele | `static/harta-stiri/data/map.json` (394.064 B), `static/harta-stiri/data/uat/*.json` (42 fișiere, 2,4 MB) |
| generarea | `tools/build_harta_data.py`, `tools/build_harta_uat.py`, `generator/mini_harta.py`, `generator/render.py` (1794-1820) |
| gardurile | `tools/harta_dom_check.py` (1.010 linii), `tools/harta_contrast.py`, `tests/test_harta_*.py` (6 fișiere) |
| istoricul | `specs/harta-felia4-7-design.md`, `specs/harta-imbunatatiri-2026-08-14.md`, `specs/registru.tsv` (IZZ-0176…IZZ-0422), `notes/harta_diag/FINDINGS-2026-09-12.md`, `notes/harta-imbunatatiri-cititor-2026-10-03.md` |
| regulile | `CLAUDE.md` (§0, §4, §5, §7, §8, §10, §14b, §16, §17), `AGENTS.md`, `REVIEW.md` |
| ramura | `origin/feat/harta-vizibilitate` (comparație de arbori) |

### 0.2 Ce am măsurat, cu ce

| Măsurătoare | Comanda (prescurtat) |
|---|---|
| structura și statisticile datasetului | `python3 -c "json.load(open('static/harta-stiri/data/map.json'))"` |
| greutatea pe componente (raw + gzip) | `gzip -c … \| wc -c` |
| volumul unui click pe județ (fișierele UAT ale vecinilor) | reimplementarea lui `neighborCountiesFor` în Python peste `map.json` + `du` pe `data/uat/` |
| mărimile de ecran (px) ale textului și liniilor | calcul din `praguriFor`/`drawUats` (unități viewBox) × scara canvasului la 1440/1024/390 px |
| contrastul și L* | calcul WCAG + CIE L* pe valorile reale din CSS |
| legenda degenerată | simulare în `node` a lui `praguriFor`+`updateLegend`, apoi **confirmare pe live** |
| denominatorul de populație | `data/localities.json` (3.179 localități, toate cu `pop`) + împerecherea cu `data/uat/*.json` (3.085/3.186 = 96,8 %) |
| dimensiunile capturilor | citirea antetului PNG (fără dependențe) |

### 0.3 Ce NU am putut verifica (onest)

- **Nu am rulat pagina într-un browser real în acest sandbox.** Playwright nu se poate instala (fără acces la
  `cdn.playwright.dev`, `pip` fără `--break-system-packages`), iar Chromium nu are bibliotecile de sistem
  (`libnspr4.so` lipsește; `apt-get update` e blocat de rețea). Deci: **toate cifrele de pixel sunt calculate,
  nu capturate** — și sunt marcate ca atare. Comenzile care au eșuat sunt în §6.
- **`curl` către `izz.ro` e blocat** din container (SSL_ERROR_SYSCALL pe CONNECT — aceeași situație ca în
  `notes/harta-imbunatatiri-cititor-2026-10-03.md`). Verificările „live" din document sunt făcute prin
  intermediar (redare de pagină), nu prin rețeaua sesiunii.
- **Nu am Putut citi istoricul ramurii** `feat/harta-vizibilitate`: clona e superficială, fără bază comună cu
  `main` (`fatal: no merge base`), deci nu pot data commit-urile sau vedea PR-ul. Am comparat **arbori**, nu istorii.
- Nu am rulat `pytest` (lipsește pytest în mediul de sistem) și nu am regenerat `map.json`: propunerea nu schimbă date.

---

## 1. DIAGNOSTIC

### 1.1 Harta de azi, în cifre (măsurat pe starea comisă, `0c01b21`)

| Fapt | Cifră |
|---|---|
| articole pe hartă / evenimente | **662 / 648** |
| fereastra temporală reală | **22 sept → 4 oct (12 zile)**; 282 articole pe 2 oct, 190 pe 3 oct, 1 pe 4 oct |
| articole de backfill (până la 14 zile vechime) | **194 (29 %)** |
| articole fără coordonate (doar județ) | **227 (34 %)** — 222 fără nicio localitate |
| articole cu UAT determinat | 402 (61 %) |
| niveluri de încredere | `text` 307 · `source` 249 · `siruta` 106 |
| surse distincte | **291**; evenimente cu >1 sursă: **28** (max 4 surse, max 5 relatări) |
| județe cu știri | 41 din 42 (Satu Mare: 0) |
| localități confirmate | 175 |
| județul cel mai încărcat / cel mai gol | Timiș 55 · Satu Mare 0 |
| geometrie | 42 contururi de județ (Natural Earth) + 3.186 poligoane UAT (geo-spatial.org / ANCPI) |
| transfer prima vizită | **504 KB raw / 126 KB gzip** (79 % din el e `map.json`) |
| un click pe un județ, rețea | **16 cereri / 603 KB raw median / 1.086 KB maxim** (Alba), adică ~180-312 KB gzip |

Harta funcționează, e accesibilă și e (parțial) onestă — dar **arată ca un prototip de inginer, nu ca un
produs de presă**, și măsoară ceva ce nu spune. Mai jos, pe cele trei planuri cerute.

### 1.2 Cartografie — nu există un sistem, există patru hărți în patru limbi

Site-ul are patru reprezentări cartografice, fiecare cu alt limbaj vizual și altă paletă
(`citit`: `templates/index.html:58-68`, `templates/surse.html:14-22`, `templates/_art.html:44`, `static/faza2.css:7-15`, `static/styles.css:690-703`):

| Unde | Ce e | Paletă | Text/etichete | Interactiv |
|---|---|---|---|---|
| `/static/harta-stiri/` (harta mare) | canvas 2D, 2.148 linii JS | rampă proprie `#f2f0e8…#7a5a10`, accent `#b58b18` | desenat în canvas, `sans-serif` generic | da |
| prima pagină („România în ultimele 24 h") | SVG static, zero JS | `--gold-wash` → `color-mix(--gold 45 %)` → `color-mix(--gold 78 %)` → `--gold-strong` (`#faf5e6/#e4d090/#d4b451/#8b6918`) | niciun text pe harta | doar link |
| `/surse/` | SVG static cu `<a>` pe județ | `--gold-wash` / `--gold-strong` / `--line` | `<title>` la hover | linkuri |
| coperțile de articol | silueta județului ca decor | paleta `art--p0..p5` | niciun text | nu |

Consecința măsurabilă: **aceeași scară h0–h4 are două rampe diferite** pe același site. Aceeași treaptă h3 e
`#c2911c` (L\* 63) pe hartă și `#d4b451` (L\* 74) pe prima pagină — 1,42:1 între ele, adică două nuanțe care
spun cititorului „altă cantitate". Iar pagina hărții nu încarcă **niciun** asset al brandului
(`măsurat`: pagina referă exact 3 fișiere — favicon, CSS-ul și JS-ul hărții; zero `styles.css`/`faza2.css`,
zero font Playfair), deși `CLAUDE.md` §8 spune că stilul derivă din `static/styles.css`. Rezultatul se vede în
capturi: titlul „Harta știrilor" e sans-serif greu, în timp ce tot restul site-ului folosește Playfair Display
(`static/styles.css:43`). **Harta nu e o pagină de presă; e o aplicație lipită de un site de presă.**

### 1.3 Culoare — trepte inegale, legendă care minte, contur desenat în culoarea fundalului

**Rampa h0–h4 de pe hartă** (`măsurat`, L\* și contrast WCAG):

| treaptă | culoare | L\* | ΔL\* față de treapta anterioară | contrast vs. alb |
|---|---|---|---|---|
| h0 (0 știri) | `#f2f0e8` | 94,7 | — | 1,14:1 |
| h1 | `#f1e3b6` | 90,3 | **4,4** | 1,28:1 |
| h2 | `#e4c46a` | 80,2 | 10,1 | 1,69:1 |
| h3 | `#c2911c` | 63,2 | 17,0 | 2,85:1 |
| h4 | `#7a5a10` | 40,4 | 22,8 | 6,37:1 |

ΔL\* de 4,4 între h0 și h1 e sub pragul la care două suprafețe mari alăturate se disting lejer: **toate județele
cu volum mic arată la fel**, iar treptele 3–4 sunt atât de întunecate încât eticheta de text de pe ele cade la
**2,82:1** (`#171717` pe `#7a5a10`), sub minimul de 4,5:1. Rampa nu e uniformă perceptiv: primele două trepte
sunt o non-informație, ultimele două sunt o prăpastie.

**Conturul** (`citit`: `harta-stiri.css:26` + `harta-stiri.js:1105`): linia interioară e `--map-inner: #ffffff`
pe un canvas care se umple tot cu `--surface: #ffffff` → **1,00:1**. Granița dintre două județe fără știri e
desenată exact în culoarea fundalului. Pe mobil, cu `lineWidth` de 1,2 unități viewBox, acea linie are
**0,43 px CSS** (vezi tabelul de mai jos), deci dispare complet. Nu e o problemă de gust: e o eroare de sistem.

**Legenda minte, literal.** `praguriFor(max)` (linia 567) produce praguri = cuartele volumului *vizibil*, iar
`updateLegend` (577) își construiește etichetele ca `p[0]+1 …  p[1]`. Când maximul vizibil e ≤ 3, `praguriFor`
întoarce un tablou mai scurt de 3 și etichetele devin `NaN`/`undefined`. **Confirmat pe live** (4 oct 2026),
`https://izz.ro/static/harta-stiri/?q=Giroc` afișează, în pagina publică:

```
Volum de știri    0    1    2–undefined    NaN–undefined    NaN+
```

Nu e un colț teoretic: e o căutare obișnuită („Giroc", 2 rezultate, ambele în Timiș). Iar problema e
structurală, nu doar la extreme: pentru max = 55 (starea națională de azi) etichetele sunt
`0 / 1–12 / 14–27 / 28–41 / 42+` — **valoarea 13 nu apare în nicio treaptă**, fiindcă pragul în sine e mereu
sărit de formula `p[i]+1`. Adică granița dintre trepte e chiar numărul pe care legenda nu-l are.

**A treia problemă de culoare: scara nu e stabilă.** Pragurile se recalculează din volumul *filtrat*
(`buildMap` → `praguriFor(maxCount)`), deci aceeași culoare înseamnă alt număr după fiecare filtru. „Maro închis"
e „55" în starea națională și „3" după o căutare. Un choropleth cu praguri mobile nu e o scară, e o impresie.

**Modul regional** are o a treia ramă de culoare (7 pastile) ale cărei valori stau toate în intervalul
L\* 84–90: Transilvania `#cddccd` și Banat `#e3d3e6` au **1,00:1** între ele (identice perceptiv), iar toate
cele 7 au sub 1,6:1 față de alb. Se vede în captura `notes/harta_diag/national_regional.png`: șapte nuanțe
pastelate aproape indistincte.

### 1.4 Tipografie și etichete — text de 3–7 px, fără așezare, în alt font

Tot ce e text pe hartă e desenat în **canvas**, cu `sans-serif` generic, în **unități viewBox** (8 u pentru
numele UAT, 11 u pentru cifrele din pastile, 13 u pentru regiuni). Unitățile viewBox nu sunt pixeli de ecran:
scara depinde de lățimea canvasului. Rezultatul (`măsurat`, calculat):

| element | unități | desktop 1440 px (canvas ~910 px) | desktop 1024 px (~600 px) | **mobil 390 px (~361 px)** |
|---|---|---|---|---|
| cifra din pastilă (max) | 11 u | 10,0 px | 6,6 px | **4,0 px** |
| cifra, caz tipic (2-5 știri) | ~8-9,4 u | 7,3-8,5 px | 4,8-5,6 px | **2,9-3,4 px** |
| raza pastilei (max) | 14 u | 12,7 px | 8,4 px | **5,1 px** |
| numele UAT | 8 u | 7,3 px | 4,8 px | **2,9 px** |
| numele regiunii | 13 u | 11,8 px | 7,8 px | **4,7 px** |
| contur interior | 1,2 u | 1,1 px | 0,7 px | **0,43 px** |
| halo de siluetă | 3 u | 2,7 px | 1,8 px | 1,1 px |

Patru consecințe, toate vizibile în capturi:

1. **Pe mobil, harta națională nu are text** — 4 px pentru o cifră nu se citește, se ghicește. Captura
   `live_mobil_national.png` (780×27368) arată exact asta: un contur palid, apoi 120 de rânduri de listă.
2. **Numele nu au sistem de așezare.** Singura regulă e „dacă spațiul liber ≥ 7 **unități**, scrie sub pastilă"
   (`harta-stiri.js:533-537` — un prag în unități de hartă amestecat cu un font tot în unități de hartă; nu
   există niciun prag în pixeli de ecran). Nu există coliziune, prioritate, nici scalare după importanță. În
   captura de județ (`live_desktop_judet.png`) „Sânnicolau Mare" domină harta — pentru că fontul e în unități,
   iar unitățile se „măresc" când te apropii.
3. **Ierarhia se inversează la zoom.** La vederea de județ, 8 u de font devin, pe un canvas de 910 px:
   **~20 px pentru Timiș, ~44 px pentru Covasna, ~80 px pentru Ilfov, ~192 px pentru București** (`măsurat`:
   bbox-ul județului × 1,52 ca fereastră de vizualizare). Adică **județele mici primesc textul cel mai mare,
   județele mari cel mai mic** — exact pe dos față de orice convenție cartografică.
4. **Numele oficiale apar deformat.** Panoul, firul de navigare și selectorul folosesc cheia brută a hărții:
   live afișează `CARAS-SEVERIN`, `BISTRITA-NASAUD`, „Evenimente în TIMIS" (`confirmat pe live`). Există deja
   `geo.eticheta_judet()` care știe „Caraș-Severin" — nu e folosit aici.

**Costul ascuns al etichetelor** (`măsurat` prin replicarea algoritmului pe geometria reală, fără browser):
`uatBadgePlacement` (`harta-stiri.js:344-380`) caută pentru fiecare UAT cu știri un punct interior bun în
**122 de candidați** (centrul + o grilă 11×11) și, pentru fiecare candidat acceptat, trage **16 raze** cu pas de
0,8 unități până la ieșirea din poligon, fiecare pas fiind un `isPointInPath`. Pe datele de azi:
**~80.000 de interogări point-in-polygon per redraw pentru Timiș** (11 UAT-uri cu știri), 43.000-53.000 pentru
Brașov/Constanța/Cluj — iar `buildMap()` rulează la **fiecare schimbare a UAT-ului de sub cursor** și la
**fiecare cadru** al animației de 380 ms (~23 de cadre ⇒ **~1,8 milioane de interogări per fly-to**). Nimic din
toate astea nu e cache-uit: poziția pastilei se recalculează identic la fiecare redraw.

### 1.5 Ierarhie vizuală — ce e important nu se vede

- **Nimic nu e mai important decât altceva.** La nivel național, 42 de poligoane au aceeași greutate de linie,
  aceeași umplere (dacă au 0 știri), iar cifra stă în pastile albe identice (`harta-stiri.js:502-534`).
  `IZZ-0405` (13 sep, proprietar) a numit deja problema: „un marker cu 66 de evenimente și unul cu 1 au aproape
  aceeași greutate vizuală". Codul de azi a rezolvat-o prin **ștergerea** markerilor și trecerea la choropleth
  (`harta-stiri.js:1154-1156`) — corect ca principiu, dar acum *toate* cifrele se bat pentru atenție în aceleași
  pastile albe, iar cel mai important lucru (unde e știrea) nu are nicio cale de a ieși în față.
- **Numerele nu au context.** Cifra din pastilă nu spune perioada (12 zile), nici denominatorul (populație,
  număr de surse monitorizate). „Timiș 55" față de „București 49" nu spune nimic despre realitate: Timiș are
  650.533 locuitori, București 1,7 milioane — iar Timiș are 17 surse distincte care au publicat în fereastră,
  București 26 (măsurat). Harta măsoară **debitul nostru de ingestie**, iar cititorul citește „densitatea
  știrilor". Pagina o spune, în paragraful 2 („Numărul indică evenimentele sau relatările afișate, nu o
  statistică oficială a incidentelor"), dar un disclaimer nu poate repara o scară care induce altă citire.
- **Fereastra de timp nu există ca obiect.** Datele acoperă 12 zile, iar pagina nu are niciun control de timp:
  29 % din punctele de pe hartă sunt de backfill (până la 14 zile), dar arată identic cu știrea de acum două ore.
  Un cititor nu poate pune întrebarea cea mai firească: „ce s-a întâmplat, de fapt, azi?"

### 1.6 Primul click — un gest, trei efecte, zero previzualizare

Modelul de interacțiune de azi e: **orice click pe un județ = filtrează + zoomează + schimbă pagina de listă**
(`harta-stiri.js:1561-1573` → `applyState` aplică imediat, apoi `animateViewTo` 380 ms). Nu există stare de
previzualizare — deși **hover-ul pe desktop o are** (tooltip cu numele și 3 titluri, `showMapTip` linia 1757).

Dovada că modelul e greșit nu e o părere, e în cod: **dublu-click-ul trebuie să dea înapoi efectul primului
click** ca să poată zooma curat — `harta-stiri.js:835-839` salvează `prevSearch` și face `history.replaceState`
înainte de zoom, cu comentariul „primul click al gestului s-a aplicat deja ca selecție, iar al doilea a intrat pe
UAT-ul de sub cursor". Când un al doilea gest trebuie să anuleze primul, gestul primar e prea încărcat.

Pe mobil, consecința e mai dură: `pointerdown` afișează tooltipul (`harta-stiri.js:787`), apoi `click`
comite zoom-ul și filtrează. Adică **o atingere face amândouă** — previzualizare și navigare — iar cititorul
ajunge într-o hartă de UAT-uri (până la 114 poligoane) fără să fi cerut asta.

**Instrucțiunile există, dar ca text de subsol.** Pagina are 105 caractere de instrucțiune sus și **1.120 de
caractere (176 de cuvinte) în 4 paragrafe la subsol** (`măsurat`), care explică scara, zoom-ul, gesturile și
sursa geometriei. Adică exact informația care ar trebui să fie *afor- danță* (un control, un hint contextual, o
legendă vie) e livrată ca documentație de sub hartă. Pentru un cititor, asta e „harta fără instrucțiuni".

Alte două detalii de prim contact, ambele măsurate:
- **Nu există `/harta/`.** Nav-ul trimite la `/static/harta-stiri/` (`templates/base.html:76`), iar
  `/harta-stiri/` face 301 spre el (`generator/render.py:1820`). Verificat live: **`izz.ro/harta/` întoarce
  pagina de 404** a site-ului. Adică harta nu poate fi dictată, scrisă pe un ecran sau partajată cu un URL
  memorabil.
- **Pagina nu are nav, footer, canonical, `og:title` sau JSON-LD** (`măsurat`: zero apariții în HTML). Un
  cititor care ajunge din Google pe un link partajat nu poate ajunge la metodă, la corecții sau la restul
  site-ului; iar linkul partajat pe WhatsApp arată card generic (doar `og:image`, fără titlu contextual).

### 1.7 Mobilul — 361 × 254 px

Pe un ecran de 390 px lățime, canvasul are ~361 px, iar raportul viewBox (1000 × 703,53) îl face înalt de
**254 px**. Țara întreagă, cu 42 de județe și 3.186 UAT-uri, încap într-o cutie de 361 × 254, cu text de 3–4 px
(§1.4). CSS-ul de mobil (`.map-card{position:sticky;top:60px}` + `.news-panel{min-height:60vh}`,
`harta-stiri.css:113-116`) ține harta lipită sub header, iar lista alunecă peste ea — o metaforă corectă de
„sheet", dar cu un panou de listă care, prin `overflow:visible !important`, randează **toate cele 120 de
elemente** în flux (de aici captura de 27.368 px înălțime / 2,3 MB: `live_mobil_national.png`).

Nu e o harta de mobil prost desenată: e **o hartă de desktop micșorată**, pentru că tot textul și toate liniile
sunt exprimate în unități de hartă. Exact opusul a ce trebuie.

### 1.8 Funcționalități — ce nu poate face azi un cititor

Cerute explicit în temă: le iau pe rând, cu dovada că lipsesc (nu doar că nu le-am văzut):

| Ce ar vrea cititorul | Starea de azi | Dovadă |
|---|---|---|
| **linie de timp** | nu există; `published` e în date și e folosit doar ca text în listă | `grep -c "published" harta-stiri.js` → doar `dateLabel` |
| **straturi pe categorie** | nu există; `map.json` nu conține categoria editorială (doar rubrica geo: `local`/`judetean`/`regional`) | `măsurat`: `category` == `geo_level` pentru toate cele 662 de articole; `articles.json` are 11 categorii reale (sport 1.807, politic 950, economic 932…) |
| **deep-link către un eveniment** | nu există; `event_id` e în date, dar nu ajunge niciodată în URL | `urlForState()` scrie doar `nivel/mod/regiune/judet/uat/loc/q` |
| **deep-link către un județ** | există, dar pe un URL urât și fără pagină proprie (`?judet=TIMIS` pe `/static/harta-stiri/`) | `urlForState` + `/harta/` = 404 |
| **comparare între județe** | nu există; o singură vedere, un singur context | `contextName()` nu are decât selecție unică |
| **istoric** | doar Back-ul browserului pe pașii din `?q`/`?judet`; nu există „ce s-a schimbat de la ultima vizită" | `static/personalize.js` există și stochează deja `reads`, dar harta nu-l folosește |
| **descărcarea datelor** | nu există link către `map.json` (deși datele sunt publice prin construcție) | `grep "map.json" index.html` → doar `fetch`-ul din JS |
| **căutare în hartă** | există, dar într-o cutie proprie, fără legătură cu căutarea site-ului (`/cauta/`, Pagefind) | `index.html:44` |
| **„localitatea mea"** | nu există; motorul de personalizare nu e cablat pe hartă | `static/personalize.js` vs. `harta-stiri.js` |

### 1.9 Ce NU e stricat (și trebuie păstrat cu orice preț)

Onestitatea obligă: harta de azi are părți peste media pieței și o rescriere naivă le-ar pierde.

- **Contract de stare în URL** (`urlForState`/`stateFromUrl`/`applyState`, 1386-1487) cu Back/Forward corect,
  inclusiv `replaceState` la tastare. Puține hărți de presă au asta.
- **Calea accesibilă echivalentă**: selectorul de județ/UAT e HTML real, cu `aria-pressed`, ținte de 44 px,
  focus restaurat la reconstrucție (`updateCountyPicker`, 1595) — exact excepția „Equivalent" din WCAG 2.2
  SC 2.5.8 pe care spec-ul o invocă. Plus zoom din tastatură, `aria-live` pe status.
- **Onestitatea datelor**: filtrul de moderare aplicat înainte de localizare (IZZ-0422/`#419`-`#420`: 132 de
  linkuri moarte + 20 de înregistrări fără slug găsite la audit nu mai ajung pe hartă), marcaj `backfill`,
  `confidence` pe fiecare articol, refuzul de a inventa precizie („numai localizări determinate").
- **Geometria verificată**: `buffer(0)` folosit doar ca artefact metric, validarea UAT pe ray-casting
  (`tools/verifica_uat.py:117-135`), poligonul-fantomă Mărașu tratat la sursă
  (`tools/build_harta_uat.py:66`), alinierea siluetei la 0,00 px pe granița de stat (FINDINGS-2026-09-12).
- **Gardurile**: `tools/harta_dom_check.py` (1.010 linii, 18 verificări, inclusiv `gold_pixels`, `edge_tolerance_px`,
  `mobil_390`, `uat_selectie`, `breadcrumb`) și 6 fișiere de teste. Chiar dacă multe teste sunt aserțiuni pe text
  de fișier (F15 din `specs/harta-imbunatatiri-2026-08-14.md`), e o instituție care a costat luni de incidente.

### 1.10 Verdictul diagnosticului, în cinci propoziții

1. **Grafic:** harta nu are un sistem cartografic — are patru hărți cu patru palete, text desenat în unități de
   hartă (3–7 px pe ecranele reale), contur desenat în culoarea fundalului (1,00:1) și o rampă perceptiv
   neuniformă (ΔL\* 4,4 la prima treaptă, 22,8 la ultima).
2. **Funcțional:** harta știe un singur lucru (volum pe unitate administrativă într-o fereastră nedezvăluită de
   12 zile) și nu poate răspunde la niciuna dintre cele cinci întrebări firești (când, ce fel, care eveniment,
   comparativ, de la ultima vizită).
3. **Intuitiv:** un singur gest face trei lucruri, deci al doilea gest trebuie să-l anuleze; previzualizarea
   există doar pe desktop; instrucțiunile sunt 176 de cuvinte la subsol; iar URL-ul memorabil (`/harta/`) nu există.
4. **Onestitate:** cifrele sunt oneste una câte una, dar scara le minte pe ansamblu (praguri mobile, denominator
   ascuns, 29 % backfill indistinguibil, legendă care afișează `NaN` pe live).
5. **Nu e o problemă de bibliotecă.** Canvasul propriu funcționează; problema e că nu există un *sistem* deasupra
   lui. De asta revoluția se face pe model, nu pe dependențe.

---

## 2. Constrângerile care decid tot (și lecțiile pe care le respectă propunerea)

1. **0 lei, static, fără backend.** Nimic din propunere nu cere un serviciu nou: fără tile server, fără
   geocodare la cerere, fără API plătit. Toate datele necesare sunt deja în repo (§4.5, populația).
2. **Cota de fișiere.** `OUTPUT_FILE_BUDGET = 17000`, live ~17.122 fișiere la 3 oct, marjă **~2.900**
   (`notes/harta-imbunatatiri-cititor-2026-10-03.md`, măsurat atunci). Consecință: orice idee care seamănă
   650 de pagini de eveniment e moartă din start; deep-link-urile de eveniment se fac pe stare de URL (0 fișiere),
   nu pe pagini.
3. **KB mici.** Prima vizită costă azi **126 KB gzip**, iar un click pe județ până la **312 KB gzip** suplimentar
   (§1.1, §1.4). Orice propunere trebuie să scadă, nu să crească.
4. **Zero Zgomot.** Nicio reprezentare nouă nu are voie să afișeze titluri brute/trunchiate; regula rămâne a
   pipeline-ului, iar harta doar consumă `title` deja validat.
5. **Exactitatea UAT.** Localizările vin din `siruta`/UAT determinist; harta nu are voie să inventeze puncte pentru
   cele 227 de articole care există doar la nivel de județ (34 %). Orice design nou trebuie să aibă o reprezentare
   *explicită* pentru `geo_precision = județ`, nu să le ascundă sau să le aproximeze.
6. **Fix-ul de moderare rămâne sfânt** (IZZ-0422): harta afișează exact ce publică site-ul. Orice schimbare de
   schemă trebuie să păstreze `moderation.apply` înainte de localizare și testul care îl apără.
7. **Ramura `feat/harta-vizibilitate`: `[NEVERIFICAT: istoric]`, dar verificabil pe arbori.** Am comparat arborii:
   `static/harta-stiri/harta-stiri.js`, `.css` și `.html` sunt **identice** pe `origin/main` și pe ramură, iar
   capacitățile anunțate acolo (backfill per sursă, „N surse" real pe eveniment, mini-harta care citește
   `map.json`) sunt deja pe `main` (`tools/build_harta_data.py:BACKFILL_DAYS`, `generator/mini_harta.py:_counts_din_dataset`,
   `harta-stiri.js:200-210`). Restul diferenței față de `main` sunt ștergeri (fișiere care există pe `main`) —
   deci **ramura e un snapshot mai vechi al repo-ului plus commit-uri de hartă care au aterizat pe `main` pe altă
   cale.** Propunerea nu are nicio dependență de ramură; dar proprietarul ar trebui să decidă explicit dacă mai
   are valoare, ca să nu devină muncă fantomă în planificare.
8. **Lecțiile din istoric, citate ca reguli de proiectare:**
   - *Mărașu / poligonul-fantomă* (PR #393 revert): geometria de la sursă poate minți → **nu derivăm geometrie
     nouă** în revoluție; păstrăm cele două straturi verificate și schimbăm doar desenul.
   - *`buffer(0)` vs. ray-casting*: validarea nu se face pe metrici (`tools/build_harta_uat.py:473-515`,
     `tools/verifica_uat.py:117`) → orice verificare nouă (ex. alinierea etichetelor) se face **pe geometrie
     reală, nu pe bbox**.
   - *`#419`/`#420`*: 132 de linkuri moarte + 20 de înregistrări fără slug la audit → deep-link-urile noi trebuie
     să treacă prin același filtru și să nu introducă ţinte care pot 404.
   - *PR #432* (backfill 14 zile + surse unite): onestitatea se plătește — 29 % din hartă e backfill → timpul
     trebuie să fie vizibil, nu ascuns.

---

## 3. Direcții revoluționare (4 variante, cu cost/risc/pierderi/dependențe)

Toate cele patru pornesc de la aceeași constatare: **problema nu e randarea, e modelul.** Fiecare schimbă alt
lucru fundamental.

### Direcția A — „ATLASUL": substrat DOM/SVG + sistem cartografic + timp + URL-uri reale

**Model nou.** Harta rămâne pagina centrală, dar se reconstruiește ca *sistem*: geometria în SVG (DOM), etichetele
într-un strat separat în spațiu de ecran (mărime constantă, așezare cu coliziuni), un singur limbaj vizual pentru
toate cele patru hărți ale site-ului, un control de timp (24 h / 7 zile / toată fereastra) și un contract de URL
cu pagini permanente (`/harta/`, `/harta/<judet>/`). Interacțiunea devine **previzualizare → angajare**.

**Ce se schimbă concret:** `harta-stiri.js` (canvas 2D) → modul SVG de ~700-900 linii; `harta-stiri.css` →
stiluri pe elemente (nu pe canvas); `map.json` rămâne sursa de date, cu schema v5 (§4.6); fără bibliotecă
externă (argumentat în §4.1).

**Cost:** ~7-11 zile de muncă de agent, din care 2 zile garduri. **0 lei.**
**Risc:** regresie de accesibilitate dacă SVG-ul nu primește focus/aria la fel de bine ca selectorul actual;
performanță DOM la 114 poligoane + 114 etichete (risc mic, dar trebuie măsurat pe dispozitiv slab);
migrarea a ~10 fișiere de teste scrise pe text (`specs/harta-imbunatatiri-2026-08-14.md` F15).
**Ce pierdem:** fluiditatea canvasului la pan/zoom foarte rapid pe telefoane vechi (compensabil cu
`will-change`/`transform` și cu ascunderea etichetelor în timpul gestului); unele micro-optimizări de hit-test.
**Dependențe:** schema v5 în `tools/build_harta_data.py` (o zi, în echipă cu pipeline-ul); decizia de rută
pentru `/harta/<judet>/` (§4.4).

### Direcția B — „RADARUL": MapLibre GL + vector tiles + animație temporală

**Model nou.** Harta devine instrument temporal: evenimentele apar în timp real de build (o „pulsare" pe zi),
zoom continuu GPU, clustere, teren 3D opțional. Pentru asta: geometrie tăiată în vector tiles (PMTiles/`.mvt`)
și randare WebGL.

**Cost:** ~2-3 săptămâni + o unealtă nouă în pipeline (tippecanoe sau echivalent Python), plus ~220-250 KB gzip
de JS de client (față de 32 KB azi) — **de 7-8× mai mult client**.
**Risc:** WebGL absent/instabil pe Android de gamă medie (publicul site-ului), deci oricum ai nevoie de o cale
de rezervă — adică două randări de întreținut; servirii PMTiles cere fie un Worker cu range requests (zonă
protejată §10, cere decizie de proprietar), fie un CDN public (contrazice „fără servicii"); pierderea căii
accesibile actuale (MapLibre nu dă DOM per element, iar excepția „Equivalent" din WCAG s-ar pierde exact când
harta devine mai greu de navigat); politica de tile-uri: OSM raster e deja respinsă în repo (IZZ-0328).
**Ce pierdem:** accesibilitatea, printabilitatea, „Ctrl+F" pe nume de localitate, greutatea mică, simplitatea.
**Dependențe:** decizie de infrastructură (Worker/R2) + date noi de pipeline. **Nu recomand acum**, dar ea e
direcția corectă *dacă* obiectivul devine „animație spectaculoasă". Se poate decide cu date: GA4/Clarity sunt
deja instalate — se poate măsura ce procent din cititori are WebGL și memorie suficientă **înainte** de a investi.

### Direcția C — „BRIEFINGUL": inversarea ierarhiei (harta iese din centru)

**Model nou.** Harta nu mai e destinație, e instrument: pagina de județ (`/subiect/<judet>/`) și prima pagină
primesc modulul de hartă focalizat pe „zona mea", cu „localitatea mea" persistentă; `/harta/` devine pagina de
explorare pentru cei care vor să rătăcească.

**Cost:** ~5-7 zile, dar distribuite în `generator/render.py` + template-uri + `static/personalize.js`.
**Risc:** se lovește frontal de alte două lucrări deja scrise în `notes/harta-imbunatatiri-cititor-2026-10-03.md`
(#2 „Localitatea mea", #9 „pagina de județ = hub local") — dacă nu se coordonează, se construiesc două hub-uri
de județ paralele și se dublează conținutul (risc SEO + cotă de fișiere).
**Ce pierdem:** identitatea de „atlas" a site-ului și un singur loc unde harta e vedetă.
**Dependențe:** #2 și #9 din documentul de 23 de idei; motorul de personalizare existent.

### Direcția D — „INSTRUMENTUL": harta ca aparat de măsură onest

**Model nou.** Se schimbă *ce înseamnă* culoarea: scară stabilă, denominator vizibil, moduri explicite
(număr absolut / la 100.000 de locuitori / acoperire de surse / doar localizări exacte), plus comparație
între două județe pe aceeași scară și un grafic de 12 zile. Harta nu mai spune „unde sunt știrile", ci
„ce știm, cât de sigur și raportat la ce".

**Cost:** ~3-4 zile (denominatorul e **deja în repo**: §4.5), plus o zi de audit al împerecherii.
**Risc:** editorial — un număr derivat (știri/100k) poate fi citit ca judecată despre o comunitate; de aceea
modul implicit rămâne „număr absolut", iar comparațiile sunt factorizate, nu clasamente.
**Ce pierdem:** nimic din ce avem, dar câștigăm un limbaj nou de explicat (legendă, footnote, sursă).
**Dependențe:** schema v5 (denominatorul pe UAT/județ), `data/localities.json` (există), o decizie editorială
(ce se afișează implicit).

### Tabelul de decizie

| | A. Atlasul | B. Radarul | C. Briefingul | D. Instrumentul |
|---|---|---|---|---|
| Rezolvă „urât" (§1.2-1.5) | **da, structural** | parțial | nu | nu |
| Rezolvă „slab" (§1.8) | **da** (timp, straturi, deep-link) | parțial (animație) | da (local) | **da** (comparații, măsură) |
| Rezolvă „ne-intuitiv" (§1.6-1.7) | **da** | nu (altă curbă de învățare) | parțial | nu |
| KB clienți | **scade** (126 → țintă < 70 KB gzip) | crește 7-8× | neutru | +2-3 KB |
| Risc de accesibilitate | mic (se păstrează calea) | **mare** | mic | mic |
| 0 lei / static | da | da, dar cere decizie de infra | da | da |
| Zile (agent) | 7-11 | 15-20 | 5-7 | 3-4 |

### Recomandarea mea explicită

**A + D, în această ordine, cu C ca fază 3 și B respinsă acum.**

Motivul, pe scurt: cele două planuri pe care proprietarul le simte cel mai tare — „urât" și „ne-intuitiv" — sunt
consecința faptului că harta nu are un sistem (de desen, de tipografie, de interacțiune). Un sistem se
construiește pe DOM/SVG, cu etichete în spațiu de ecran și cu un singur limbaj vizual, iar asta **nu cere nicio
bibliotecă nouă** și niciun serviciu — dimpotrivă, mutarea canvas → SVG elimină ~400 de linii de hit-testing
manual și aduce înapoi accesibilitatea „gratis" (elementele devin focusabile, printabile, căutabile cu Ctrl+F).
Apoi, „slab" se rezolvă pe fond, nu pe efecte: timp, straturi, deep-link, comparație — iar toate patru se pot
livra din datele deja existente. B (Radarul) vinde senzația, dar plătește cu accesibilitatea, cu 7-8× mai mult
JavaScript și cu o decizie de infrastructură care nu e a mea; o propun aici doar ca *decizie măsurată* (Clarity/
GA4 pot spune dacă publicul suportă WebGL), nu ca plan. C e corectă, dar e altă lucrare (hub-ul de județ) și
trebuie făcută o singură dată, coordonat cu ideile #2 și #9 din documentul de 23 de idei — nu în paralel cu ele.

---

## 4. Recomandarea, pe specificație (ce s-ar construi dacă proprietarul spune „da")

### 4.1 Substratul: SVG/DOM în loc de canvas — fără nicio bibliotecă

**De ce fără bibliotecă** (răspuns direct la „altă bibliotecă de cartografie"):

| Candidat | Greutate client | Ce dă | De ce nu (acum) |
|---|---|---|---|
| MapLibre GL JS | ~220-250 KB gzip | zoom continuu, WebGL, stiluri | WebGL pe Android mediu, fără DOM per element → pierdem calea accesibilă; cere tiles/Worker |
| Leaflet | ~42 KB gzip + 15 KB CSS | pan/zoom cu inerție, pluginuri | aduce un al doilea sistem de stilizare peste brandul nostru; tiles raster sunt deja respinse (IZZ-0328); pentru poligoanele noastre pre-proiectate nu adaugă nimic esențial |
| D3 (geo/array/scale) | ~30-60 KB gzip | proiecții, scale | **nu avem nevoie de proiecție** — geometria e deja proiectată în viewBox de `tools/build_harta_uat.py`; scalele se calculează în 20 de linii |
| **niciuna (SVG + 3 module proprii)** | **0 KB nou** | exact ce ne trebuie | costul e codul propriu: ~700-900 linii, în loc de 2.148 |

**Ce câștigăm, mecanic:**
- `vector-effect: non-scaling-stroke` rezolvă într-un rând problema „0,43 px pe mobil" (§1.4): linia se
  desenează în pixeli de ecran indiferent de zoom.
- Etichetele devin `<text>`/HTML într-un strat separat → mărime constantă, fontul site-ului, halo, coliziuni
  calculate o dată per gest. Pot fi selectate, citite de cititoare de ecran și căutate cu Ctrl+F.
- Fiecare poligon devine un element focusabil cu `tabindex`, `role="button"`/`<a>` și `aria-label` — calea
  accesibilă nu mai depinde de un hit-test scris manual (care a costat IZZ-0193, IZZ-0194).
- Se șterg: `ensureCanvas`, gestionarea Pointer Events, `applyViewTransform`, `countyFillAtPoint`,
  `countyEdgeAtPoint`, `smallestUatAt`, `uatBadgePlacement`, plus re-parsarea `Path2D` la fiecare cadru de
  animație (azi: 42 de `new Path2D` + 42 de `pathBounds` pe cadru, ×23 cadre per fly-to; `măsurat` prin citirea
  lui `buildMap`).
- Pan/zoom = o singură modificare de atribut `viewBox` pe `<svg>` → compus de browser, fără JS per pixel.
- Print și „salvează ca imagine" funcționează nativ (azi canvasul se printează ca o poză).

**Ce rămâne din codul de azi** (nu se aruncă munca grea): logica de stare și URL (`urlForState`/`applyState`),
`filtered()`/`matchedLevel` (niveluri cumulative), gruparea pe evenimente (`itemsForView`), încărcarea leneșă a
UAT-urilor, filtrul de moderare aplicat în pipeline, plus toate deciziile de accesibilitate (ținte de 44 px,
`aria-live`, focus restaurat).

### 4.2 Sistemul cartografic (unul singur, pentru toate cele patru hărți)

**Rampa: 4 trepte informative + „zero știri" neutru, cu ΔL\* uniform** (`măsurat`, candidat propus):

| treaptă | culoare | L\* | ΔL\* | contrast vs. alb |
|---|---|---|---|---|
| h0 (0 știri) | `#eaecf0` (gri rece neutru) | 93,4 | — | 1,18:1 |
| h1 | `#efe3b8` | 90,2 | 10,8 | 1,28:1 |
| h2 | `#ddc36f` | 79,4 | 11,4 | 1,73:1 |
| h3 | `#c8a127` | 68,0 | 11,0 | 2,45:1 |
| h4 | `#a8841f` | 57,0 | 11,3 | 3,51:1 |

Față de rampa actuală: treptele devin **echidistante perceptiv** (~11 L\* în loc de 4,4/10,1/17,0/22,8), iar
treapta maximă rămâne luminoasă (L\* 57 în loc de 40) → textul închis pe orice umplere are ≥ 5,1:1, deci
**etichetele nu mai au nevoie de halo ca să fie citibile**.

**Reguli de culoare (verificate mecanic, se extinde `tools/harta_contrast.py`):**
1. ΔL\* ≥ 8 între oricare două trepte adiacente ale rampei.
2. Orice text desenat peste o umplere ≥ 4,5:1; orice element grafic (linie, simbol) ≥ 3:1 față de umplerile vecine.
3. Granițele nu se desenează niciodată în culoarea fundalului: fiecare poligon are contur propriu
   (hairline închis + halo deschis dedesubt, „casing" clasic), cu test automat care interzice `stroke` egal cu
   `fill`-ul canvasului.
4. Pragurile sunt **absolute** (fixe pe modul de scară), nu recalculate per filtru: aceeași culoare = același număr
   în orice stare, iar legenda se construiește *din* praguri (nu prin `p[i]+1`), cu test de proprietate pe toate
   valorile 0..60 (bug-ul `NaN` de azi devine imposibil prin construcție).
5. Modul „regional" folosește una din două soluții: fie se elimină (nu adaugă informație — 7 pastile
   indistincte), fie primește diferențiere prin **hașură + etichetă**, nu prin nuanță.

**Tipografie (scara site-ului, `--fs-*` din `static/styles.css`):**
- nume de județ/regiune: 13-14 px, `--font-display` (Playfair) sau 800 system-ui pentru UAT — o singură alegere, documentată;
- nume UAT: 11 px, doar când prioritatea îl admite;
- cifre în pastile: 12 px, tabular;
- **niciun text sub 11 px**, niciodată; pe ecrane < 420 px, se ascund etichetele și rămân pastilele (prioritate:
  județ > UAT cu ≥ 2 știri > restul).
- Așezare: prioritate după volum, plasare sub formă, respingere la coliziune (bbox) și la marginea viewport-ului;
  test automat: `getBoundingClientRect` pe fiecare etichetă vizibilă → nicio suprapunere, nimic sub 11 px.

**Linii (toate în spațiu de ecran, prin `non-scaling-stroke`):** graniță internă 1 px, chenar de selecție 2 px,
halo de siluetă 3 px.

### 4.3 Modelul de interacțiune: previzualizare → angajare

| Gest | Azi | Propus |
|---|---|---|
| hover (desktop) | tooltip cu 3 titluri | la fel + evidențierea formei |
| **tap 1** (touch) / click | filtrează + zoomează + schimbă lista | **selectează și arată** (sheet pe mobil, panou pe desktop) — fără zoom, fără rețea |
| **tap 2** pe aceeași zonă, sau butonul „Intră în județ" | — | zoom + încărcarea UAT (acum, și doar acum, cele ~600 KB) |
| dublu-click | zoom, cu anularea primului click | zoom (nu mai are ce anula) |
| Esc / „Înapoi la România" | reset | reset (păstrat) |
| tastatură | selector HTML echivalent | selector HTML + poligoane focusabile + `aria-activedescendant` |

**Straturi (chips-uri, nu meniu ascuns):** `Toate · Locale · Județene · Regionale` (există deja ca „nivel") +
**tematic** (`Sport`, `Politic`, `Economic`, `Sănătate`, … din `ai_cat`) + `≥ 2 surse` (transparența multi-sursă,
azi o linie de text în listă) + `Doar localizări exacte` (ascunde cele 227 de articole de nivel județ).
Straturile sunt radio/checkbox real, cu `aria-pressed`, și se reflectă în URL.

**Timp:** control cu trei poziții (`24 h`, `7 zile`, `toată fereastra` = 12 zile), plus un sparkline pe județ cu
volumul zilelor. **Fără promisiune de „live"**: build-ul rulează ~6 ori pe zi, cu gol median ~4 h
(`CLAUDE.md` §17) — pagina scrie „verificat la <ora>", nu „în timp real".

**Evenimentul devine obiect:** cardul unui eveniment (titluri agregate, sursele cu link, momentul, nivelul de
încredere) se deschide în panou, fără pagina nouă, iar linkul lui e `?ev=<event_id>` (0 fișiere, partajabil).

**Mobil:** hartă de ~46 vh (nu 254 px pierdute sus), etichete ascunse, pastile doar pe județele cu știri, sheet
cu două poziții (peek/full) și listă paginată **real** (20 de elemente, nu 120 în DOM).

### 4.4 Contractul de URL și SEO

| URL | Ce e | Cost |
|---|---|---|
| `/harta/` | pagina hărții (mutată de la `/static/harta-stiri/`), cu nav + footer, canonical, `og:title`, JSON-LD (`Dataset` + `Place`) | 1 fișier + 1 redirect păstrat |
| `/harta/?judet=TIMIS&nivel=local&q=…` | starea completă (compatibilă cu ce e partajat azi: `?judet`, `?uat`, `?loc`, `?q`, `?nivel`, `?mod`) | 0 |
| `/harta/?ev=<event_id>` | deep-link de eveniment (deschide cardul) | 0 |
| `/harta/<judet>/` | **opțiunea 1**: pagină proprie, 42 fișiere + 42 imagini OG (~3 % din marja de 2.900) — **opțiunea 2 (recomandată)**: 301 către `/subiect/<judet>/`, care există deja, e indexată și permanentă, iar harta se încorporează acolo ca modul (ideea #9 din documentul de 23 de idei) | 0-84 fișiere |
| `/harta-stiri/` → `/harta/` | redirect păstrat pentru linkurile existente | 0 |

Recomand opțiunea 2: zero pagini noi, zero conținut duplicat, zero risc SEO, iar harta primește pagini de județ
care există deja de luni de zile. Oglinzile OG per județ (42 imagini, generate cu `tools/gen_images.py` care
există deja) se adaugă **după** ce se măsoară partajările, nu înainte.

**Decizie de implementare F4 (manager, 2026-10-05):** cererea a fost explicită pentru URL-uri proprii
`/harta/<județ>/`, deci nu folosim redirectul recomandat mai sus către `/subiect/`. Generatorul emite 42
de pagini statice sub `output/harta/` (plus `/harta/`), cu același shell și dataset; ruta deschide harta
județului, nu o pagină editorială care s-ar putea să nu existe pentru toate codurile. Cost măsurat la build:
43 fișiere; fără pachet nou, backend sau date duplicate. Titlul, canonicalul, `og:title`/`og:description` și
JSON-LD sunt per județ; imaginea OG rămâne comună. Paginile intră în sitemap.

### 4.5 Semantica: ce măsoară harta, spus pe față

Moduri de scară, comutabile, cu legenda rescrisă pentru fiecare:

1. **Număr absolut** (implicit, compatibil cu azi) — „evenimente în fereastra aleasă".
2. **La 100.000 de locuitori** — denominatorul **există deja în repo**: `data/localities.json` are `pop` pentru
   toate cele 3.179 de localități, iar sumele pe județ se potrivesc cu INS în ±4 % (Timiș 650.533 ≈ 1,00,
   Brașov 546.615 ≈ 0,99, Cluj 679.141 ≈ 0,97, Constanța 656.016 ≈ 0,96, Ilfov 542.689 ≈ 1,09;
   `măsurat`). Pentru nivel UAT, împerecherea pe nume+label reușește în **3.085/3.186 = 96,8 %**; restul
   (sectoarele Bucureștiului + ~95 de nume cu cratime) cere un mic tabel de excepții — măsurat, nu presupus.
3. **Acoperire** — câte surse distincte au publicat în fereastră pentru fiecare județ (azi 1..26, `măsurat`).
   Atenție: NU se refolosește orbește euristica `source_county()` din `tools/build_harta_data.py` pe post de
   „surse configurate" — are fals-pozitivele documentate în IZZ-0236 (Oltenia → OLT) și e potrivire pe subsir;
   dacă modul „acoperire" se livrează, se bazează pe **numărul de surse care au publicat efectiv** (fapt din date),
   nu pe o atribuire euristică.
4. **Doar localizări exacte** — filtrul care scoate cele 227 de articole de nivel județ din numărătoare.

Fiecare mod are footnote cu sursa și data (regula site-ului, ca la ghiduri), iar cardul unui județ arată
„N evenimente · X la 100.000 · Y surse active · ultima știre la <ora>".

### 4.6 Contractul de date v5 (schiță)

`map.json` rămâne un fișier static, dar se separă pe două straturi și se codifică pe coloane:

- `geo-judete.<hash>.json` — geometria (42 contururi, ~43 KB): **imutabilă**, `Cache-Control: immutable`,
  referită cu hash (`render._asset_ver` există deja) → 0 bytes la vizitele repetate.
- `harta-<build>.json` — doar datele per articol, în forma `{keys: […], rows: [[…]]}` (dictionary encoding),
  cu: `id_eveniment`, `titlu`, `slug`, `sursă`, `categorii[]` (inclusiv `ai_cat`), `judet`, `uat`, `loc`,
  `siruta`, `x`, `y`, `precizie` (`uat|localitate|judet`), `încredere`, `publicat`, `relatări`, `surse[]`,
  `backfill`. Câmpurile `category`/`geo_level` se elimină: sunt identice azi (`măsurat`: 606/53/3 pe amândouă) —
  duplicare pură.
- `uat/<JUDET>.<hash>.json` — neschimbat ca structură, dar cu hash în nume și fără reîncărcare la fiecare
  selecție; vecinii se încarcă **la cerere vizuală** (only-if-needed), nu toți 15 deodată.

Ținta de transfer: prima vizită **< 70 KB gzip** (de la 126), vizită repetată **< 10 KB** (de la 126, fiindcă
`init()` cere azi `cache:"no-store"` — linia 2131), iar un click pe județ **< 60 KB** (de la ~180-312 KB).
Se măsoară cu `tools/greutate.py`/`tools/asset_budget.py`, care există deja.

### 4.7 Buget: fișiere, KB, zile

| Resursă | Azi | După revoluție | Notă |
|---|---|---|---|
| fișiere noi în output | — | **0** (opțiunea 2 de rută) sau 1 (`/harta/`) + 42 (OG, amânate) | marjă 2.900 |
| JS client | 102 KB raw / 32 KB gzip | ~55-70 KB raw / ~18-22 KB gzip | fără biblioteci |
| CSS client | 13,6 KB / 4,5 KB gzip | ~14-18 KB / ~5 KB gzip | parte din sistemul brandului |
| payload | 394 KB / 90 KB gzip | ~210 KB / ~55 KB gzip + geometrie imutabilă | dictionary encoding + split |
| cereri la un click pe județ | 16 | 1-2 | UAT-urile la cerere |
| zile de muncă (agent) | — | 7-11 | F0-F5 mai jos |

### 4.8 Faze (feliile verticale, fiecare cu criterii de acceptare)

**F0 — reparații de onestitate (0,5-1 zi, se pot livra singure):** legenda nu mai poate produce `NaN`
(construcție din praguri + test de proprietate pe 0..60); praguri absolute în loc de cuartile per filtru;
`cache: "no-store"` → `ETag`/`max-age`; textul de pe prima pagină („după județul sursei", `templates/index.html:68`)
aliniat cu ce face `generator/mini_harta.py`; `geo.eticheta_judet()` folosit în panou/fir de navigare/selector.
*Acceptare:* `?q=Giroc` nu mai conține `NaN` sau `undefined`; există test care rulează legenda pentru 0..60.

**F1 — substratul (3-5 zile):** SVG/DOM + strat de etichete în spațiu de ecran + `non-scaling-stroke`; paritate
1:1 cu starea din URL; păstrarea tuturor deciziilor de accesibilitate.
*Acceptare:* `tools/harta_dom_check.py` verde (adaptat), plus măsurători noi: niciun text < 11 px la 390/768/1440;
nicio etichetă suprapusă; 114 poligoane randează în < 100 ms pe profil CPU ×4.

**F2 — interacțiunea (2-3 zile):** previzualizare → angajare, chips-uri de straturi, control de timp, card de
eveniment, `?ev=`.
*Acceptare:* un tap nu mai declanșează nicio cerere de rețea; dublu-click nu mai are nevoie de `replaceState`;
`?ev=` deschide același card la rece.

**F3 — semantica (2-3 zile):** moduri de scară, footnote, comparație pe aceeași scară, sparkline 12 zile.
*Acceptare:* aceeași culoare ↔ același număr în orice filtru (test); denominatorul afișat cu sursa și data;
comparația nu poate produce clasament implicit.

**F4 — URL-uri și SEO (1-2 zile):** `/harta/`, redirect păstrat, nav/footer/canonical/JSON-LD, rută de județ
(opțiunea 2).
*Acceptare:* `/harta/` răspunde 200; `/harta/?judet=TIMIS` == starea de azi; linkurile vechi funcționează;
`/harta-stiri/` → 301.

**F5 — gardurile (1-2 zile):** extinderea `tools/harta_dom_check.py` (etichete ≥ 11 px, fără suprapuneri,
fără `NaN` în legendă, buget de rețea per gest), migrarea testelor de text în teste pe DOM randat, măsurare de
buget de fișiere.
*Acceptare:* `pytest` verde, `ruff` verde, raport de buget scris în PR.

### 4.9 Ce se întâmplă cu gardurile existente

| Gardă | Soartă |
|---|---|
| `tools/harta_dom_check.py` (18 verificări) | **se păstrează și se extinde** — e cea mai bună investiție din repo pe harta asta |
| `tests/test_harta_interactions.py` (aserțiuni pe text) | se rescrie pe DOM (rămân numele verificărilor ca intenție) |
| `tests/test_harta_data.py`, `test_harta_nivel_cumulativ.py`, `test_harta_judet_din_sursa.py`, `test_harta_sursa_oficiala.py`, `test_harta_route.py` | rămân, cu schema v5 |
| `tools/harta_contrast.py` (10 perechi) | se extinde cu regulile 1-4 din §4.2 |
| `tools/build_harta_uat.py`, `tools/verifica_uat.py` | **neatinse** — geometria nu se re-derivă (lecția Mărașu, `buffer(0)`) |

---

## 5. CONTRACT DE REALITATE

### 5.1 Ce înseamnă, măsurabil, „revoluționată"

O hartă e revoluționată când **cinci afirmații sunt adevărate simultan și sunt verificate mecanic**, nu când
arată bine într-o captură:

| # | Afirmație | Bază azi (măsurată) | Țintă | Cum se verifică |
|---|---|---|---|---|
| 1 | **Se citește la orice lățime** | cifre de 4 px pe mobil, nume de 2,9 px | niciun text < 11 px la 390/768/1440 | test DOM care măsoară fontul randat |
| 2 | **Scara e stabilă și corectă** | praguri per filtru; legendă `NaN` pe live | aceeași culoare = același număr; legendă numerică pentru orice maxim 0..60 | test de proprietate + captură live |
| 3 | **Prima interacțiune nu costă** | 1 gest = 3 efecte + până la 16 cereri / 1.086 KB | tap 1 = 0 cereri; zoom = ≤ 2 cereri / < 60 KB gzip | măsurare de rețea în `harta_dom_check` |
| 4 | **Orice stare e partajabilă și memorabilă** | `/harta/` = 404; fără canonical/OG | `/harta/` 200, stare în URL completă, card social corect | cerere live + inspecție HTML |
| 5 | **Cifra are context** | „55" fără perioadă, fără denominator | fiecare număr are fereastră + denominator + sursă scrise lângă el | inspecție + test care interzice un număr fără context |

Dacă 4 din 5 sunt adevărate, nu e revoluție, e îmbunătățire. Dacă 5 din 5 sunt adevărate dar costul de întreținere
crește (mai multe fișiere, mai mult JS), revoluția s-a plătit cu viitorul — de aceea bugetul de fișiere și KB e
parte din contract, nu o notă de subsol.

### 5.2 Ce NU acoperă propunerea (explicit)

- **Nu promite timp real.** Build-ul rulează ~6 ori/zi (`CLAUDE.md` §17); harta poate arăta *timp*, nu *acum*.
- **Nu rezolvă precizia de localizare.** Cele 227 de articole fără coordonate (34 %) rămân fără punct; propunerea
  le dă o reprezentare onestă, nu una falsă. Îmbunătățirea geocodării e altă lucrare (pipeline, nu hartă).
- **Nu atinge geometria.** Nici un poligon, nici o proiecție, nici `buffer(0)`/ray-casting; lecția Mărașu rămâne
  intactă. Dacă un UAT lipsește la sursă, lipsește în continuare.
- **Nu rezolvă cota de fișiere** și nu concurează cu ea: opțiunea recomandată de rută costă 1 fișier.
- **Nu implementează ideile #1-#23** din `notes/harta-imbunatatiri-cititor-2026-10-03.md`. Relația e: propunerea
  *depinde* de #2 („Localitatea mea", pentru briefing) și *se ciocnește* de #9 (hub de județ) — care trebuie
  coordonat, nu dublat. #14 (timeline + contradicții) e vecină, dar aparține directivei Story Intelligence, nu
  hărții.
- **Nu decide** ce se întâmplă cu ramura `feat/harta-vizibilitate` (observația din §2, punctul 7 — decizie de
  proprietar, nu a agentului).
- **Nu măsoară dispozitivele reale.** Cifrele de pixel sunt calculate, nu capturate în browser adevărat; prima
  măsurătoare reală trebuie făcută în F1, cu Chromium headless (metoda din `specs/harta-felia4-7-design.md`).
- **Nu rezolvă** problema celor două rampe de pe homepage și hartă în afara unui singur sistem de tokeni — dacă
  homepage-ul se schimbă în altă felie în paralel, tokenii trebuie împărțiți explicit.
- **Nu conține planul de rollout** (cine, când, în ce ordine de PR-uri) — aici se cere doar propunerea.

### 5.3 Ce ar falsifica planul (criterii de abandon, oneste)

1. Dacă la F1 se măsoară pe un Android real că SVG/DOM-ul nu ține pan/zoom la 60 fps → direcția A își pierde
   avantajul principal și se reevaluează B sau un hibrid canvas-geometrie + DOM-etichete.
2. Dacă împerecherea populației pe UAT nu trece de ~95 % după tabelul de excepții → modul „la 100.000" se
   livrează doar la nivel de județ.
3. Dacă `harta_dom_check` nu poate fi adaptat fără a-și pierde acoperirea → feliile se livrează cu dublă gardă
   (vechi + nou) până la paritate, nu cu gardă slabă.
4. Dacă proprietarul preferă animația ca prioritate → se decide cu date (Clarity/GA4: WebGL, memorie, device mix),
   nu cu impresii.

### 5.4 Riscuri cu declanșator (ce se urmărește, cine, când)

| Risc | Declanșator de urmărit | Răspuns |
|---|---|---|
| Regresie de accesibilitate (pierdem calea echivalentă) | orice `harta_dom_check` roșu pe tastatură/UAT | se blochează felia; se repară înainte de merge |
| Bloat de echipă (4 hărți, 4 sisteme) | a doua paletă definită într-un fișier nou | tokenii se mută în `static/styles.css` (`CLAUDE.md` §8) și se șterge rampa locală |
| Confuzie „clasament" din normalizare | prima apariție a cuvântului „top"/„locul N" în UI | se scoate; comparația rămâne un instrument, nu un podium |
| Linkuri moarte noi | link de eveniment cu slug lipsă | se păstrează filtrul `moderation.apply` + testul din `test_harta_data.py` |
| Costuri ascunse de pipeline | orice schemă v5 care cere un apel AI sau o cerere de rețea la build | se respinge (0 lei, deterministic) |

---

## 6. Ce nu am verificat (cu comanda care a eșuat, nu din memorie)

```
$ python3 -m pip install --user playwright
error: externally-managed-environment (PEP 668)          → venv: OK, dar:
$ /tmp/venv/bin/playwright install chromium
Error: Failed to download Chrome for Testing 153.0.8010.12 … Download failure, code=1
$ node capture.mjs
Error: Failed to launch the browser process: Code: 127
/tmp/chromium: error while loading shared libraries: libnspr4.so
$ sudo apt-get update
W: Failed to fetch http://deb.debian.org/… Connection failed   (rețea blocată în sandbox)
$ curl -sS -o /dev/null -w "%{http_code}" https://izz.ro/
curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL in connection to izz.ro:443
$ git diff --stat origin/main...origin/feat/harta-vizibilitate
fatal: origin/main...origin/feat/harta-vizibilitate: no merge base   (clonă superficială)
```

Deci: **nu am rulat pagina într-un browser real** (așa că toate măsurătorile de pixel sunt calculate), **nu am
Putut citi istoricul/PR-urile** ramurii de vizibilitate (așa că am comparat arbori, nu istorii) și **nu am putut
cere direct `izz.ro`** din sesiune (verificările live au trecut prin intermediar și sunt marcate ca atare).
Niciuna dintre aceste limitări nu schimbă concluziile de diagnostic — cifrele din care se trag sunt în fișierele
comise —, dar prima dintre ele trebuie închisă în F1, cu browser.

---

## 7. Ce cer de la proprietar (trei decizii, nu mai mult)

1. **Ruta de județ:** `/harta/<judet>/` pagină proprie (42 fișiere + 42 OG) sau 301 către `/subiect/<judet>/`
   (0 fișiere, se încorporează modulul de hartă acolo)? Recomandarea mea: **a doua**, coordonat cu ideea #9.
2. **Scara implicită:** rămâne „număr absolut" (conservator, compatibil) sau „la 100.000 de locuitori"
   (mai corect, dar schimbă citirea pentru un cititor obișnuit cu harta de azi)? Recomandarea mea: număr absolut
   implicit, 100 k disponibil cu un click, explicat în legendă.
3. **Modul regional:** se elimină (nu adaugă informație azi, 7 nuanțe la 1,00:1 între ele) sau se păstrează cu
   hașură + etichetă? Recomandarea mea: se elimină din harta publică și rămâne doar în `/surse/`, unde
   regiunile au sens (catalogul de surse).

Dacă răspunsul la toate trei e „decide tu", propunerea e executabilă ca atare; dacă răspunsul la 1 e „pagină
proprie", bugetul crește cu 42-84 de fișiere și F4 se lungesc cu o zi.

---

## 8. Anexă — comenzile care produc cifrele din document

```bash
# structura și statisticile datasetului
python3 -c "import json,collections; d=json.load(open('static/harta-stiri/data/map.json')); ..."

# greutăți (raw + gzip)
for f in static/harta-stiri/harta-stiri.js static/harta-stiri/harta-stiri.css \
         static/harta-stiri/data/map.json; do wc -c "$f"; gzip -c "$f" | wc -c; done

# volumul unui click pe județ (fișierele UAT ale vecinilor, regula bbox+35% din neighborCountiesFor)
python3 - <<'PY'   # vezi corpul din analiză: bbox-uri + pad 35% + sumă de fișiere
PY

# legenda degenerată (simulare fidelă a praguriFor/updateLegend, apoi confirmare live)
node -e 'function praguriFor(max){return [...new Set([1,2,3].map(q=>Math.floor(max*q/4)))].filter(p=>p>0).sort((a,b)=>a-b)}; ...'

# denominatorul de populație (deja în repo) și împerecherea cu UAT
python3 -c "import json; d=json.load(open('data/localities.json')); ..."   # 3.179 localități, toate cu pop
python3 - <<'PY'  # join pe nume normalizat: 3.085/3.186 = 96,8 %
PY

# contrast + L* pe valorile reale din CSS
python3 -c "…WCAG + CIE L* pentru --map-h0..h4, REGION_FILLS, --map-inner…"
```

Verificări live făcute în sesiune (prin intermediar, 4 oct 2026):
`https://izz.ro/static/harta-stiri/` (starea națională, 648 evenimente),
`https://izz.ro/static/harta-stiri/?q=Giroc` (**legenda cu `NaN`/`undefined`**), `https://izz.ro/harta/`
(**404**).

---

**cerut:** diagnostic pe trei planuri + propunere de revoluție (minim 3 direcții, recomandare, contract de
realitate), livrat ca document, fără implementare.
**livrat:** documentul de față — diagnostic cu cifre și dovezi (§1), patru direcții cu cost/risc/pierderi/
dependențe și recomandarea explicită A+D (§3), specificația recomandării (§4) și contractul de realitate (§5),
plus limitele asumate (§5.2, §6) și cele trei decizii care îmi lipsesc (§7).
**neatins la livrarea studiului:** codul de produs (zero linii), `main`, `tools/`, `generator/`,
`static/harta-stiri/`, `data/`, `moderation.yaml`, ramura `feat/harta-vizibilitate`; nicio schimbare de
schemă, niciun test modificat. *(Rând scris pentru commitul de document; implementarea a început pe aceeași
ramură imediat după — stadiul real e în §9.)*

---

## 9. Stadiu la implementare (2026-10-04)

Studiul rămâne planul de referință; secțiunea asta spune ce s-a livrat pe ramura
`arena/01a10582-izz-ro` și ce rămâne. Fiecare rând are dovada lui, nu o promisiune.

| Cerut de diagnostic | Stadiu | Dovadă / comandă |
|---|---|---|
| F0.1 legenda care nu mai minte (`NaN`, benzi inventate) | **livrat** | praguri absolute `1/6/15/30` în `#map-legend[data-praguri]`, benzi scrise static în HTML, JS doar citește și arată/ascunde; `pytest tests/test_harta_scara.py` (acoperire 0..∞, fără goluri, fără suprapuneri) |
| F0.2 nume de județe, nu coduri (`TIMIS`) | **livrat** | `judetLabel()` + `#judete-etichete` (42 de etichete == `generator.geo.eticheta_judet`), folosite în panou, tooltip, selector, fir de navigare |
| F0.3 cache-ul care pierdea 90 KB gzip la fiecare încărcare | **livrat** | `cache:"no-store"` scos din fetch-ul de date; rămâne regula `/static/harta-stiri/*` = `max-age=300, must-revalidate` (`generator/render.py:_write_headers`) |
| F0.4 furtuna de prefetch | **livrat** | plafon 6 fișiere, alese după suprapunerea cu view-box-ul: TIMIS 8→6, ALBA 15→6 (1.017→435 KB), BRAȘOV 13→6 |
| F1 substrat de desenare (canvas → SVG/DOM, fără biblioteci) | **livrat** | `pytest tests/ -q` → 1907 passed / 4 skipped / 8 xfailed; `ruff check .` curat |
| F1 hit-test nativ în locul cascadei de toleranțe | **livrat** | `event.target` + `isPointInFill`; dispare costul de 43.000–80.000 point-in-polygon per redesenare (măsurat: 79.831 la TIMIS) |
| F1 etichete-text în pixeli de ecran (≥ 11 px), linii cu `non-scaling-stroke` | **livrat** | `LABEL_PX { judet 13, regiune 14, uat 11, cifra 12 }`, grupuri `.label-fit` contrascarate; `tests/test_harta_interactions.py::test_map_labels_are_real_text_with_minimum_pixel_sizes` |
| F1 paletă: `h0` neutru, trepte echidistante, graniță vizibilă | **livrat** | `python tools/harta_contrast.py` → 24/24 pe ambele teme (ΔL* 8,3–11,3; ΔE* ≥ 11,7; contur 3,98:1 pe alb; înainte `#ffffff` pe `#ffffff` = 1,00:1) |
| F1 calea accesibilă păstrată | **livrat** | poligoane cu `role="button"`, `tabindex="0"`, `aria-pressed`, `aria-label` cu nume + cifră |
| „un singur sistem vizual" (pulsul de pe prima pagină) | **livrat** | `.puls-map path.h0..h4` == `--map-h0..h4`; gardă de egalitate în `tests/test_mini_harta.py`; captionul spune explicit că scara pulsului e relativă la zi |
| F5 gardurile mutate pe substratul nou | **livrat** | `tools/visual_check.py` (rulează în CI pe `main`) citește semnătura din DOM + `viewBox`, nu din pixeli; `tools/harta_dom_check.py` folosește `getBBox`/`isPointInFill`/`getScreenCTM` + `elementFromPoint`, fără replică manuală a transformării; testele de canvas rescrise pe invarianții noi |
| F2 previzualizare → angajare (județ) | **livrat** | prima activare filtrează și partajează `?judet=X&preview=1`, fără zoom și 0 cereri UAT; „Intră în [județ]” sau a doua activare face angajarea și cere o singură geometrie; `?judet=X` istoric rămâne modul detaliu. Acoperit de `tests/test_harta_interactions.py`, `tools/harta_dom_jsdom.mjs` (fără browser) și `tools/harta_dom_check.py` (**[NEVERIFICAT] fără Playwright/Chromium**) |
| F3 control de timp (12 zile) | **urmează** (fereastra e acum în footnote, calculată din date) | `#map-window` = „22 sept. – 4 oct. (13 zile)”, scris de `updateWindow()` |
| F3 filtre pe categorii / straturi | **urmează** — `category` din `map.json` v4 este `local`/`judetean`/`regional` (606/53/3), adică exact nivelul geografic care există deja ca filtru; un strat „pe categorii editoriale” ar cere categorii noi în dataset, deci nu se poate livra doar din client (rămâne pe F4, cu schemă v5) | — |
| F3 deep-link pe eveniment (`?e=`) + card partajabil | **urmează** | — |
| F3 comparație județ-județ | **urmează** | — |
| F3 moduri de scară (volum / pe locuitor) + numitorul cu sursă și dată | **livrat** | `tools/build_harta_populatie.py` → `data/populatie.json` (42 de județe, total 19.080.476, +0,14 % față de INS 2021); 7 verificări noi în `tests/test_harta_scara.py`; `tools/harta_dom_jsdom.mjs` |
| F4 /harta/ + /harta/<slug>/ pentru toate județele | **livrat** | `generator.render._write_harta_pages()` emite 43 de shell-uri statice din aceeași pagină + același `map.json`; 42 de slug-uri validate fără coliziuni, canonicale/OG/JSON-LD WebPage+Dataset+Place locale, sitemap și redirect `/harta-stiri/` → `/harta/`. `python -m generator.main --render-only`: 13.505/17.000 fișiere (marjă 3.495). Linkurile nav/home folosesc `/harta/`; detaliul se angajează pe `/harta/timis/`. OG image rămâne cea comună — 42 imagini OG nu fac parte din felia asta. |

**Cum a fost verificat (și ce NU s-a putut verifica).** Browserul real nu există în mediul în care s-a
lucrat (Playwright/Chromium nu se pot instala), deci dovada vine din trei straturi: (1) suita de teste
Python; (2) verificări de DOM în jsdom — 23 de verificări de structură (`clip-path` legat de siluetă,
conturul în strat propriu, o singură cerere de geometrie, `h0..h4` aplicate, etichete text) plus o
plimbare prin toate cele 26 de căi de interacțiune (hover, click, zoom, tastatură, selector, UAT, fir,
căutare), cu 0 erori; (3) `tools/harta_contrast.py`, determinist. **jsdom nu are layout**, deci nu ține
loc de browser: `tools/harta_dom_check.py` și `tools/visual_check.py` rămân de rulat pe o mașină cu
Playwright, iar primele rulări pot cere ajustări de toleranțe (nu de logică). Cifrele de pixeli din §1
sunt calculate, nu capturate.

**F3a — moduri de scară, livrat (2026-10-04).** Ce era diagnosticat ca „lipsă de semnificație"
(cifra spunea cât de mare e județul, nu cât de multe știri are pe cap de locuitor) are acum un
comutator în bara de unelte: **Volum** (ce era) / **Pe locuitor** (evenimente la 100.000 de
locuitori, fereastra hărții). Ce s-a livrat concret:

- **Numitorul are sursă și dată**: `data/populatie.json` (42 de județe, generat de
  `tools/build_harta_populatie.py` din `data/localities.json`; total 19.080.476 = +0,14 % față de
  recensământul INS 2021 de 19.053.815). Instrumentul refuză să scrie dacă abaterea depășește 2 %,
  iar testul citește cifrele din footnote și le compară cu fișierul, ca să nu poată diverge.
- **Scara e o a doua scară, nu o înlocuire**: praguri absolute proprii `[0,1 / 1 / 2 / 4]`, scrise
  în pagină (`data-praguri-locuitor`) lângă benzi, pe grila de afișare a ratei (o zecimală). Testul
  verifică pentru ambele scări că benzile acoperă 0..∞ contiguu, pe grila proprie, și că prima bandă
  nu poate înghiți un eveniment real (cel mai mic județ, 193.355 de locuitori → o știre = 0,52).
- **Invarianta „aceeași culoare = același număr" e păstrată prin construcție**: clasa de culoare se
  calculează din chiar valoarea afișată (rotunjită la o zecimală), deci ce vede cititorul și ce
  colorează harta sunt același număr. Verificat pe toate 42 de județe, în jsdom și în garda de DOM.
- **Footnote-ul spune numărătorul, numitorul și fereastra** — cu totaluri și cu propoziția care
  lipsește cel mai des într-o hartă: „diferențele de sub un eveniment nu sunt semnificative".
- **UAT-urile rămân pe volum și o spun**: populația există doar pe județe în datele publicate, deci
  în interiorul unui județ scara e numărătoarea, iar legenda are un titlu propriu pentru asta
  („Volum de știri (pe orașe și comune)"), plus o notă în pagina hărții.
- **Legenda se vede și după intrarea într-un județ** — acolo se schimbă exact ce explică ea. Înainte
  era ascunsă la zoom, deci cititorul cu un județ deschis nu avea nicio scară pe ecran.
- **Costul**: `populatie.json` = 942 B, cerut **lenes**, o singură dată, doar dacă cititorul comută
  scara (sau dacă linkul o cere). Modul implicit nu face nicio cerere în plus.
- **Gardă nouă, în repo**: `tools/harta_dom_jsdom.mjs` — 46 de verificări de structură/scară plus o
  plimbare prin toate cele 26 de căi de interacțiune, în jsdom (fără browser). A prins două defecte
  reale înainte de livrare: un `use` de siluetă lăsat în afara arborelui (ar fi tăiat toate UAT-urile
  din vedere) și un mod „pe locuitor" care afișa tăcut numărătoarea (în stare intra fișierul de
  populație întreg, nu dicționarul de județe). `tools/harta_dom_check.py` a primit secțiunea
  „SCARA SI NUMITOR", care recalculează raportul din `map.json` + `populatie.json`, independent de
  JS-ul paginii.

**Notă operațională (actualizată 2026-10-05).** Managerul a transmis că exportul a reușit și că
PR #440 are CI 11/11 verde, cu feliile F0–F3 salvate pe GitHub. Nu am reverificat remote (sesiunea e
închisă pentru operații GitHub și nu am încercat niciun fetch/push). F2 preview→angajare, rutele F4 și
felia F3 comparație/grafic lucrate după export sunt **doar în workspace-ul acestei sesiuni** până când
managerul exportă din nou. Hash-urile locale pot dispărea la reprovisionarea sandbox-ului; fișierele din
workspace sunt sursa de adevăr pentru următorul export.
