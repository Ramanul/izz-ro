# SPEC — întoarcerea pe Cloudflare Workers **Free** (plafon 20.000 fișiere/versiune)

**Cerere proprietar, 2026-09-09:** din 22 septembrie abonamentul Workers Paid ($5/lună) dispare.
Site-ul trebuie să funcționeze impecabil pe planul **Free**, fără intervenția lui.

## 1. Fapte verificate (nu din memorie)

| Fapt | Cum a fost verificat |
|---|---|
| Workers **Free** = **20.000 fișiere statice / versiune**; Paid = 100.000. Fișier individual max 25 MiB. | `developers.cloudflare.com/workers/platform/limits/#static-assets`, citit prin conectorul Cloudflare pe 2026-09-09 |
| **Cererile către fișiere statice sunt gratuite și nelimitate** — plafonul de 100.000 cereri/zi al planului Free NU se aplică unui Worker assets-only. | `developers.cloudflare.com/workers/platform/pricing/`, nota 3, citit 2026-09-09 |
| Workers Builds (integrarea git care publică la fiecare commit) există și pe Free. | tabelele de limite Workers Builds, „Free Plan" / „Paid Plans", citite 2026-09-09 |
| Free permite **100 de Workers** per cont. | aceeași pagină de limite |
| Starea de azi: **17.147 articole**, mediană **590 articole/zi** pe fereastra de 31 de zile. | `data/articles.json`, histogramă pe `published` |
| Doar **907 din 17.147** de articole (5,3%) vin din surse în altă limbă decât româna. | câmpul `source_lang` din stare |
| **257** de articole au fotografie reală (Wikidata/Commons); restul au artă generată. | `data/leadphotos.json` — 8.796 din 9.053 de intrări sunt marcaje `miss` |
| **2** articole au `event_chart` (meteo). | stare |

## 2. Problema, calculată

`output/` = pagini de articol + imagini de articol + rest (subiecte, paginare, feeduri, static).

Regimul dinainte, proiectat pe date reale (`~3,2 fișiere/articol`):

| TTL | fișiere | % din 20.000 |
|---|---|---|
| 9 zile | 14.773 | 74% |
| 12 zile | 20.965 | **105%** |
| 21 zile | 45.663 | **228%** |
| 30 zile (azi) | 61.620 | **308%** |

Concluziile care contează:

1. **Pe regimul vechi, planul Free permite ~9 zile de arhivă.** Nu 30, nu 21.
2. **„Doar știri din România" NU rezolvă nimic** — 94,7% din articole sunt deja din surse
   românești. Ar tăia ~5% din fișiere dintr-o depășire de 208%. Premisa proprietarului e
   infirmată de date, deci nu se implementează: ar strica acoperirea fără să rezolve plafonul.
3. **Imaginile sunt costul dominant**, nu paginile: ~2,2 fișiere de imagine per articol.

## 3. Observația de primă instanță

Arta per articol **nu e fotografie**. `generator/htmlart.py` o compune din tipografie și
geometrie: fond din paleta site-ului, etichetă majusculă Playfair 800, filete aurii, cercuri,
cifra zilei, un strat de „grain" care e deja un data-URI SVG. Zero figurativ, prin decizie de
design (redesign 2026-08-05).

Deci fiecare articol plătea **2–3 fișiere raster + 2–3 cereri HTTP** ca să transporte un
dreptunghi colorat cu un cuvânt pe el — pe care browserul îl poate desena singur, mai clar
(vectorial, nu 960×504 fix), fără nicio cerere.

**Arta se mută în pagină (HTML/CSS inline).** Nu e o compresie a designului, e eliminarea unui
intermediar raster.

## 4. Ce se schimbă

1. **Plafoanele spun adevărul.** `OUTPUT_FILE_CEILING` 100.000 → **20.000**;
   `OUTPUT_FILE_BUDGET` 90.000 → **17.000** (85% din plafon).
2. **Artă inline.** `htmlart.stil_inline(a)` întoarce stilul (paletă, compoziție, etichetă,
   dată); `templates/_art.html` îl desenează; paleta și mărimile stau în `static/styles.css`
   ca variabile CSS (§8 — fără culori hardcodate în template).
   Nu se mai scriu `art.jpg`, `art.webp`, `art-card.webp`.
3. **`cover.jpg` (og:image) doar pentru fereastra care se distribuie** —
   `OG_COVER_MAX_ARTICLES = 1200` (~2 zile). Mai vechi de atât: og:image pe imaginea
   statică a categoriei, generată o dată per build (15 fișiere).
4. **Fotografiile reale rămân fișiere** (`photo.jpg`/`photo.webp`, `art.jpg` pentru lead-uri
   fără obligație de credit) — sunt fotografii, nu decor generat. La fel articolele cu
   `event_chart`, care au imagine din date.
5. **Restul se subțiază editorial, nu arbitrar.** Pagină de subiect doar de la
   `SUBJECT_MIN_ARTICLES = 3` articole (o pagină cu 2 articole e thin content, nu graf de
   cunoaștere); feed de subiect doar de la `SUBJECT_FEED_MIN_ARTICLES = 12`.
6. **`ARTICLE_TTL_DAYS` 30 → 21.**
7. **Supapă de siguranță la randare.** Dacă proiecția depășește bugetul, randarea taie
   articolele cele mai vechi până intră — plafonul gazdei nu mai poate fi depășit tăcut,
   care e exact incidentul din 2026-08-21 (deploy refuzat, site înghețat 21 h).

## 5. Rezultatul MĂSURAT (două randări complete pe aceeași stare, 2026-09-09)

`python -m generator.main --render-only`, apoi `python tools/count_output.py`:

| | înainte | după | Δ |
|---|---|---|---|
| **total fișiere** | **51.896** (259% din 20k) | **16.732** (83,7%) | **−68%** |
| pagini de articol | 12.519 | 11.600 | supapa taie 875 (vezi mai jos) |
| imagini de articol | 32.702 | 1.246 | **−96%** |
| rest (subiecte, feeduri, paginare, static) | 6.675 | 3.886 | −42% |

**Cifra „înainte" e CONFIRMATĂ PE LIVE, nu doar măsurată local** (2026-09-09 09:41 UTC):

```
$ curl -s https://izz-ro.andifreelancer2.workers.dev/build.json
{"article_count": 12475, "branch": "main", "commit": "6babd4f...", "file_count": 51896, ...}
```

Adică exact ce servește `izz.ro` acum. Fără schimbarea de aici, pe 22 septembrie deploy-ul ar
fi fost refuzat — tăcut, ca în 2026-08-21. Cele trei stări din §5.10 nu se confundă: „înainte"
e **confirmat pe live**, „după" e **verificat local**; pe live se confirmă abia după merge.

Ambele randări sunt făcute pe aceeași stare comisă, care acoperă 30 de zile — TTL-ul de 21 se
aplică abia la prima rulare de pipeline (`state.expire()`). Până atunci supapa taie de la cel
mai vechi, exact pentru ce a fost pusă: 11.600 de articole publicate din 12.475 publicabile.
După prima rulare de pipeline nu mai are ce tăia.

**Preview-ul de ramură al Cloudflare nu e verificabil din sesiune** — măsurat, nu presupus:
`bash tools/verify_allowlist.sh https://claude-cloudflare-free-migration-2sqeju-izz-ro.andifreelancer2.workers.dev/`
→ `[BLOCAT DE PROXY] ... CONNECT refuzat, dar numele se rezolvă în DNS -> nu e în allowlist`,
în timp ce originea de producție răspunde `HTTP 200`. Proprietarul îl poate deschide în browser.

Proiecție pe paginile chiar scrise, grupate pe zi din `output/sitemap.xml` (înainte de supapă):

| TTL | pagini | subiecte+feeduri | paginare | coperți | fixe | **total** | % din 20k |
|---|---|---|---|---|---|---|---|
| 18 | 7.437 | 1.146 | 386 | 1.200 | 1.584 | 11.753 | 58,8% |
| **21** | 9.285 | 1.432 | 479 | 1.200 | 1.584 | **13.980** | **69,9%** |
| 24 | 11.357 | 1.751 | 582 | 1.200 | 1.584 | 16.474 | 82,4% |
| 30 | 12.457 | 1.921 | 637 | 1.200 | 1.584 | 17.799 | 89,0% |

**De ce 21 și nu 30, când și 30 încape (89%).** Pentru că 89% nu e o marjă: rata de intrare din
ultimele zile complete măsurate (730–1.052 articole brute/zi) e peste media de 590 pe care se
sprijină tabelul. La ~700 de articole publicate pe zi, TTL 30 ar sări plafonul, iar supapa ar
scurta fereastra singură — adică arhiva ar oscila zilnic în loc să fie stabilă. La TTL 21,
regimul stă la 70% și absoarbe o creștere de ingest de ~40% înainte ca supapa să atingă ceva.

**21 de zile de arhivă pe Free, față de 9 pe regimul vechi.** Aceasta e valoarea schimbării.

### Efect secundar măsurat: pagini mai ușoare

Homepage-ul are 44 de blocuri de artă și **zero cereri de imagine de articol** (înainte: 44 de
`<img>`). HTML-ul crește (93,5 KB pe home, 13,6 KB pe articol) dar dispar zeci de cereri și
sute de KB de raster. `media/` nu mai crește: `tools/gen_images.py` desenează doar copertele og
din fereastra recentă, cele 15 coperți de categorie și imaginile din date.

## 6. Verificare (§16, ambele roluri)

**Programator.** `python -m pytest tests/ -q` și `python -m ruff check .` verzi.
`python -m generator.main --render-only` → 16.732 de fișiere, sub buget.
`python tools/count_output.py` → rezervă 4.200 ≥ rest măsurat 3.886.

**Utilizator (Chromium 141 headless, `output/` servit pe `127.0.0.1:8899`).** Homepage-ul,
pagina de articol și toate cele patru compoziții randate la 320 / 360 / 729 px, în ambele teme:
arta apare, scalează identic și își păstrează paleta. Homepage-ul face **14 cereri în total,
una singură de imagine** (o fotografie reală de lead).

**Livrabilitate.** Lighthouse 13.4.1, mediane pe 3 repetări: home **Perf 94** (baseline 80),
articol **97** (baseline 88). pa11y WCAG2AA: **0** erori. Detaliile în
`specs/masuratori-frontend.md`.

**Ce NU s-a putut verifica din sesiune:** nimic pe live — schimbarea nu e publicată. Minutele
de build Workers Builds pe planul Free nu sunt citibile prin conectorul Cloudflare, deci rămân
de urmărit de proprietar după 22 septembrie (`specs/STATE.md`).

## 7. Ce NU se face și de ce

- **Nu se taie sursele „ne-românești".** Măsurat: 5,3% din articole. Nu rezolvă plafonul,
  strică acoperirea. (Proprietarul a autorizat tăierea *dacă e nevoie*; nu e.)
- **Nu se mută imaginile pe R2 sau pe un al doilea Worker.** Ambele funcționează pe Free, dar
  adaugă o suprafață de deploy și o dependență de cont pentru un artefact care oricum nu
  trebuia să existe. Dacă arta e desenabilă în pagină, găzduirea ei e o problemă inventată.
- **Nu se șterge `media/`.** Nu se mai adaugă artă nouă acolo, dar ștergerea a ~25.000 de
  fișiere într-un PR îl face nerevizuibil. Rămâne curățenie separată.
- **Nu se rescrie istoricul git** ca să scadă cele 681 MB din `media/`.
