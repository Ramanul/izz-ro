# IZZ.ro — propunere de rebranding vizual

**Data:** 7 noiembrie 2026 · **Stare:** propunere, fără modificări în producție
**Machetă interactivă:** `analiza/rebranding/index.html` (patru file: Direcții · Prima pagină · Articol · Sistem)
**Legătură cu auditul:** `analiza/2026-11-07-analiza-multidimensionala.md` (§3 performanță, §6 UX, §7 accesibilitate)

---

## 1. Diagnostic: de ce arată „obosit” un site bine gândit

Identitatea actuală — numită în CSS „Cronică aurie” — este un omagiu conștient adus ziarului tipărit: serif Playfair, auriu, linii subțiri, majuscule mono, sigilii de dată, proporția de aur. Ideea e bună, execuția s-a supraîncărcat. Șase observații măsurabile:

1. **Prea multe elemente cu aceeași greutate.** Un card are 7 straturi: badge auriu, trust-label auriu, ilustrație, titlu, dată, „~1 min”, rezumat, surse. Toate strigă la fel, deci ochiul nu știe de unde să înceapă. Pe prima pagină sunt 60 de astfel de carduri.
2. **Trei familii de fonturi, șapte fișiere (104 KB).** Playfair 700/800, Inter 400/600/700, JetBrains Mono 400/700. Mono-ul apare în badge-uri, meta, surse, butoane, subsol — adică peste tot unde ar trebui să fie interfață discretă.
3. **Auriu peste tot, deci nicăieri.** `--gold`/`--gold-strong` colorează linkuri, badge-uri, trust-label-uri, titluri de secțiune (prima literă), butoane, newsletter. Când accentul e pretutindeni, nu mai e accent.
4. **Arta generativă e identitate, dar și zgomot.** 60 de SVG-uri inline pe prima pagină (455 KB, 76% din greutate), 24 din 49 de scene sunt aceeași variantă (`warm_geometry`). Pe ecran, cardurile arată ca o bandă decorativă, nu ca știri diferite.
5. **Brandul se repetă de trei ori în antet** (eyebrow „Portalul știrilor tale”, logo, descriptor), plus data, plus numerele zilei. Antetul consumă primul ecran pe mobil.
6. **Ierarhia tipografică e „matematică”, nu optică.** Scara φ (0,618 · 0,786 · 1 · 1,272 · 1,618…) produce treceri neuniforme percepute: 1,27 → 1,61 e o diferență mare, 0,786 → 1 e mică. La text de 12–13 px, Playfair își pierde eleganța.

Concluzia: **nu trebuie schimbat ce spune site-ul, ci cât de repede se vede ce spune.**

---

## 2. Poziționare și principii

**Ideea de brand:** *„Știrile tale, fără zgomot”* — un ziar care respectă timpul cititorului. Vizual, asta înseamnă **ierarhie, nu decor**.

Trei principii care decid orice detaliu:

1. **Un singur lucru important pe ecran.** Un titlu mare, un accent, o acțiune. Restul se supune.
2. **Culoarea este semantică, nu ornamentală.** Navy = acțiune/link. Aramă = semnătură de brand (punctul din wordmark, linii). Roșu = doar „ultima oră”. Verde/galben/roșu = doar nivel de confirmare, sub formă de punct + formă.
3. **Serif pentru citit, sans pentru operat.** Orice text de citit (titluri, dek, corp) e serif; orice text de interfață (etichete, meta, butoane) e sans. Mono dispare.

---

## 3. Trei direcții

| | **A. Hârtie curată** *(recomandat)* | **B. Sistem** | **C. Nocturn** |
|---|---|---|---|
| Fonturi | Newsreader + Inter | Inter doar | Newsreader + Inter |
| Accent | aramă (semnătură) + navy (acțiune) | culori de date pe categorii | aramă pe negru |
| Ton | ziar contemporan | serviciu informațional | revistă premium |
| Plus | continuitate, lizibilitate, cost mic | densitate, scalabilitate | memorabil |
| Minus | mai puțin „spectaculos” | pierde autoritatea editorială | obosește; cere fotografii care nu există |
| Cine câștigă | cititorul care revine zilnic | utilizatorul de hartă/unelte | prima impresie |

**Recomandare: A.** Este o evoluție, nu o ruptură: păstrează seriful, albul cald și arama (capitalul de brand acumulat), dar le mută din text în structură. B ar fi o schimbare de poziționare (ziar → dashboard), prea mare pentru un site care încă își construiește autoritatea. C ar arăta bine pe un ecran de prezentare și rău pe telefon, dimineața, când 82% din articole nu au fotografie.

---

## 4. Sistemul A, în detaliu

### 4.1 Culoare

| Rol | Token | Valoare | Contrast | Întrebuințare |
|---|---|---|---:|---|
| Hârtie | `--paper` | `#FBFAF7` | — | fundal |
| Cerneală | `--ink` | `#14161A` | 16,7:1 | titluri, corp |
| Text secundar | `--ink-2` | `#4A515C` | 7,6:1 | dek, rezumate |
| Meta | `--ink-3` | `#6F7683` | 4,8:1 | dată, sursă secundară |
| Acțiune | `--navy` | `#173A5E` | 11,3:1 | linkuri, butoane, focus |
| Brand | `--brass` | `#A8823A` | decor | punctul din wordmark, linii, kicker |
| Brand text | `--brass-deep` | `#7C5F22` | 5,6:1 | kicker pe hârtie |
| Confirmat | `--ok` | `#1F6F63` | 5,9:1 | punct la „2 publicații · confirmat” |
| O singură origine | `--warn` | `#9A7B2E` | 4,9:1 | romb |
| Divergent / live | `--live` | `#B23A2E` | 5,6:1 | „ultima oră”, relatări divergente |
| Linii | `--line` / `--rule` | `#E7E4DD` / `#D3CEC3` | — | separatoare |

Regula de aur (literal): **arama nu mai colorează niciodată un link sau un text de interfață.** Doar semnătura, kicker-ul de categorie și firele de 2 px.

### 4.2 Tipografie

- **Newsreader** (variabilă, 86 KB latin-ext, subsetabilă la ~28 KB cu `tools/fetch_fonts.py`) înlocuiește Playfair 700 + 800. Motive: contrast mai mic la dimensiuni mici (deci diacritice românești mai solide), axă optică, aspect contemporan fără să pară „revistă glossy”.
- **Inter** rămâne pentru interfață, dar doar 400 și 600. **JetBrains Mono dispare**; cifrele primesc `font-variant-numeric: tabular-nums`.
- Scară: **12 · 13 · 14,5 · 16,5 · 19 · 21 · 26 · 32 · 44** (raport ~1,22).
- Titluri: `letter-spacing: -0.02em`, `line-height: 1.06–1.2`. Corp: 19 px / 1,62, măsură 66–70 caractere (712 px).
- Rezultat pe disc: 104 KB → **~50 KB** de fonturi, 7 fișiere → 3.

### 4.3 Spațiu, grilă, formă

- 1180 px maxim, margini 28 px (16 px mobil), 12 coloane, gutter 32 px.
- Ritm vertical pe 8 px; secțiuni la 52 px; separatoare de 1 px, fără chenare, fără umbre.
- Rază 4 px doar la imagini, butoane și cipuri. Fără „carduri” cu fundal: conținutul stă pe hârtie, separarea se face prin linii.

### 4.4 Componente-cheie (schițate în machetă)

| Componentă | Acum | Propus |
|---|---|---|
| **Antet** | eyebrow + logo 3 rânduri + descriptor + dată + numere + 2 rânduri de navigație | wordmark `izz.` + tagline pe un rând, navigație pe un rând, banda de categorii, un rând de status (dată · articole → subiecte · surse · județe · actualizat) |
| **Briefing** | listă de 7 titluri într-o coloană, apoi un link | listă pe două coloane, oră tabulară + titlu + categorie/sursă |
| **Lead** | card mare + aside cu surse | fotografie 16:9 + titlu 38 px + dek + un rând de meta; aside: „ultima oră” + 2 titluri + intrare spre hartă |
| **Card** | 7 elemente | 4 elemente: kicker · titlu · dek o linie · meta (trust + oră + sursă) |
| **Trust** | trust-label auriu, mono, majuscul, text lung | un singur rând: punct colorat + formă + 3–5 cuvinte |
| **Articol** | fără imagine, 3 casete de disclaimer | imagine (dacă există) sau deschidere tipografică, corp serif 19 px, bandă de context, „ce confirmă sursele”, surse cu rol, un rând de divulgare |
| **Footer** | 13 linkuri pe un rând, mono | 3 coloane + bloc „Susține IZZ” + promisiunea de brand |

### 4.5 Imagini și artă generativă

Problema nu e arta, ci cantitatea și uniformitatea. Propunere — **„coperți v2”, trei tipuri, maximum 8 pe pagină**:

1. **Fotografie licențiată** (Commons, CC0/PD, eveniment) — când există, e eroul cardului, 16:9, credit discret.
2. **Copertă tipografică** — tipul documentului + entitatea + data, pe hârtie, cu un fir de aramă. Zero fișiere, zero cereri, un singur format (CSS). Înlocuiește 60 de SVG-uri cu 8 compoziții per pagină.
3. **Portret de arhivă** — pentru știrile cu persoane publice (deja există `data/portraits.json`), tratat unitar: 1:1, 160 px, cu credit.

Efecte laterale dorite: prima pagină 595 KB → sub 200 KB; dispare problema ID-urilor duplicate (`art-gold-grad`); dispare monotonia `warm_geometry`.

### 4.6 Mișcare și mod întunecat

- Tranziții 120–180 ms, doar `color`, `border-color`, `transform`. Fără animații la scroll pe liste (azi există `intra-in-pagina` pe fiecare card).
- Mod întunecat: `#0F1115` hârtie, `#E9E6DF` cerneală, aramă `#D3B26A`, linkuri `#A9C7E9`. Se comută din bara machetei.

### 4.7 Accesibilitate inclusă în design

- Toate perechile de text ≥ 4,5:1 (tabelul din 4.1).
- Etichetele de încredere au **formă + culoare** (cerc / romb / pătrat), deci funcționează și fără percepția culorii.
- Ținte ≥ 44 px pe mobil; focus vizibil navy 2 px, offset 3 px.
- Link „Sari la conținut”, fără emoji în titluri, fără `autofocus`.
- Fără text în imagini (în afară de coperțile tipografice, care sunt text real).

---

## 5. Implementare în repo

### 5.1 Faze

| Fază | Ce se schimbă | Fișiere | Rezultat măsurabil |
|---|---|---|---|
| **0. Tokeni** | culori, scară, spațiere — fără atingerea șabloanelor | `static/styles.css` (`:root`), `theme.js` | zero schimbări vizuale majore, dar o singură sursă de adevăr |
| **1. Tipografie** | Newsreader + Inter 400/600, scara nouă, mono scos din meta | `tools/fetch_fonts.py`, `templates/base.html`, `styles.css` | 104 KB → ~50 KB fonturi |
| **2. Antet + footer** | wordmark, navigație pe un rând, status line, footer pe coloane | `templates/base.html`, `styles.css` | primul ecran pe mobil câștigă ~90 px |
| **3. Card + prima pagină** | card cu 4 elemente, briefing pe 2 coloane, lead cu fotografie, maximum 24 de carduri | `templates/_card.html`, `templates/index.html`, `render.py` | prima pagină ≤ 200 KB |
| **4. Articol** | corp serif 19 px, bandă de context, „ce confirmă sursele”, un rând de divulgare | `templates/article.html`, `_editorial_relations.html` | 0 pagini fără linkuri interne |
| **5. Coperți v2** | 8 compoziții per pagină, CSS-only, fără SVG inline | `templates/_art.html`, `generator/htmlart.py`, `styles.css` | −450 KB pe prima pagină |
| **6. Restul paginilor** | categorie, hartă, ghiduri, instrumente, căutare | șabloanele respective | consistent vizual |

Fiecare fază e livrabilă separat și se poate publica independent; hash-ul de conținut al CSS-ului (`asset_ver`) sparge cache-ul automat.

### 5.2 Mapare de variabile (vechi → nou)

| Vechi | Nou | Notă |
|---|---|---|
| `--paper: #f6f7f9` | `--paper: #FBFAF7` | alb cald, nu alb-albastru |
| `--ink: #15171c` | `--ink: #14161A` | neschimbat perceptual |
| `--ink-2: #4d5562` | `--ink-2: #4A515C` | |
| `--ink-3: #6d6d7f` | `--ink-3: #6F7683` | 4,8:1 |
| `--gold: #c9a227` | `--brass: #A8823A` | doar decor |
| `--gold-strong: #8b6918` | `--brass-deep: #7C5F22` + `--navy: #173A5E` | linkurile trec pe navy |
| `--gold-wash: #faf5e6` | `--sunk: #F3F1EC` | fără bej în casete |
| `--fs-*` (φ) | scară 1,22 | 12…44 |
| `--s-*` (Fibonacci 5/8/13/21/34/55/89) | 4/8/12/16/24/32/48/64/96 | ritm pe 8 |
| `--font-mono` | eliminat | cifre tabulare în Inter |

### 5.3 Riscuri și atenuări

| Risc | Atenuare |
|---|---|
| Pierderea recunoașterii (arama dispare din linkuri) | arama rămâne în wordmark, kicker și fire de 2 px — e semnătura, doar nu mai e text |
| Regresii de șablon | faza 0–2 nu atinge HTML; fazele 3–6 trec prin testele de randare (propunere I3 din audit: `pytest -m "render or template"` blocant) |
| CSP | fără stiluri inline noi; tot ce e culoare/tipografie stă în `styles.css` |
| Cache | `?v=<hash>` deja există pentru CSS și JS |
| Font nou = fișier nou | `tools/fetch_fonts.py` subțiază la charset RO; licență OFL, fără cost |
| „Prea multă schimbare deodată” | fazele se pot opri după oricare; macheta arată ținta finală, nu obligă la ea |

### 5.4 Ce NU se atinge

- **URL-uri, canonical, JSON-LD, sitemap-uri** — zero impact SEO.
- **Textele editoriale, politicile, etichetele AI Act** — se reformulează doar vizual, nu se elimină.
- **Hartă, căutare, PWA** — primesc doar tokenii noi; logica rămâne.
- **Zero reclame, zero tracking** — rebrandingul nu e prilej de monetizare.

---

## 6. Cum măsurăm succesul

| Indicator | Acum | Țintă după rebranding |
|---|---:|---:|
| Greutate prima pagină (gzip) | 108 KB | **≤ 45 KB** |
| Greutate pagină articol (gzip) | 20,5 KB | ≤ 22 KB (crește conținutul, nu șablonul) |
| Fonturi | 86 KB / 7 fișiere (măsurat: 87.960 B) | **≤ 55 KB / 3 fișiere** |
| Elemente cu greutate vizuală pe card | 7 | **4** |
| Carduri pe prima pagină | 60 | ≤ 24 |
| Pagini fără nicio imagine/context | 82% | ≤ 40% |
| Contrast minim text | 4,73:1 | ≥ 4,5:1 (păstrat) |
| CSS | 3 fișiere / 84 KB | **1 fișier / ~50 KB** |

Măsurare: `analiza/masuratori.py` (bytes, elemente, imagini), `tools/greutate.py` (greutate pe tip de pagină), plus un test de contrast în CI.

---

## 7. Ce nu propun

- **Nu propun un logo nou dramatic.** `izz.` cu punct de aramă e deja memorabil; îi trebuie doar o construcție corectă (wordmark, favicon, iconiță PWA identice) — nu o rebranding de nume.
- **Nu propun fotografii de presă.** Politica imaginilor e un avantaj etic și juridic; coperțile tipografice sunt răspunsul corect la 82% articole fără fotografie.
- **Nu propun pagini „revistă”.** Un singur titlu mare pe ecran, nu trei.
- **Nu propun dark-first.** Modul întunecat rămâne o preferință, nu identitatea.
- **Nu propun schimbarea structurii de informație.** Categoriile, harta, ghidurile, dosarele rămân exact unde sunt.

---

## 8. Stadiu implementare (7 noiembrie 2026)

Direcția A a intrat în repo. Fazele 0 (tokeni) și 1 (tipografie) sunt livrate, cu șabloanele
atinse doar la nivel de fonturi; restul paginilor arată deja în noua identitate pentru că totul
trece prin tokeni.

### 8.1 Ce s-a schimbat

| Fișier | Schimbare |
|---|---|
| `static/styles.css` | `:root` rescris: culoare (hârtie caldă, tuș, navy pentru acțiuni, aramă doar decor), scară tipografică 1,22, ritm de spațiere pe 4 px, `--navy` nou, `--font-display` = Newsreader, `--font-mono` = Inter (mono scos din UI, cifre tabulare prin `font-variant-numeric`); linkuri/focus/butoane mutate din aramă în navy; titluri 800 → 600, titluri de card 700 → 400; blocul dark recalibrat |
| `static/styles.css` (componente) | `color: #fff` fix pe fundaluri care se inversează în tema întunecată (`.btn-source`, paginare, hover pe butoane-icon) → `var(--paper)`, care se întoarce o dată cu fundalul; butonul de instalare PWA a pierdut gradientul metalic auriu (navy solid) |
| `static/fonts.css` | 5 fețe: Newsreader 400/600 + Inter 400/600/700. Playfair și JetBrains Mono au ieșit |
| `static/fonts/` | `Newsreader-400.ro.woff2` + `Newsreader-600.ro.woff2` (subset RO, instanțe statice din variabila OFL); cele 4 fișiere Playfair/JetBrains șterse |
| `templates/base.html` | preload doar pe Newsreader 600 + Inter 400 (cele două fețe din primul ecran) |
| `tools/fetch_fonts.py` | aceleași familii, ca o rulare viitoare a jobului `fonts` să nu readucă Playfair |
| `static/sw.js` | `PRECACHE` cu fonturile noi, `SHELL` v3 → v4 (cache-urile vechi se aruncă) |
| `static/site.css` | treptele fluide `--fs-2xl/3xl` aliniate la scara nouă |

### 8.2 Măsurători față de țintă

| Indicator | Înainte | Acum | Țintă | Verdict |
|---|---:|---:|---:|---|
| Fonturi | 87.960 B / 7 fișiere | **76.224 B / 5 fișiere** | ≤ 55 KB / 3 fișiere | −13%, ținta nu e încă atinsă |
| Prima pagină (gzip) | 109.205 B | 109.179 B | ≤ 45 KB | neschimbat — 76% e arta inline, faza 3 |
| Articol (gzip) | 20.563 B | 20.542 B | ≤ 22 KB | în limite |
| Contrast minim (text mic) | 4,73:1 | **4,74:1** | ≥ 4,5:1 | AA păstrat |
| CSS | 4 fișiere / 84 KB | 4 fișiere / 85 KB | 1 fișier / ~50 KB | faza 6 (consolidare) |

Măsurătorile „înainte" sunt contrafactuale pe aceeași pagină randată (blocul de fonturi din `HEAD`
pus înapoi în `<head>`), nu o randare separată: markup-ul e identic, deci diferența e efectul
slice-ului. Detalii și tabelul de contrast complet: `specs/masuratori-frontend.md`.

De ce fonturile nu coboară la 3 fișiere: Newsreader are nevoie de două fete (400 pentru titlurile
de card, 600 pentru titlurile mari), iar Inter 700 nu poate fi scos fără bold sintetizat la
`<strong>` din corpul articolelor. Câștigul vine din scoaterea Playfair (34.940 B) + JetBrains
Mono (15.580 B), minus Newsreader (38.784 B). Sub 55 KB s-ar ajunge doar tăind din Inter
(400/600/700 = 37.440 B) — o discuție de faza 6, cu măsurat înainte/după pe A11y.

### 8.3 Verificări

- `pytest`: 3100 passed, 4 skipped, 8 xfailed — inclusiv `test_arta_inline`, `test_pwa` (precache),
  testele de randare; `ruff check .` curat; CSS validat cu `csstree-validator` (singurul avertisment
  rămas e preexistent, `url(#art-gold-grad, var(--art-geo-aur))`).
- Etichetele din arta generativă se desenează acum cu Newsreader, care e cu 13–30% mai îngustă
  decât Playfair la același corp: pragurile `--art-et-k` rămân valide ca limită de sus (nimic nu
  se mai taie), dar textul arată mai mic în același chenar. Remăsurarea pe Newsreader e treaba
  fazei 5, împreună cu arta v2.

### 8.4 Ce urmează

1. **Faza 2** — masthead și footer: wordmark `izz.` construit corect (un singur weight, punct de
   aramă), bara de sus mai subțire, footer pe 3 coloane cu mai puțin text mono-uppercase.
2. **Faza 3** — cardul de la 7 la 4 elemente + prima pagină cu ≤ 24 de carduri; aici scade și
   greutatea (arta inline 455 KB e ținta reală, nu fonturile).
3. **Faza 5** — arta generativă v2 + recablarea etichetelor; opțional, aceeași instanță Newsreader
   și pentru coperțile raster (`generator/htmlart.py`, `generator/covers.py`), ca rasterul și SVG-ul
   din pagină să nu mai folosească două serife diferite.
4. **Faza 6** — consolidarea CSS-urilor (`site.css`, `faza2.css` în `styles.css`), rampa hărților
   mutată pe aramă, paginile utilitare.

> Notă despre `tools/fetch_fonts.py`: sandbox-ul de lucru nu are acces la `fonts.googleapis.com`,
> deci cele două fișiere Newsreader au fost produse local din fontul variabil OFL (instanțiere
> `wght` 400/600, apoi subsetare pe `RO_UNICODES` + unire latin/latin-ext pentru diacritice).
> Jobul `fonts` din Actions, rulat pe noile familii, trebuie să dea aproximativ aceleași fișiere —
> de confirmat la prima rulare manuală.

---

## Anexă: fișierele propunerii

| Fișier | Ce conține |
|---|---|
| `analiza/rebranding/index.html` | macheta interactivă: direcții, prima pagină, articol, sistem (tokeni, tipografie, componente, before/after) |
| `analiza/rebranding/fonts/newsreader-var.woff2` | Newsreader variabilă (latin-ext), OFL — folosită doar în machetă |
| `analiza/rebranding/fonts/LICENSE-Newsreader.txt` | licența SIL OFL 1.1 |
| acest document | raționamentul, tokenii, planul de implementare |
