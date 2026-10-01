# Dimensiunea 5 — greutatea primei încărcări, măsurată

**Măsurat:** 2026-09-04, cu `tools/greutate.py`, pe o randare locală completă
(`python -m generator.main --render-only`) — **13.430 de pagini**.

**Ce e:** dimensiunea 5 din `specs/dimensiuni.md` avea doar eticheta „perf front-end", fără
definiție. Definiția aleasă: *câți octeți plătește cititorul ca să deschidă o pagină, și din ce
sunt făcuți.* Nu dublează §13 — `tools/audit.sh` dă scoruri Lighthouse pe câteva pagini și cere
Chromium; asta măsoară static, pe toate paginile, **compoziția**.

## Cifra de ansamblu

```
13.430 pagini · mediana primei încărcări 127 KB · cea mai grea 508 KB
```

## Compoziția, pe cele patru tipuri de pagină

| pagină | HTML | eager | cereri | lazy |
|---|---|---|---|---|
| `index.html` (home) | 123 KB | **201 KB** | 65 | 1.090 KB (65 imagini) |
| `local/index.html` | 40 KB | 154 KB | 23 | 337 KB |
| `judetean/index.html` | 40 KB | 124 KB | 15 | 400 KB |
| articol (13.400 pagini) | 13 KB | **116 KB** | 6 | 0 KB |

## Constatarea principală: șasiul costă de 7× cât conținutul

Pe o pagină de articol — adică pe **99,8% din site** — greutatea se împarte așa:

```
  CSS      50 KB  ┐
  fonturi  25 KB  ├─ 93 KB identice pe toate paginile = „șasiu"
  JS       18 KB  ┘
  ────────────────
  HTML     13 KB  ← singurul lucru diferit de la o pagină la alta
  copertă  23 KB
```

Șasiul se cache-uiește după prima vizită. Dar traficul de căutare și de rețele sociale
aterizează direct pe un articol, o dată — deci cazul tipic **este** prima vizită, iar acolo
cititorul plătește 129 KB ca să primească 13 KB de text.

[INTERPRETARE] Cel mai mare element unic e CSS-ul, 50 KB, adică 39% din greutatea unui articol.
Întrebarea următoare, nemăsurată încă: **cât din el se aplică efectiv unei pagini de articol?**
Un `styles.css` care servește și harta, și homepage-ul, și paginile de categorie, e prin
construcție mai mare decât are nevoie orice pagină în parte.

## Reverificat pe 2026-09-04, pe alt set de date

Măsurătoarea de mai sus a fost repetată dintr-o randare complet nouă (`output/` gol la start,
31.011 imagini regenerate), pe conținutul de peste zi: **14.773 de pagini** în loc de 13.430.
Faptul că e alt eșantion e tocmai ce face reverificarea utilă — arată ce ține la schimbarea de
conținut și ce nu.

| | prima măsurătoare (13.430 pag.) | reverificare (14.773 pag.) |
|---|---|---|
| mediana primei încărcări | 127 KB | **127 KB** |
| cea mai grea pagină | 508 KB | **508 KB** |
| CSS pe un articol | 50 KB | **50,1 KB** |
| fonturi | 25 KB | **24,7 KB** |
| JS | 18 KB | **18,0 KB** |
| **șasiu** | **93 KB** | **92,8 KB** |
| copertă | 23 KB | 20,0 KB (`.jpg` 15,5 + `.webp` 4,5) |
| HTML pe un articol | 13 KB | 14,3 KB |
| cereri pe un articol | 6 | 7 |

**Ce ține:** șasiul, la zecime de KB — normal, sunt fișiere din repo, nu conținut. Și mediana,
la kilobyte, deși s-au adăugat 1.343 de pagini.

**Ce s-a mișcat:** coperta (20 KB în loc de 23) și numărul de cereri (7 în loc de 6) — o copertă
se servește ca `<picture>` cu `.webp` plus `.jpg` de rezervă, deci două cereri, iar mărimea ei
depinde de imaginea concretă. Cifra de 23 KB din prima măsurătoare nu era greșită; era media
altui set de coperți.

**Riscul declarat atunci se închide:** prima măsurătoare a fost făcută dintr-o randare tăiată de
timeout, cu suspiciunea că un subset de coperți lipsește și trage media în jos. Randarea asta a
mers până la capăt (`>> Render-only: 13198 articole din state -> output/`), iar mediana e
aceeași. Nu lipsea nimic.

## Corecție la `IZZ-0237`

Rândul din registru spune *„home trage acum 1.256 KB de imagini pe 62 de carduri"* (2026-08-22).
Măsurat azi: 1.090 KB lazy + 109 KB eager = **1.199 KB de imagini**, pe 130 de referințe. Ordinul
de mărime se confirmă.

**Dar cifra e înșelătoare ca impact, și asta contează mai mult decât confirmarea:** 87% din ea e
`loading="lazy"`, deci nu intră în prima încărcare. Prima încărcare reală a homepage-ului e
**324 KB** (123 HTML + 201 assets). O optimizare de imagini pe homepage ar ataca 1.199 KB dintre
care 1.090 nu se descarcă niciodată pentru cine nu derulează.

Amestecul eager/lazy e chiar motivul pentru care `tools/greutate.py` le raportează separat.

## Ce NU spun cifrele astea

- **Nu e transfer real.** Sunt octeți pe disc: fără gzip/brotli de la Cloudflare (CSS-ul de 50 KB
  probabil pleacă sub 12 KB comprimat), fără cache-ul vizitatorului, fără HTTP/2.
- **Totalul pe tip de fișier, peste toate paginile, nu înseamnă nimic.** Unealta îl tipărește
  (`.css 657 MB`), dar e același `styles.css` numărat de 13.430 de ori. Comparabilă e cifra
  **per pagină**, nu suma.
- **Nu e un scor.** Nu înlocuiește Lighthouse din §13; spune din ce e făcută greutatea, nu cât de
  bine se comportă pagina la încărcare.
- **Nu numără cererile externe, și sunt trei, nu una.** Unealta sare deliberat peste `https://`
  (nu poate ști mărimea unui fișier de pe alt domeniu fără rețea), iar două dintre cele trei nici
  măcar nu apar în HTML — sunt injectate din JS la runtime, deci nicio unealtă care citește HTML
  nu le poate vedea:

  | ce | de unde | poartă |
  |---|---|---|
  | `beacon.min.js` | `templates/base.html:53` | `analytics_token` |
  | `googletagmanager.com/gtag/js` | `static/personalize.js:305`, `s.src=` | `eProductie()` **+ opt-in** |
  | `clarity.ms/tag/…` | `static/personalize.js:331`, `s.src=` | `eProductie()` **+ opt-in** |

  Toate trei au poartă de producție, deci **niciuna nu e în randarea locală**. Prin urmare cei
  116 KB eager de pe un articol nu sunt „greutatea unui articol": sunt **podeaua locală, înainte
  de consimțământ**. În producție, un cititor care acceptă personalizarea încarcă în plus cele
  trei, iar tag-ul Clarity mai cheamă la rândul lui `scripts.clarity.ms` și un host de colectare
  (`n.clarity.ms`, măsurat 2026-08-13 — vezi comentariul din `personalize.js`).

  [INTERPRETARE, din cunoștințe generale, NU dintr-o măsurătoare a acestui site] `gtag.js` e în
  mod obișnuit de ordinul zecilor bune de KB, deci greutatea third-party nemăsurată poate fi
  comparabilă cu întreg șasiul de 93 KB. **Nu am nicio cifră proprie și nu inventez una.**
  Măsurarea ei cere un browser real cu opt-in acceptat — adică §13, nu unealta asta.

## Cum se reface

```bash
python -m generator.main --render-only   # ~25 min; imaginile se refolosesc dacă output/ există
python tools/greutate.py 12              # top 12 pagini + compoziția pe tip
```

Șasiul (93 KB) se verifică însă **fără randare, în ~1 secundă** — sunt fișiere din repo, iar
`base.html` spune exact care: `static/styles.css` (51.298) + cele două `preload` woff2,
Playfair-800 și JetBrainsMono-700 (25.280) + `theme.js` și `personalize.js` (18.452) =
**95.030 octeți = 92,8 KB**. Reverificat astfel pe 2026-09-04, independent de randare.

---

## Corecție 2026-09-05: cifrele de mai sus sunt pe DISC, iar pe sârmă compoziția se inversează

Secțiunea „Ce NU spun cifrele astea" declara onest că măsurătoarea e pe disc și presupunea în
paranteză *„CSS-ul de 50 KB probabil pleacă sub 12 KB comprimat"*. Presupunerea a fost măsurată:

| | pe disc | pe sârmă (gzip -9) | cotă din șasiu, pe sârmă |
|---|---|---|---|
| `styles.css` | 51.298 | **11.769** | 27% |
| fonturi preload (2 × woff2) | 25.280 | **25.280** — deja comprimate | **58%** |
| `theme.js` + `personalize.js` | 18.452 | **6.638** | 15% |
| **șasiu** | **95.030 = 92,8 KB** | **43.687 = 42,7 KB** | |

HTML-ul unui articol: mediana 14.656 → **3.972** octeți gzip (n=400 pagini reale, raport 0,27).
Cloudflare servește brotli, deci cifrele de pe sârmă sunt limite superioare.

**Ce schimbă asta.** Șasiul e sub jumătate din cifra publicată. Și, mai important, **ordinea se
inversează**: pe disc CSS-ul e cel mai mare element (54% din șasiu), pe sârmă sunt fonturile (58%),
fiindcă woff2 e deja comprimat și nu se mai strânge. Constatarea „șasiul costă de 7× cât conținutul"
se *întărește* pe sârmă, nu se înmoaie — jumătatea de conținut se comprimă la 27%, jumătatea de
șasiu aproape deloc.

**Deci întrebarea deschisă de mai sus țintea al doilea element ca mărime, nu primul.** [OPINIE]
Rămâne totuși întrebarea corectă de pus prima: fonturile sunt mari dar aproape netăiabile (deja
subset românesc, exact două fețe preload, iar scoaterea uneia e decizie de design, §8), pe când
CSS-ul e tăiabil. „Cel mai mare" și „cel mai tăiabil" nu sunt același lucru.

## Răspunsul la întrebarea deschisă: cât din CSS se aplică unei pagini de articol

Măsurat cu `tools/css_folosit.mjs` (Chromium prin CDP, `CSS.startRuleUsageTracking` +
`takeCoverageDelta`), pe 6 articole + cele trei indexuri, în două viewporturi.

```
51.298 octeti  = 41,6 KB in reguli (363)  +  8,5 KB comentarii/spatii/preambul @media
```

Contabilitate pe octeți de regulă, ca să fie comparabilă cu restul dimensiunii. **Nu un procent
unic**, fiindcă o regulă neatinsă la prima randare nu e o regulă moartă:

| stare condusă | prima dată folosit aici |
|---|---|
| prima randare | 12,7 KB · 89 reguli |
| personalizare (consimțământ + panou) | 2,4 KB · 16 |
| derulare până jos | 0,0 KB · 1 |
| hover / focus | 0,3 KB · 4 |
| temă întunecată | 0,9 KB · 6 |
| mobil (390px), prima randare | 0,6 KB · 8 |
| mobil, personalizare | 0,1 KB · 1 |
| **total folosit** | **17,0 KB = 40,9% din reguli** |

Pe tip de pagină: home 39,9% · articol 39,8% · local 34,6% · județean 34,6%. **Nicio pagină nu
folosește mai mult de 40%** — șasiul CSS e comun prin construcție, deci fiecare pagină plătește
pentru suprafețele celorlalte.

**Neatins de nicio pagină, în nicio stare: 19,6 KB, 192 de reguli.** Cele mai mari grupuri:
`Pagini utilitate` (6,0 KB, 56 reguli), `/surse/` (3,0 KB), `Căutare` (2,6 KB),
`orientare editorială` (1,7 KB) — adică suprafețe care există, dar nu se ating de pe cele patru
tipuri de pagină măsurate.

### Cât valorează tăierea — MĂSURAT, nu estimat

Am scos cele 192 de reguli din fișier și l-am recomprimat:

```
brut    51.298 -> 31.215   (-39%)
gzip-9  11.769 ->  8.930   (-24%,  -2.839 octeti)
```

**Tot premiul e 2,8 KB pe sârmă**, adică ~4% dintr-o pagină de articol. Cauza e instructivă:
regulile moarte sunt repetitive, deci gzip le mânca deja aproape gratis — 39% din fișier
înseamnă 24% din octeții transmiși.

[OPINIE] **Deci: nu tăiați CSS-ul pentru greutate.** Cei 19,6 KB rămân un semnal de întreținere
(dimensiunea 7 aplicată pe CSS), nu o optimizare de performanță.

### Ce NU spune cifra de 192

„Neatins" = neexercitat de stările conduse de unealtă. O stare la care ea nu ajunge — harta,
un formular trimis, o pagină de eroare, un breakpoint nedeschis — apare tot acolo, pe nedrept.
De-aia unealta conduce stările explicit **și verifică** dacă s-au aplicat: prima versiune raporta
toată tema întunecată drept „neatinsă" fiindcă un clic eșua tăcut pe un element acoperit.

### Cum se reface

```bash
python -m generator.main --render-only      # ~25 min
node tools/css_folosit.mjs --json raport.json
```
