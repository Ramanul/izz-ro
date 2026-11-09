# Măsurători front-end — arhiva §13

> **Ce e:** istoricul complet al măsurătorilor de performanță/accesibilitate pe izz.ro, mutat aici
> din `CLAUDE.md §13` pe 2026-08-06. Motivul mutării: §13 avea 5.898 de caractere și se încărca în
> context la FIECARE tură, deși se citește o dată pe lună. Regulile care obligă la acțiune au rămas
> în `CLAUDE.md §13`; aici stau cifrele, ipotezele picate și metodologia.
>
> **Când se citește:** înainte de orice slice care atinge `templates/`, `static/styles.css` sau
> HTML/JSON-LD din `render.py`. Și obligatoriu înainte de a re-investiga CLS.

## Unealta

**Regula de alegere a uneltei:** preferă măsurarea CLI **locală** în locul „site-urilor de
testare" — ieșire JSON structurată, rulează pe `localhost` ÎNAINTE de deploy, fără rate limits.
API-urile externe (PageSpeed Insights, validatorul W3C) sunt un complement **post-deploy** pe
site-ul live, **nu un substitut** pentru măsurătoarea de dinainte de commit.

`bash tools/audit.sh` — Lighthouse + pa11y pe `output/` servit local, JSON în `.audit/` (gitignored).
Setup: `npm i -g lighthouse pa11y`. Auto-detectează Chromium (`CHROME_PATH` pentru override).

Auto-detecția acoperă Linux/CI (Chrome *și* Chromium) și, pe Windows, **doar căile implicite ale
Google Chrome** — Chromium n-are installer oficial de Windows, deci nu există cale canonică de
sondat; acolo se pasează `CHROME_PATH` pentru Chromium sau Edge.

**Atenție la `.audit/` vechi:** până pe 2026-08-02 scriptul era Linux-only pe Windows în trei feluri
separate (niciun browser găsit; o linie de versiune care citea „Opening in existing browser
session."; pa11y murea pe o cale MSYS iar rularea tot tipărea „-1 errors"). Un `.audit/` de dinainte
de data aia, de pe Windows, **nu e o măsurătoare**.

## 2026-09-09 — arta desenată în pagină (migrarea pe Workers Free)

Mediane pe **3 repetări**, aceeași unealtă ca baseline-ul de mai jos (Lighthouse 13.4.1,
Chromium 141.0.7390.37), `output/` servit pe `127.0.0.1:8899`,
`ARTICLE_PATH=/sport/30-de-ani-de-la-moartea-legendarului-fotbalist-ion-oblemenco/`.

| Pagină | Perf | A11y | BP | SEO |
|---|---|---|---|---|
| home | **94** (94/96/92) — baseline 80 → **+14** | 96 | 100 | 100 |
| articol | **97** (97/97/97) — baseline 88 → **+9** | 96 | 100 | 100 |

pa11y WCAG2AA (v10.0.0): **0** erori pe ambele pagini — arta desenată în pagină nu adaugă
niciuna, deși textul ei devine text DOM real.

**De unde vin cele +14 / +9:** homepage-ul face acum **14 cereri în total, dintre care 1 de
imagine** (o fotografie reală de lead) și 258 KB transferați. Înainte, fiecare card cerea propriul
`art.jpg`/`art-card.webp` — 44 de cereri de imagine doar pe home. CLS 0.091, TBT 0 ms, LCP 2,4 s.

**A11y 96, nu 100 — și NU din cauza artei.** Singura penalizare e `target-size`, pe
`nav.subnav > details.subnav-more > summary` și pe linkul din el, adică pe meniul „Mai multe
secțiuni". Suprafața aia nu e atinsă de această felie; e o regresie apărută între 2026-08-02 și
azi, de reparat separat. Blocurile `.art` nu apar în niciun audit picat.

## Baseline — re-măsurat 2026-08-02 pe `main` @ `34cc8d3`

| Pagină | Perf | A11y | BP | SEO |
|---|---|---|---|---|
| home | **80** | 100 | 100 | 100 |
| articol | **88** | 100 | 100 | 100 |

pa11y WCAG2AA: **0** erori.

Măsurat cu Lighthouse 13.4.1, pa11y 9.1.1, Chromium 141.0.7390.37. Un upgrade la oricare dintre
cele trei mută cifrele, de aceea `audit.sh` le scrie în `.audit/versions.txt` la fiecare rulare.
**Compară like cu like:** același corpus pe desktopul Windows sub Chrome 150.0.7871.187 citește
home **83-84** / articol **92** în modul low-CLS de mai jos — deci 80 nu e o cifră de reprodus acolo.

## Varianța e un comutator cu două stări, nu o împrăștiere (măsurat 2026-08-02, PR #106)

Șase rulări pe două revizii, articol fixat: home a citit 84·83·84 înainte și 76·83·83 după. Fiecare
scor urmărește CLS aterizând pe exact una din două valori — ~0.156 (home 83-84) sau 0.272 (home 76).
Aceeași bimodalitate pe pagini de articol: 92 la CLS 0.172, 85 la 0.272. Ambele moduri apar pe
**ambele** revizii, deci comutatorul e preexistent, nu introdus de un slice.

**Consecință operațională:** o singură pereche înainte/după **nu poate** rezolva un efect mai mic de
~8 puncte pe home. Se rulează **3+ repetări per revizie și se compară medianele**, cu `ARTICLE_PATH`
fixat. Asta înlocuiește citirea mai veche „5 rulări identice, un outlier la 84" — aceea era același
comutator văzut dintr-o singură parte.

**Fixează pagina de articol când compari.** `audit.sh` scora `find | head -1`, adică ce întorcea
primul sistemul de fișiere, deci scorul „articol" se referea tăcut la pagini diferite între rulări
(măsurat: 87 vs 88 pe același commit). Implicitul e sortat și deci stabil pentru un corpus dat, dar
conținutul se schimbă între randări — pentru un înainte/după real, pasează `ARTICLE_PATH=/cat/slug/`.

## De ce e ținut jos Perf-ul pe home

Măsurat din JSON-ul Lighthouse, nu ghicit: **CLS și FCP**. CLS 0.272 în modul prost scorează 56 la
pondere 25; FCP 2.6 s scorează 65 la pondere 10; `styles.css` blochează randarea ~900 ms; TBT e
100 perfect. **Nimic din asta nu ține de imagini.**

## Vinovatul CLS e `#izz-install-btn` — și cele două explicații anterioare erau greșite

Măsurat 2026-08-02, emulare mobilă 412 px. Lighthouse atribuie 100% din shift unui singur element,
`body > main`, al cărui `boundingRect.top` final e **285**. Comutând butonul de instalare într-un
browser real: ascuns → `main` începe la **236.3**; afișat → **285.3**. Potrivire exactă.

Butonul stă în `.nav`, în grupul de header sticky, e `hidden` în markup, iar
`personalize.js::initInstallButton` îi scoate `hidden` când se declanșează `beforeinstallprompt` —
împingând fiecare articol în jos cu **49 px** în timpul cititului. Momentul evenimentului ăluia nu
e determinist, exact de-aia scorul e bimodal, nu zgomotos.

*(2026-10-03: funcția nu mai e în `personalize.js`, s-a mutat în `static/pwa.js`, iar butonul a
ieșit din `.nav` într-un element `position: fixed`. Măsurătoarea de mai sus rămâne așa cum a
fost făcută — descrie poziția din header, care e exact ce NU trebuie refăcut.)*

### Două ipoteze picate — a NU se redeschide

- **NU e `#izz-consent`:** e `position: fixed; bottom: 0`, adică în afara fluxului — nu are cum să
  miște `main`.
- **NU e swap-ul de web-font:** forțând stivele de fallback declarate și re-măsurând → delta **0 px**
  pe grupul de header, la 412 px și la 1280 px. Fonturile sunt self-hosted, subsetate (7-17 KB), două
  preîncărcate. Înregistrat în registru ca `IZZ-0133 · masurat-fals`.

### Repararea e o decizie de plasare, nu una tehnică

Butonul trebuie să nu mai crească header-ul, iar unde se mută e decizia proprietarului (§8).
Rezervarea permanentă a rândului ar costa 49 px de header mobil pentru un buton pe care majoritatea
vizitatorilor nu-l văd niciodată. **A NU se „repara" prin întârzierea dezvăluirii dincolo de
fereastra CLS** — aia e vânătoare de scor, interzisă de §13.

## Contrast — lecția din 2026-07-02

Fix-ul care a dus A11y la 100 a întunecat două tokenuri (`--ink-3`, `--gold-strong`). Descoperirea
„linkuri de footer" era de fapt **249 de erori pe tot site-ul**; doar măsurarea a arătat scopul real.
Contrastul pentru culori noi trebuie să treacă 4.5:1 față de `--paper` **ȘI** `--gold-wash`, nu doar
față de alb.

## Alarma „fotografiile au stricat Perf" — non-eveniment (2026-08-02)

Home era 80 și înainte, și după. Costul total al adăugării de fotografii reale: **−1 punct** pe o
pagină de articol, +65 KiB, +0.3 s LCP. Tabelul complet înainte/după e în PR #101.

**Regula generală:** o cifră din fișierele astea e o măsurătoare de sandbox local, nu o promisiune
despre izz.ro. Există ca să compare *înainte vs după un slice pe aceeași mașină*. Când un scor pare
o regresie, măsoară commit-ul de dinainte de slice într-un worktree și compară.

## Rebranding „Hârtie curată" — faza 0+1: tokeni și tipografie (2026-11-07)

Slice: `static/styles.css` `:root` + blocul dark, `static/fonts.css`, `templates/base.html`
(preload), `static/sw.js` (precache), `tools/fetch_fonts.py`. Șabloanele nu s-au atins dincolo
de preload-uri; structura de informație e identică, deci diferențele de mai jos sunt integral
efectul tokenilor.

**Măsurat local** (`--render-only` pe `state`-ul real: `build.json` = 6496 articole / 11.089
fișiere — verificat ÎNAINTE de citire, fiindcă `pytest` rescrie `output/` cu fixture-ul de ~190
articole). Coloana „înainte" e contrafactualul obținut prin înlocuirea blocului de fonturi din
`<head>` cu cel de la `HEAD`, pe aceeași pagină randată: markup-ul e identic, deci diferența e
integral efectul acestui slice.

| Indicator | Înainte | După | Δ |
|---|---:|---:|---:|
| Fonturi auto-găzduite (`static/fonts/*.woff2`) | 87.960 B / 7 fișiere | 76.224 B / 5 fișiere | −11.736 B (−13%), −2 fișiere |
| `fonts.css` inlineat în `<head>` | 1.160 B | 794 B | −366 B |
| Prima pagină, gzip | 109.205 B | 109.179 B | −26 B |
| Articol (`/extern/slabirea-timpurie-a-vortexului-polar-…/`), gzip | 20.563 B | 20.542 B | −21 B |
| `styles.css` | 80.768 B | 81.764 B | +996 B (comentarii + regula `tabular-nums`) |
| Prima încărcare, mediană pe 7679 pagini (`tools/greutate.py`) | — | 155 KB | neschimbat de acest slice |
| Fișiere în `output/` | 11.088 | 11.089 | +1 (licența OFL Newsreader) |

Corecție de cifră: tabelul de ținte din `analiza/rebranding/PROPUNERE.md` §6 spunea „104 KB / 7
fișiere" la fonturi; măsurat pe disc, cele 7 fișiere însumau 87.960 B (85,9 KiB). Ținta de ≤55 KB
rămâne neatinsă; vezi §8.2 din propunere pentru de ce (Newsreader are nevoie de două fete, Inter
700 nu poate fi scos fără bold sintetizat la `<strong>`).

**Contrast (WCAG 2.1, text mic) — toate tokenii de text, pe cele trei fundaluri, în ambele teme.**
Regula din acest fișier (§Contrast) cere 4,5:1 față de `--paper` **și** `--gold-wash`:

| Token | pe `--paper` | pe `--paper-2` | pe `--gold-wash` | Verdict |
|---|---:|---:|---:|---|
| `--ink` #14161a | 17,35 | 18,11 | 16,05 | AA |
| `--ink-2` #4a515c | 7,67 | 8,01 | 7,09 | AA |
| `--ink-3` #6a6a73 | 5,13 | 5,35 | 4,74 | AA |
| `--gold-strong` #7c5f22 | 5,72 | 5,97 | 5,29 | AA |
| `--navy` #173a5e | 11,16 | 11,65 | 10,32 | AA |
| `--live` #b23a2e | 5,69 | 5,94 | 5,26 | AA |
| dark: `--ink` / `--ink-2` / `--ink-3` | 15,2 / 8,6 / 6,1 | 14,0 / 7,9 / 5,6 | 14,0 / 7,9 / 5,6 | AA |
| dark: `--gold-strong` #d3b26a / `--navy` #a9c7e9 | 9,3 / 10,8 | 8,6 / 10,0 | 8,6 / 10,0 | AA |

Nota de implementare: `--ink-3` a fost coborât de la #6f7683 (4,38:1 pe `--paper`, **sub AA**) la
#6a6a73. Culorile de accent au trecut din aramă în navy pentru *acțiuni*; arama (`--gold`) rămâne
doar decor (3,40:1 — nu se folosește pe text, exact ca înainte cu aurul viu).

**Trei reparații colaterale găsite la măsurare** (ar fi fost regresii in vizibil, nu în scor):
`color: #fff` fix pe fundal `var(--ink)` / `var(--gold)` (`.btn-source`, `.pagination .current`,
hover pe `.theme-toggle`, `.back-to-top`, `.pagination a`, `.btn-preset`) — albul nu supraviețuiește
inversării temelor; acum textul e `var(--paper)`, care se inversează o dată cu fundalul. Butonul de
instalare PWA a pierdut gradientul metalic (aramă) în favoarea navy-ului solid.

**Ce NU s-a putut măsura aici:** `bash tools/audit.sh` cere un Chromium și `lighthouse`/`pa11y`
instalate; sandbox-ul de lucru nu are nici browser, nici pachetele, deci **scorurile Lighthouse și
numărul de erori pa11y rămân nemăsurate pentru acest slice** — de rulat pe o mașină cu browser
înainte de merge. Ce s-a rulat: `pytest` (3100 passed, 4 skipped, 8 xfailed), `ruff check .`
(curat), `csstree-validator` (singurul avertisment e preexistent: `url(#art-gold-grad, ...)`).

## Rebranding „Hârtie curată" — fazele 2–6: masthead, card, articol, coperți, consolidare (2026-11-07)

Aceleași condiții ca mai sus, cu o diferență importantă: **fără browser**. Sandboxul în care s-a
făcut redesignul nu are Chromium, `lighthouse`, `pa11y` și nici acces la rețea, deci **nu există
scoruri Lighthouse sau număr de erori pa11y pentru acest slice** — toate cifrele de aici sunt
octeți pe disc, legături verificate și rapoarte de contrast calculate. De rulat `tools/audit.sh`
pe o mașină cu browser înainte de merge.

### Greutatea paginilor (build real: 6.496 articole, 11.087 fișiere)

| Pagină | Înainte de fază 3 | După fazele 2–6 | Δ |
|---|---:|---:|---:|
| Prima pagină, brut | 593.356 B | **138.964 B** | −458.392 B (−77%) |
| Prima pagină, gzip | 109.179 B | **36.718 B** | −72.461 B (−66%) |
| Articol `/ai/competentele-…/`, brut | — (nemăsurat) | **17.955 B** | — |
| Articol, gzip | 20.542 B | **5.202 B** | −15.340 B (−75%) |

Cauza scăderii nu sunt fonturile: **arta generată a ieșit de pe card** (58 de compoziții inline
însemnau ~455 KB, 76% din prima pagină). Arta rămâne pe pagina de articol, pe lead și pe coperta
OG, unde chiar e privită. Prima pagină are acum 25 de carduri vizibile și 10 rubrici.

### CSS: de la trei foi la una

| | Înainte | Acum |
|---|---:|---:|
| Fișiere | `styles.css` + `site.css` + `faza2.css` | `styles.css` |
| Cereri la prima pictare | 3 | **1** |
| Octeți (brut / gzip) | 90.178 B / 23.873 B | **89.668 B / 23.773 B** |

`site.css` era duplicat cuvânt cu cuvânt al blocului mobil din `styles.css`; `faza2.css` conținea
`.puls*` și `.progress`, mutate în `styles.css`. Amândouă fuseseră inventate pe 2026-10-02 doar ca
să ocolească `Cache-Control: immutable` pe `styles.css` — problemă rezolvată între timp de hash-ul
din `?v=`.

### Rampa hărții, treaptă cu treaptă

Cele cinci trepte erau încă aurul vechi (`#c9a227`). Sunt acum construite pe alama brandului, cu
**aceleași trepte de lumină**, în ambele teme:

| Treaptă | Înainte | Acum | L* înainte → acum |
|---|---|---|---:|
| h0 (neutru) | `#eaecf0` | `#eaecf0` | 93,4 → 93,4 |
| h1 | `#f2d090` | `#e0d3ba` | 85,0 → 85,0 |
| h2 | `#d6bb6c` | `#cfbb93` | 76,6 → 76,6 |
| h3 | `#c9a227` | `#bfa36d` | 68,3 → 68,3 |
| h4 | `#a8841f` | `#a8823a` (= `--gold`) | 57,0 → 56,7 |
| dark h1–h4 | `#43371a … #b28c22` | `#423721 … #af8c49` | identice (±0,1) |

Textul închis pe trepte dă 12,12 / 9,55 / 7,41 / 5,05:1 (înainte 12,12 / 9,55 / 7,41 / 5,11) — AA
păstrat fără halou. Accentul paginii de hartă trece pe `--gold-strong` (5,97:1 pe alb, era 5,08),
iar `--map-on-accent` devine alb: negru pe alama închisă ar da 3,0:1, sub prag.

Dovadă vizuală: `analiza/rebranding/img/proba-rampa-harta-2026-11-07.jpg`.

### Coperți (OG 1200×630)

1.200 de coperți proprii + 5.296 articole care folosesc coperta de categorie. Newsreader 700 pentru
titlu (56 px, coboară la 34 px din 4 în 4 până încape în 4 rânduri, pe lățimea sigură a geometriei:
54% diagonală, 66% coloană, 64% split, 50% arc), Inter 600 pentru kicker și etichete (24 px),
JPEG q90. Mărime: mediană **98 KB**, între 24 și 283 KB.

### Porți noi, rulate pe build-ul real

| Poartă | Rezultat |
|---|---|
| `tools/html_check.py` | 7.679 pagini, **399.474** legături interne, **8.040** imagini: 0 legături moarte, 0 ancore moarte, 0 imagini fără `alt`, 0 active lipsă |
| `tools/a11y_static.py` (nou) | 7.679 pagini: **0** încălcări tari (nume accesibil, un singur `h1` pe pagină, etichete de formular, id-uri unice, fără `tabindex` pozitiv) |
| `tools/greutate.py` | 7.679 pagini, prima încărcare **mediană 160 KB**, cea mai grea **532 KB** |
| `pytest` | **3.110 passed**, 4 skipped, 8 xfailed (10 teste noi, de mutație, pentru poarta de accesibilitate) |
| `ruff check .` | curat |

### Două erori de măsurare reparate în `tools/greutate.py`

Prima rulare pe build-ul real raporta „cea mai grea pagină 2.016 KB". Nu era o regresie de site, ci
două defecte ale uneltei, găsite pentru că cifra nu se potrivea cu markup-ul:

1. `<source>` dintr-un `<picture>` nu are atribut `loading` propriu, deci **toate** imaginile de card
   (`loading="lazy"` pe `<img>`) erau numărate ca „eager": 2.016 KB → 615 KB după reparație.
2. `<img>` dintr-un `<picture>` cu `<source>` e doar fallback: browserul descarcă sursa, nu și
   jpg-ul. Se numărau amândouă: 615 KB → **532 KB** după reparație.

Ambele reparate în `tools/greutate.py`, cu motivul scris în docstring. Cifrele din secțiunile
anterioare ale acestui fișier, măsurate cu unealta veche, sunt deci **ușor umflate** pe paginile cu
`<picture>` (articolele).

### Ce rămâne nemăsurat / neatins (starea la finalul fazei 6)

- **Lighthouse și pa11y**: fără browser în sandbox, fără scoruri. Nu se inventează — dar vezi
  faza 7 mai jos: ele rulează deja în CI, pe runner.
- **CLS/LCP reale**: necesită randare. Ce se știe static: toate `<img>` au `width`+`height`
  (0 imagini fără dimensiuni pe 7.679 pagini), deci spațiul e rezervat înainte de descărcare.
- **Portrete mari** — *închis în faza 7*, cu o corecție de premisă: fișierele nu erau
  supradimensionate, erau supracodificate.
- **Fonturi**: 76.224 B / 5 fișiere, ținta era ≤55 KB / 3 fișiere — *decizie de design, cu
  variantele măsurate în faza 7*.

## Rebranding „Hârtie curată" — faza 7: greutate, nume, portrete, fonturi (2026-11-07)

Trei „rămâne deschis" din §8.4 s-au închis, unul s-a dovedit o premisă greșită, iar inventarul
de tokeni a scos la iveală trei bug-uri reale. Toate cifrele de mai jos sunt măsurate local pe
build-ul real (6.496 articole, 11.087 fișiere), cu comenzile citate.

### Portretele: nu erau mari, erau prost comprimate

Premisa din faza 6 („cinci portrete de 190–371 KB, `srcset` ar scuti 1,5 MB") era greșită în
cauză, nu în cifră. `media/portraits/ciprian-deac.jpg` avea **232×318 px** la 379.742 B, adică
**5,15 B/px**, iar în pagină se afișează la maximum **168 px**. Un `srcset` ar fi servit tot un
fișier prost comprimat, doar mai mic: problema era codificarea. `tools/fetch_portraits.py`
scria pe disc octeții primiți de la Commons, fără re-encodare.

| Măsurătoare | Înainte | După |
|---|---|---|
| Cel mai greu portret servit | 379.742 B (5,15 B/px) | 19.635 B (0,27 B/px) |
| Cele 368 de portrete servite, în total | 15.516 KB | 12.417 KB (−20%) |
| `media/portraits/` pe disc | 98,8 MB | 78,2 MB (−20,6 MB, 220 fișiere rescrise) |
| PSNR pe cel mai greu fișier (q85) | — | 34,1 dB |
| `sport/ciprian-deac-…`, prima încărcare | 552,6 KB | 192,5 KB |

Unealta: `python tools/usureaza_portrete.py [--apply]`. Reguli deterministe (ca fișierul comis să
fie reproductibil): EXIF-ul se arde în pixeli și apoi se aruncă, latura mare ≤ 640 px, JPEG
progresiv q85, rescriere doar dacă scade ≥15% și fișierul trece de 20 KB. Același
`compacteaza_bytes` e chemat acum de `fetch_portraits.py` pe fiecare descărcare, deci regula se
aplică și în viitor. Garda: `tests/test_greutate_portrete.py` — buget **0,75 B/px** (podea 6 KB),
plus proba că unealta nu mai are ce rescrie; 220 din 394 de fișiere erau peste buget, acum 0
(maximul e 0,71 B/px).

Un efect secundar de plătit o dată: `data/portrete_incadrare.json` e cheiat pe `sha256`-ul
fișierului, deci re-encodarea a invalidat 220 de intrări. `tools/incadrare_portrete.py` le-a
recalculat (OpenCV YuNet, 5,6 s) — decupajul a ieșit practic identic: 179 de intrări diferă doar în
a patra zecimală, iar abaterea maximă a lățimii medalionului e sub 4% (`abdoulaye-seye` 170,42% →
166,73%). Detectorul citește aceiași pixeli cu o diferență de compresie, nu altă față.

### Numele din CSS: 465 de referințe redenumite, zero pixeli mișcați

`--gold` → `--brass`, `--gold-strong` → `--brass-deep`, `--gold-wash` → `--sunk`, iar scara de
spațiere `--s-5/8/13/21/34/55/89` → `--sp-4/8/12/20/32/56/88` (numele = valoarea în px; vechiul
`--s-13` era 12px). `--font-mono` a fost șters: avea exact valoarea lui `--font-text`, deci era
un al doilea nume pentru același font.

Dovada că nu s-a mișcat nimic vizual: cele **7.679 de pagini randate** au fost comparate înainte/după
(cu `?v=` normalizat) — **o singură diferență**, contoarele pe 24 de ore din banda zilei
(976 → 973 articole), adică timpul, nu CSS-ul.

Inventarul de tokeni (`var(--x)` fără `--x:` în fișier) a scos trei bug-uri tăcute, toate
reparate:

| Token | Efectul real | Reparația |
|---|---|---|
| `--ok`, `--warn` | punctul de încredere din card (`background: var(--ok)`) rămânea **transparent**: verde = confirmat și ocru = o singură origine erau invizibile | definite (`#2f6b46` 6,07:1; `#8a6414` 5,14:1) + variantă de temă întunecată (8,57:1 / 9,07:1) |
| `--font-title` | nume dinainte de rebranding: cifra din callout-ul financiar se desena cu Inter, nu cu seriful de titluri | → `--font-display` |
| `--s-4` | pas de spațiere inexistent (seria veche era 5/8/13/21/…) → marginea dispărea cu totul | → `--sp-4` |

Garda: `tests/test_css_tokeni.py` (niciun `var()` fără definiție; whitelist-ul de tokeni puși din
JS e dovedit, nu declarat; numele vechi nu au voie să reapară; `--sp-N` trebuie să fie N px).

### Fonturile: ținta „3 fișiere / 55 KB" se retrage, cu cifre

Livrate: **5 fețe / 76.224 B** (Inter 400/600/700 = 37.440 B; Newsreader 400/600 = 38.784 B).
Ținta din propunere era 3 / 55 KB. Au fost măsurate ambele drumuri și **niciunul nu duce acolo**
fără o schimbare vizibilă:

1. **Newsreader variabil, un singur fișier pentru 400–800.** Aici a existat o **eroare de
   măsurare** care a stat o vreme în document: cifra „9.396 B" (sau 4.044 B cu `opsz` fixat) a
   ieșit dintr-un subset făcut din `analiza/rebranding/fonts/newsreader-var.woff2` — dar fișierul
   acela **nu e fontul complet, e felia latin-ext**: 229 de codepoint-uri, fără `!`…`H`, fără
   cifre, fără aproape tot ASCII-ul de bază. Un subset fără litere cântărește puțin și seamănă cu
   un câștig de 29 KB; HarfBuzz, chemat să shapeze titluri reale cu el, a arătat imediat că
   spațierea iese fără sens (`H` și `o` lipsesc din cmap).
   Pe fontul variabil **complet**, economia realistă e de ordinul a **15–20 KB** (38.784 B →
   ~20–25 KB, cu `gvar` pentru 212 glife), adică inventarul ar ajunge la **~58 KB** — tot peste 55.
   Peste asta, rutarea ar cere vectorul complet din `google/fonts`, care nu e în repo. Garda
   `test_fisierul_variabil_din_analiza_e_doar_o_felie` ține minte capcana.
2. **Renunțarea la Inter 600** (3 fișiere / ~47 KB): cele ~30 de etichete scrise cu 600 ar cădea
   pe 700 — exact „efectul vizibil pe `strong`" din §8.4. Se decide cu A11y măsurat, nu ca efect
   secundar al unei cifre de octeți.

**Concluzia nu e „rămâne pe mai târziu", e „ținta era formulată greșit".** A fost scrisă înainte de
a se ști din ce e făcut inventarul; acum se știe: fiecare dintre cele cinci fețe are un rol
(400 text de articol, 600 titluri și etichete, 700 butoane și „citește mai mult"), iar Inter singur
cântărește 37.440 B. Criteriul real, păzit de `tests/test_fonturi.py`, e **5 fețe / 80.000 B** plus
diacriticele românești verificate față cu față.

### Lighthouse / pa11y: rulau deja, doar că nu se știa

`tools/audit.sh` are nevoie de Chromium, iar sandboxul nu are; dar `.github/workflows/editorial-frontend-audit.yml`
rulează **exact acest script** pe fiecare PR care atinge `generator/render.py` sau șabloanele:
trei rulări pentru revizia de bază și trei pentru cea de pe PR, cu mediană pe patru categorii
Lighthouse plus numărul de erori WCAG2AA din pa11y. Pe ramura rebrandingului a trecut verde
(rularea `42357330249`, 7 nov 08:52). Ce lipsea era ca schimbările de **CSS și imagini** să
declanșeze și ele măsurătoarea — un redesign se judecă pe ele, nu pe `render.py`. Adăugate în
`paths:`, alături de `static/**` și `media/portraits/**`.

## Paleta epistemică: culori măsurate, nu alese din paletare (2026-11-08, IZZ-0456)

Cererea a venit ca paletă „semantică" (verde = consens, albastru = traseul sursei, ocru =
divergență, indigo = incertitudine). Am măsurat valorile propuse față de fundalul real al
site-ului, înainte de a atinge CSS-ul. Rezultatul a schimbat trei din patru decizii.

| Propus | Contrast pe `--paper` (#fbfaf7) | Verdict |
|---|---:|---|
| verde `#4E9F6E` / `#2E6F40` | 3,09:1 / 5,81:1 | al doilea trece, dar…
| albastru `#3B82F6` | 3,52:1 | **pică AA** pentru text; în plus se bate cap în cap cu `--navy`, culoarea de acțiune |
| albastru `#60A5FA` | 2,44:1 | pică și pe tema deschisă, și pe cea întunecată (5,14:1 doar pe dark) |
| ocru `#D97706` | 3,05:1 | **pică AA** |
| indigo `#6366F1` | 4,28:1 | pică pragul de 4,5:1 la text mic (etichetele au 11–13px) |

**Ce s-a livrat, cu valori măsurate:**

| Token | Valoare | Contrast pe `--paper` | Rol |
|---|---|---:|---|
| `--ok` | `#2f6b46` (existent) | 6,07:1 | confirmat de origini independente |
| `--warn` | `#8a6414` (existent) | 5,14:1 | o singură origine / neconfirmat reciproc |
| `--live` | `#b23a2e` (existent) | 5,69:1 | **divergență între relatări** |
| `--infer` | `#5b54a8` (nou) | 6,14:1 | formulare cu rezervă la sursă; deducere |

Verdele, ocrul și roșul **existau deja** și erau deja folosite epistemic (punctul din card:
`.trust--ok/--single/--div`). Schimbarea lor ar fi fost o regresie de contrast, nu o
îmbunătățire — deci nu s-au atins. Ce lipsea nu era paleta, ci **acoperirea** ei: marca
exista doar pe card și pe rândul de stare, iar „cu rezervă la sursă" era un `<em>` fără
culoare, adică invizibil ca stare. Noul token umple exact golul care nu avea culoare.

`--live` se folosește **doar** pentru divergență (`--trust--div`, bordura `.dialectic-diverg`).
Nu există și nu are voie să apară un token pentru „breaking", „urgență", „tragedie": regula
de aur e verificată de `tests/test_culoare_semantica.py::test_nu_exista_culoare_marcata_pentru_emotia_stirii`.

**Greutate:** CSS 89.137 → 91.837 B raw (23.486 → 24.508 B gzip, **+1,0 KB gzip**), din care
~700 B sunt comentariul-regulă din capul fișierului, care nu ajunge la cititor după minificare
la deploy. HTML: +~430 B pe pagină de sinteză (legenda, o dată pe pagină), 183 de marcaje de
rezervă în tot build-ul.

**Acoperire pe build-ul real** (6.659 articole, `--render-only`):

| Element | Pagini |
|---|---:|
| Legendă (sinteze cu conținut epistemic) | 346 |
| Marcaj „cu rezervă la sursă" | 183 |
| Legendă care explică `--div` (relatări care se contrazic) | 41 |
| Legendă care explică `--infer` | 118 |

Cifra mică nu e un defect de implementare: doar 6,2% din conținut e sinteză multi-sursă
(`analiza/2026-11-07-analiza-multidimensionala.md` §1). Pe restul, orice legendă ar fi promis
o distincție care nu se vede în text — de aceea legenda se emite condiționat, per pagină.

**Ce rămâne nemăsurat aici:** Lighthouse/pa11y (sandboxul nu are Chromium; `tools/audit.sh`
rulează pe PR în `editorial-frontend-audit.yml`). Contrastul de mai sus e calculat WCAG pe
valori hex, nu citit din pixeli randați — deci e limita superioară a încrederii, nu dovada
finală. Cifrele de greutate sunt locale, comparabile doar înainte/după pe aceeași mașină.
