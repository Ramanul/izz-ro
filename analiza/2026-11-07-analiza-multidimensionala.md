# IZZ.ro — analiză multidimensională

**Data analizei:** 7 noiembrie 2026 · **Commit analizat:** `b0835d1` (`main`) · **Build de referință:** randare locală din `data/articles.json`, 7 noiembrie 2026, 06:42 UTC
**Obiect:** site-ul public izz.ro ca produs (tehnic, performanță, SEO, editorial, UX, accesibilitate, securitate, legal, operațional, sustenabilitate) și pipeline-ul care îl produce.
**Livrabile:** acest raport, `analiza/masuratori.json` (cifrele brute), `analiza/masuratori.py` (script reproductibil).

---

## 0. Pe scurt

### Verdict

IZZ.ro este, la nivel de **inginerie**, cu mult peste media agregatoarelor românești: pipeline determinist cu stare în git, 3.100 de teste care trec în 62 de secunde, CSP cu hash-uri, zero legături interne moarte (0 / 18.177 în eșantionul propriu, 0 / 14.307 la `html_check`), transparență editorială scrisă și aplicată mecanic. La nivel de **produs** însă, site-ul are trei slăbiciuni care se văd exact acolo unde contează — pe prima pagină, în rezultatele Google și pe pagina de articol:

1. **Prima pagină cântărește 595 KB de HTML (108 KB gzip), din care 455 KB sunt SVG decorativ desenat în pagină** — 76% din greutate e artă generată, nu informație. Paginile de categorie sunt la fel (mediană 135 KB, `/tech/` 378 KB).
2. **82% dintre pagini de articol nu au nicio imagine**, iar textul propriu-zis ocupă 28% din pagină (mediană 4,9 KB text în 17 KB de HTML). Diferențiatorul editorial — sinteza multi-sursă — apare în doar **6,2%** din articole.
3. **Arhiva de rezervă (gh-pages) este la ~85% din plafonul de 1 GB** al GitHub Pages și crește ~19 MB/zi: în câteva zile, fallback-ul pentru permalink-urile expirate (fereastra TTL de 11 zile) nu mai poate fi publicat.

Restul problemelor sunt reale, dar secundare: titluri prea lungi pentru SERP (91% peste 60 de caractere), 654 de meta-descrieri identice, imagini neresponsive (0 `srcset`), hartă cu cereri către un terț nedivulgat în politica de confidențialitate, newsletter promis în politica de confidențialitate dar inexistent pe site, lipsa oricărei măsurători de audiență (deliberat, dar fără înlocuitor).

### Tablou de bord

| Indicator | Măsurat | Cum se citește |
|---|---:|---|
| Pagini HTML randate | **7.678** | 6.496 articole + 15 hub-uri + 316 paginare + 850 utilitare + pagina 404 |
| Greutate HTML totală | **163,8 MB** (43,0 MB gzip) | fără imagini, doar documente |
| Prima pagină | **581 KB / 108 KB gzip** | 60 carduri, 455 KB SVG inline |
| Pagină de categorie (mediană) | **135 KB / 19,7 KB gzip** | `/tech/` 378 KB |
| Pagină de articol (mediană) | **16,9 KB / 4,8 KB gzip** | text util: 4,9 KB (28%) |
| CSS blocant la prima pictare | **22,5 KB gzip / 3 cereri** | `styles.css` + `site.css` + `faza2.css` |
| JS blocant / amânat | **1,7 KB / 7,7 KB gzip** | `theme.js` sincron în `<head>` |
| Imagini pe disc | **2.369 JPG (227,8 MB) + 757 WebP (73,6 MB)** | mediană 103 KB / fișier |
| Imagini fără `srcset` | **100%** (1.642 `<img>` reale) | un singur fișier 960 px pentru orice ecran |
| Articole cu fotografie | **1.186 / 6.496 (18%)** | restul: doar text |
| `og:image` specific articolului | **1.200 / 6.496 (18,5%)** | 81,5% partajează imaginea categoriei |
| Titluri peste 60 caractere | **5.909 / 6.496 (91%)** | mediană 82 caractere |
| Fișiere în deploy | **11.090 / 17.000** (buget intern) | 485 MB |
| Teste | **3.100 trec, 4 sărite, 8 xfail, 62 s** | `ruff` curat |

### Primele zece constatări

1. Arta generativă inline este singurul cost semnificativ de performanță al site-ului: 60 de compoziții SVG pe prima pagină, cu `id="art-gold-grad"` duplicat de 10–17 ori pe pagină (HTML invalid, referințe de gradient fragile).
2. 82% dintre articole nu au imagine, iar `og:image` este aproape mereu imaginea categoriei — partajările sociale arată toate la fel.
3. Titlurile nu sunt proiectate pentru SERP: 91% depășesc 60 de caractere, 5% sunt tăiate cu „…” în `<h1>`, iar anunțurile oficiale păstrează titlul brut al documentului (mediană 103, maxim 735 de caractere).
4. Sinteza multi-sursă — promisiunea centrală a brandului — acoperă 6,2% din conținut; 93,8% sunt rezumate dintr-o singură sursă.
5. 39% din conținutul „Local” sunt anunțuri oficiale (1.306 din 3.371), publicate cu titlul instituției, fără corp, ceea ce trage în jos percepția de „ziar”.
6. Legăturile interne sunt subțiri: mediană 5 linkuri interne pe articol, „Articole conectate” doar pe 21% din pagini, 777 de pagini de subiect sunt `noindex`.
7. Politica de confidențialitate promite newsletter (Brevo) și „nicio cerere către terți”, dar formularul lipsește (`content/newsletter.html` nu există), iar harta încarcă stiluri și tile-uri de la `tiles.openfreemap.org`.
8. Stocarea crește necontrolat: `output/` 485 MB, `.git` 206 MB, `media/` 214 MB comis, gh-pages 851,5 MB din 1 GB (+19 MB/zi).
9. Accesibilitatea este solidă la contrast (minim 4,73:1), focus și mișcare redusă, dar lipsește linkul „sari la conținut”, emoji-urile intră în `<h1>`/`<h2>`, iar ecranele de 44 px sunt ocazionale.
10. Nu există nicio măsurare de audiență: o decizie corectă etic, dar care lasă produsul fără busolă — se pot lua decizii doar din intuiție și din Search Console.

### Primele cinci acțiuni (dacă se face doar atât)

| # | Acțiune | Efort | Efect măsurabil |
|---|---|---|---|
| 1 | **Plan de stocare pentru arhivă** (retenție + alertă la 90% + mutarea coperților în afara git) | M | fallback-ul nu moare; repo-ul nu mai crește cu ~20 MB/zi |
| 2 | **SVG o dată pe pagină** (`<defs>` comun / `<use>` / limită de carduri cu artă) | S | prima pagină 595 → ~150 KB; gzip 108 → ~35 KB |
| 3 | **Titlu SEPARAT de titlul afișat** (`seo_title`, buget 60 caractere) + normalizarea titlurilor oficiale | M | CTR în Google și comprehensibilitate |
| 4 | **`srcset` 240/480/960 + `og:image` per articol pentru știrile importante** | S | −50…70% bytes de imagine pe mobil; partajări distincte |
| 5 | **Context pe pagina de articol** (județ, entități, 3–5 articole conectate, „ce urmează”) | M | timp pe pagină, adâncime de crawl, 82% → sub 40% pagini „goale” |

---

## 1. Metodă și limite

**Ce am măsurat.** Am randat site-ul din starea comisă (`python -m generator.main --render-only`, 49 s, 11.090 fișiere) și am analizat cele 7.678 documente HTML produse, plus `data/articles.json` (7.528 de iteme), configurația (`generator/config.py`), șabloanele Jinja2, CSS/JS-ul static, workflow-urile și documentele de politică. Cifrele brute sunt în `analiza/masuratori.json`, reproduse cu `analiza/masuratori.py`.

**Capcană de metodă, semnalată în cod:** suita `pytest` re-randează `output/` cu un set redus de ~190 de articole (`tests/conftest.py`, fixture `output_randat`). Dacă rulezi testele înainte de măsurători, `output/build.json` arată `article_count: 189` și toate cifrele de greutate scad de ~30 de ori. Orice audit viitor ar trebui să verifice `build.json` înainte de a trage concluzii.

**Ce NU am putut măsura.**
- **Date de teren (CrUX / Search Console / Cloudflare Analytics):** nu am acces. Toate cifrele de performanță sunt statice (bytes, cereri, structură), nu LCP/INP de la cititori reali.
- **Lighthouse/axe în browser:** mediul nu are Chromium; nu am rulat un audit de accesibilitate automat pe pagini reale (verdictul de accesibilitate e din cod + măsurători de contrast + inspecție de markup).
- **Conținut articol cu articol:** am evaluat agregate și eșantioane (400 de pagini pentru linkuri, 300 pentru ID-uri duplicate, 500 pentru imagini), nu fiecare din cele 6.496 de știri.
- **Comportament live:** site-ul de producție poate diferi prin fereastra de 24 h, cache și deploy-ul curent; cifrele se referă la build-ul local din starea comisă.

---

## 2. A. Arhitectură și pipeline

### Ce funcționează

- **SSG pur, fără bază de date:** `data/articles.json` comis în repo este adevărul unic; 18.032 de linii de Python în `generator/`, cu module separate pentru fetch, stare, clustering, selecție, procesare AI, moderare, randare, hartă, index de căutare.
- **Gărzi care nu se învață singure:** `guard.autotest()` rulează 59 de cazuri la fiecare pornire și oprește publicarea dacă garda de conținut nu mai prinde atacul; `qa_check.py` blochează commitul dacă apar surse incoerente; `grounding_gate.py` blochează citatele și cifrele străine.
- **Buget de fișiere explicit:** 11.090 / 17.000 (rezervă 5.910) — conștientizarea plafonului Cloudflare Free este în cod, nu în capul cuiva.
- **Fallback în două straturi:** Workerul de 404 trimite permalink-urile expirate către oglinda gh-pages, cu listă pozitivă de căi (fără să servească prima pagină veche).
- **Reproductibilitate:** randarea durează 49 s pentru 7.678 de pagini; `--dry-run` și `--render-only` permit testarea fără rețea și fără AI.

### Ce mă doare

| Observație | Dovadă | De ce contează |
|---|---|---|
| `render.py` are 2.806 linii și ține împreună randarea, SEO, JSON-LD, harta, feed-urile, OG, sitemap-uri | `wc -l generator/render.py` | orice modificare atinge tot; testele compensă, dar viteza de schimbare scade |
| `data/articles.json` are 9,4 MB și e rescris integral la fiecare rulare orară | `du -sh data/articles.json` | churn în git; diff-uri ilizibile; fiecare rulare comite un fișier mare |
| 35 de workflow-uri, 14 cu `cron` | `.github/workflows/` | suprafață operațională mare; 4 rulări pe oră în total (build, deploy, monitor, detectie-tacere) |
| Suita de teste e „raport-only” în pipeline (`build.yml`, pasul „Suita de teste (raport-only, IZZ-0415)”) | `build.yml:92` | o regresie de template nu oprește publicarea; doar `qa_check` și `grounding_gate` opresc |
| Randarea completă rescrie 11.090 de fișiere chiar dacă 95% sunt neschimbate | `output: 11090 fisiere` | timp de build și upload; nu e critic la 49 s, dar crește cu fereastra |

### Propuneri

**A1 (P2, efort M) — Separă `render.py` pe domenii:** `render_pages.py` (articol/categorie/paginare), `render_meta.py` (JSON-LD, OG, sitemap, feed), `render_special.py` (hartă, subiecte, dosare, ghiduri). Fără schimbare de comportament; testele existente rămân plasa de siguranță.

**A2 (P2, efort S) — Cache de randare pe articol:** hash pe `(slug, model, titlu, corp, published)` → dacă nu s-a schimbat, copiază directorul existent. În practică, la o rulare orară doar 5–15% din pagini se schimbă; build-ul scade sub 20 s și upload-ul scade proporțional.

**A3 (P3, efort S) — Comprimă starea:** `data/articles.json.gz` (sau JSON Lines pe zile) reduce fișierul la ~1,5 MB și face diff-urile utile. Dacă la 12 luni ajunge la 50 MB, mutarea în D1/R2 e justificată; acum nu e.

**A4 (P3, efort M) — Consolidează workflow-urile:** țintește 12–15 workflow-uri (build+deploy, monitor, conținut, securitate). Fiecare workflow în minus este un eșec în minus la 3 dimineața.

---

## 3. B. Performanță și greutate

### Ce am măsurat (build 2026-11-07, 06:42 UTC)

| Tip pagină | n | mediană | p95 | max | mediană gzip |
|---|---:|---:|---:|---:|---:|
| Prima pagină | 1 | **580,8 KB** | — | — | **107,6 KB** |
| Categorie (pag. 1) | 15 | 135,1 KB | 370,9 KB | 377,6 KB (`/tech/`) | 19,7 KB |
| Paginare | 316 | 95,1 KB | 156,5 KB | 453,2 KB | 16,6 KB |
| Articol | 6.496 | 16,9 KB | 19,5 KB | 32,4 KB | 4,8 KB |
| Utilitar (subiect, ghid, legal…) | 850 | 11,0 KB | 19,6 KB | 173,7 KB (`/surse/`) | 3,6 KB |

**Descompunerea primei pagini:** 594.760 bytes = **454.924 bytes de SVG inline** (60 de compoziții), 1.160 bytes CSS de fonturi, 3.963 bytes JSON-LD, restul markup de carduri și navigație. Adică **76% din prima pagină este decor**.

**CSS și JS la prima pictare:**

| Resursă | Raw | Gzip | Blochează? |
|---|---:|---:|---|
| `styles.css` | 80.768 | **20.952** | da |
| `site.css` | 878 | 544 | da |
| `faza2.css` | 2.034 | 1.043 | da |
| `theme.js` (în `<head>`, fără `defer`) | 4.332 | **1.726** | **da** |
| `judet.js` + `pwa.js` + `editorial-updates.js` + `push.js` | 17.687 | 7.723 | nu (`defer`) |
| Fonturi (7 fișiere woff2) | 104 KB | — | 2 preîncărcate (Playfair 800 + JetBrains 700), 25 KB |

**Imagini:** 2.369 JPG (227,8 MB, mediană 103 KB, p95 177 KB) și 757 WebP (73,6 MB). **Niciun `<img>` nu are `srcset`** — cardurile declară `sizes="(min-width: 1000px) 360px, …"`, dar descarcă tot fișierul de 960 px. Pe un telefon de 390 px, un card de 360 px primește o imagine de 2,6× rezoluția necesară.

**Harta:** `/harta/` încarcă `harta-stiri.js` (140 KB) + `vendor/maplibre` (1,2 MB) + date 3,1 MB, cu stiluri și tile-uri de la `tiles.openfreemap.org`. E ok ca pagină secundară, dar nu are indicator de încărcare bugetat și depinde de un terț (vezi §8).

**Ce lipsește din CSS:** `content-visibility: auto` / `contain-intrinsic-size` (0 apariții). Pe o pagină cu 60 de carduri, asta este cea mai ieftină optimizare de pictare rămasă.

### Interpretare

Prima pagină are un cost de transfer pe care niciun CDN nu îl poate ascunde: 108 KB gzip **înainte** de CSS (22 KB), fonturi (25 KB preîncărcate) și imaginile cardurilor lente. Pe 3G/4G românesc, asta mută LCP-ul cu 300–700 ms față de un buget de 100 KB. Paginile de categorie au aceeași problemă, amplificată de numărul de carduri.

Arta generativă nu este însă „decor degeaba”: ea ține identitatea vizuală a site-ului și a înlocuit 2–3 fișiere per articol și un build cu Chromium. Problema nu e ideea, ci **livrarea**: aceleași `<defs>` sunt repetate de 60 de ori, iar compozițiile se repetă (`warm_geometry` 24 din 49 de scene pe prima pagină).

### Propuneri

**B1 (P0, efort S) — Un singur set de `<defs>` per pagină.** `templates/_art.html:66` definește `id="art-gold-grad"` în fiecare SVG. Consecințe: HTML invalid (ID duplicat de 10–17 ori pe pagină), iar `url(#art-gold-grad)` se rezolvă la primul nod din DOM — dacă acel nod ajunge ascuns (carduri din `<template>`, secțiunea „din județ”), gradientul dispare. Fix: un `<svg width="0" height="0"><defs>…</defs></svg>` o dată în `base.html`, iar compozițiile folosesc `fill="url(#art-gold-grad)"`. Câștig estimat: −3…5 KB per card, plus validitate.

**B2 (P0, efort M) — Plafon de artă inline pe pagină + `content-visibility`.** Păstrează SVG-ul doar pentru primele 12–16 carduri (restul: variantă CSS-only, deja existentă în `htmlart`), și adaugă:
```css
.card { content-visibility: auto; contain-intrinsic-size: 320px 420px; }
```
Estimat: prima pagină 595 → ~150 KB (−75%), gzip 108 → ~35 KB, fără pierdere vizuală în primul ecran.

**B3 (P1, efort S) — `srcset` real.** În `_card.html` și `article.html`: 240/480/960 px (WebP + JPG fallback), păstrând `sizes` deja scris. Estimat: −50…70% bytes de imagine pe mobil; pe articol, imaginea `fetchpriority="high"` devine LCP real, nu 103 KB orbește.

**B4 (P1, efort S) — Mai puține cereri blocante:** fuzionează cele trei CSS-uri într-unul (22,5 KB gzip) sau, mai bine, inline critical-CSS (~6 KB) + încarcă restul cu `media="print" onload`; mută `theme.js` inline cu hash CSP (infrastructura de hash există deja în `_headers`).

**B5 (P2, efort S) — Buget de greutate care blochează.** `tools/greutate.py` există și raportează, dar nu oprește nimic. Adaugă praguri per tip (home ≤ 200 KB, categorie ≤ 120 KB, articol ≤ 40 KB, gzip) și rulează-l în `build.yml` lângă `asset_budget.py --enforce`.

**B6 (P2, efort S) — Cache HTTP pentru HTML.** `_headers` nu setează `Cache-Control` pentru documente. Cu rebuild orar: `max-age=60, stale-while-revalidate=300` reduce revalidările și TTFB-ul perceput, fără să servească știri vechi.

---

## 4. C. SEO și vizibilitate

### Date

| Indicator | Valoare | Comentariu |
|---|---:|---|
| URL-uri în `sitemap.xml` | 6.581 | 7.678 pagini − pagini `noindex` |
| `sitemap-news.xml` | 1.000 | la plafonul Google News; conținut < 48 h |
| `sitemap-images.xml` | 1.000 | |
| `sitemap-priority.xml` | 454 | |
| Pagini `noindex` | 1.094 | 316 paginare + 778 subiecte/utilitare |
| Titluri > 60 caractere | 5.909 (91%) | mediană 82 |
| `<h1>` trunchiate cu „…” | 320 (5%) | „D I S P O Z I Ţ I A nr. 1.748…” |
| Titluri duplicate | 421 (72 grupuri) | 316 din paginare, restul anunțuri oficiale |
| Meta-descrieri duplicate | 654 (101 grupuri) | „Anunț oficial publicat de Primăria X.” |
| Meta-descrieri < 70 caractere | 649 | mai ales anunțuri fără corp |
| `og:image` la nivel de categorie | 5.296 (81,5%) | 1.200 au copertă proprie |
| Linkuri interne / articol (în `<main>`) | mediană 5 | „Articole conectate” doar pe 21% |
| Legături interne moarte | 0 / 18.177 (eșantion 400 pagini) | `html_check.py`: 0 / 14.307 pe 305 pagini |

### Ce funcționează

Sitemap-uri separate și corecte, `lastmod`, `news:publication_date`, RSS cu 50 de iteme, IndexNow cu coadă persistentă, `robots.txt` curat, JSON-LD valid pe toate paginile (0 erori de parsare), `@graph` cu `@id`-uri absolute, `NewsArticle` + `BreadcrumbList`, `max-image-preview:large`, `rel="prev"/"next"` pe paginare și `noindex,follow` pe paginarea adâncă. Canonicalul e corect peste tot (0 lipsă).

### Problemele reale

1. **Titlul nu e proiectat pentru SERP.** Google afișează ~60 de caractere / 580 px. La 82 de caractere mediană, majoritatea titlurilor sunt tăiate la cuvântul care conta. În plus, șablonul adaugă „— IZZ.ro”, consumând 9 caractere pe fiecare pagină.
2. **Anunțurile oficiale poluează indexul semantic:** titluri administrative de 100–735 de caractere, cu majuscule și litere spațiate, plus 654 de descrieri identice. Pentru un crawler, 1.306 pagini aproape identice înseamnă conținut subțire; pentru cititor, înseamnă zgomot.
3. **Churn de URL-uri:** fereastră TTL de 11 zile, ~620 de articole noi pe zi. Site-ul nu acumulează autoritate pe URL-uri stabile; singurele active evergreen sunt ghidurile, dosarele și ce rămâne pe oglindă — dar oglinda e pe alt domeniu și servită prin Worker, deci fără semnale proprii.
4. **Subiectele sunt `noindex` (777 pagini)** — exact paginile care ar putea fi hub-uri evergreen („Euronews”, „Sectorul 1”, „vortex polar”) sunt excluse din index.
5. **`og:image` uniform** — 81,5% dintre partajări arată aceeași imagine de categorie; pe Facebook/WhatsApp, știrile devin indistincte.

### Propuneri

**C1 (P0, efort M) — `seo_title` separat de titlul afișat.** Câmp nou în `process.py` (sau derivat în `render.py`): 50–60 de caractere, fără „— IZZ.ro” în `<title>` (brandul e deja în `og:site_name` și în breadcrumb), cu păstrarea titlului complet în `<h1>` și `og:title`. Metric: procentul de titluri ≤ 60 caractere (țintă 100%) și CTR în Search Console.

**C2 (P0, efort M) — Normalizarea titlurilor oficiale.** Pentru `processed_by == "official"`: scoate prefixele de tip „ANUNȚ”, „PROIECT DE HOTĂRÂRE”, „D I S P O Z I Ţ I A”, normalizează majusculele, taie la 90 de caractere la cuvânt și păstrează titlul brut într-un `<details>` cu eticheta „Titlul documentului”. Plus: adaugă localitatea în `<title>` și în meta-descriere („Anunț oficial — Primăria Tulcea, 5 nov. 2026: …”) ca să elimini duplicatele cross-localitate. Metric: 0 titluri > 90 caractere la anunțuri; 0 descrieri duplicate.

**C3 (P1, efort S) — Descrieri unice pentru anunțurile fără corp.** Astăzi 649 au sub 70 de caractere, iar 654 sunt identice. Formula propusă: `{tip document} emis de {instituție} la {dată}: {primul enunț din titlu, 90 car}`. Zero muncă editorială, diferență mare în SERP.

**C4 (P1, efort M) — `og:image` per articol pentru știrile importante.** Azi `OG_COVER_MAX_ARTICLES=1200` acoperă arbitrar 18%. Propunere: generate pentru (a) toate sintezele C, (b) toate articolele din primele 24 h, (c) top 3 pe categorie — cu text scurt (categoria + data) peste compoziția existentă. Alternativ: endpoint `/og/<slug>.png` în Workerul existent, cu cache 30 zile (cost: 1 invocare per partajare, nu per vizualizare).

**C5 (P1, efort S) — Legături conectate pe 100% din articole.** Există deja `editorial_relations` / `_editorial_relations.html` și un prag `RELATED_MIN_SHARED=2`. Scade pragul la 1 entitate pentru categoriile mici și afișează 3–5 articole; adaugă „următorul/anteriorul din categorie”. Metric: mediană linkuri interne 5 → 9; pagini fără nicio legătură internă → 0.

**C6 (P2, efort S) — Promovează 40–60 de subiecte la indexabil.** Criteriu mecanic: ≥ 8 articole sau ≥ 3 luni de acoperire sau entitate din `data/entities/`. Restul rămân `noindex`. Metric: 40–60 pagini evergreen care pot primi trafic din căutări de tip entitate.

**C7 (P3, efort S) — Igienă:** elimină `hreflang="ro"` auto-referențial (inutil fără alternativă lingvistică), păstrează `robots` pe paginare, verifică că `sitemap-priority.xml` nu dublează `sitemap.xml` fără câștig.

---

## 5. D. Editorial și conținut

### Date

| Indicator | Valoare |
|---|---:|
| Iteme în stare | 7.528 (12 zile) |
| Model B (o sursă) | 7.059 (**93,8%**) |
| Model C (sinteză multi-sursă) | 469 (**6,2%**) |
| Anunțuri oficiale (fără AI) | 1.366 (18,1%) |
| Local = anunț oficial | 1.306 / 3.371 (**39%**) |
| Surse distincte / top 10 pondere | 398 / **18,1%** |
| Surse cu un singur articol | 99 |
| Teaser B (mediană) | 28 cuvinte |
| Sinteză C (mediană) | 45 cuvinte |
| Pagini „~1 min citire” | 6.138 / 6.496 (**95%**) |
| Duplicate eliminate la dedup | 555 |
| Articole ascunse de moderare (rularea de azi) | 5 |
| Titluri duplicate în date | 67 (37 grupuri) |
| Valori murdare în `ai_cat` | `None` (1.366), `" economic"`, `"external"`, `"monden"`, `"politice"`, `"education"`, `"justitie"` |

### Ce funcționează

Diversitatea surselor este reală (top 10 = 18% din volum, 99 de surse cu un singur articol), dedup-ul editorial elimină 555 de duplicate de eveniment într-o rulare, moderarea mecanică prinde spam și markup (5 cazuri azi), iar `guard` are 59 de cazuri de autotest. Etichetarea tipului de conținut („Sinteză din N publicații / o singură origine / fapte neconfirmate reciproc”) este o idee editorială excelentă, rar întâlnită la agregatoare.

### Problemele reale

1. **Diferențiatorul e minoritar.** Brandul promite „un subiect, toate sursele”; 93,8% din conținut este un rezumat dintr-o sursă. Cu `CLUSTER_MIN_SOURCES=2` și 7.528 de iteme, doar 469 ajung sinteză — clusteringul e prea strict sau prea mult conținut vine din surse unice (primării, știri locale).
2. **Anunțurile oficiale domină „Local”** (39%), fără corp, cu titluri administrative. Cititorul care intră pe /local/ vede un buletin de instituții, nu un ziar.
3. **Volumul de text e mic:** 28 de cuvinte mediană. Este o alegere asumată („mai puțin zgomot”), dar înseamnă că pagina trebuie să ofere *context*, nu doar text — ori contextul lipsește în 82% din cazuri.
4. **Taxonomie murdară:** `ai_cat` are 20+ de valori inconsistente și 1.366 de lipsuri; întreține confuzie în rapoarte și riscă să reintre în logică.
5. **Duplicate oficiale:** același tip de document de la primării diferite produce titluri identice („Hotărâre de consiliu: aprobarea Regulamentului…” × 12).

### Propuneri

**D1 (P0, efort M) — Normalizare titluri oficiale** (vezi C2). Este cea mai mare îmbunătățire editorială cu efort mic, pentru că 1 din 5 articole este anunț oficial.

**D2 (P1, efort M) — Ridică ponderea sintezelor C la 15–20%.** Trei pârghii: (a) coboară pragul de clustering pentru categoriile cu multe surse (sport, extern, economic); (b) grupează pe `story_id` și peste 48 h (acum fereastra e scurtă); (c) acceptă sinteză C și când o singură sursă are ≥ 2 materiale pe același eveniment. Metric: % C din total, publicat în `editorial-report.json`.

**D3 (P1, efort S) — Igienă de date:** elimină `ai_cat` (nefolosit în randare) sau îl înlocuiește cu `ai_cat_norm` dintr-un enum închis; adaugă un test care respinge valori în afara enum-ului. Curăță și `prompt_version: None` la cele 1.366 de iteme oficiale.

**D4 (P2, efort S) — „Ce nu știm” pe fiecare articol.** Sinteza are deja `dialectic` cu `ASSUMED_SILENCE`; extinde eticheta la model B: „O singură sursă · fapte neconfirmate”. Deja există pe card, dar nu și în corpul paginii — o linie, multă încredere.

**D5 (P2, efort M) — Prag de calitate pe titluri la intrare:** respinge titluri > 110 caractere fără normalizare, titluri cu majuscule > 60%, titluri fără verb conjugat. `tools/title_quality_audit.py` există deja — transformă-l în poartă blocantă pentru anunțurile oficiale.

---

## 6. E. UX și produs

### Ce funcționează

- **Prima pagină spune o poveste:** „Ce s-a întâmplat azi” (briefing de 7 titluri), lead-ul cu sursele în lateral, apoi secțiuni pe categorii. Numărul zilei („1.061 articole → 975 subiecte · 173 surse · 37 județe”) este un semnal de prospețime rar.
- **Produse reale, nu pagini de umplutură:** harta știrilor (niveluri geografice, „volum” vs „pe locuitor”, confirmări încrucișate), „Ce urmează” (calendar generat din entități), ghiduri cu valori oficiale, calculator de salariu, căutare Pagefind cu diacritice opționale și filtre.
- **Personalizare locală discretă:** „Județul meu” în `localStorage`, fără cont, fără tracking.
- **PWA + Web Push** cu maximum o alertă pe zi, cu reguli mecanice anti-clickbait — o funcție greu de găsit pe piața RO și imposibil de implementat pe plan gratuit fără codul lor.

### Ce lipsește

1. **Pagina de articol e goală vizual** (82% fără imagine) și are 4,9 KB de text într-un șablon de 17 KB. Pentru cititorul care vine din Google sau dintr-un share, prima impresie este „pagină de text cu două casete de disclaimer”.
2. **Disclaimerul e repetat de trei ori** (badge + trust-label + ai-note + „Răspunde editorial”), ceea ce subminează încrederea în loc să o construiască.
3. **Newsletter promis, dar inexistent:** `content/legal/privacy.md` și `content/legal/contact.md` descriu abonarea Brevo; `generator/render.py:2018` caută `content/newsletter.html`, care nu există. Secțiunea nu se randează. Fie se livrează embed-ul, fie se scoate promisiunea.
4. **Fără „load more” / flux continuu:** prima pagină are 60 de carduri și se termină; cititorul fidel nu are unde merge decât pe categorii.
5. **Fără semnal de autoritate pe articol:** nu există „cine a verificat”, „de ce acest subiect”, „ce s-a schimbat față de versiunea anterioară” (infrastructura de corecții există, dar apare rar).

### Propuneri

**E1 (P0, efort M) — „Bandă de context” pe articol.** Sub titlu, 1 rând compact: județul (link la `/harta/<judet>/`), 2–3 entități (link la `/subiect/`), data publicării sursă, „3 articole conectate”. Nu adaugă greutate (text + 3 linkuri) și rezolvă simultan problema 82%-fără-imagine și a linkurilor interne.

**E2 (P1, efort S) — Condensează disclaimerul.** Un singur rând vizibil („Rezumat automat dintr-o sursă · citește originalul”) + link „Cum lucrăm”, cu explicația completă pe `/legal/method/`. Păstrează marcajul AI Act obligatoriu, scoate repetiția.

**E3 (P1, efort S) — Newsletter sau tăcere.** Dacă Brevo e disponibil: `content/newsletter.html` cu formular + double opt-in, secțiune pe prima pagină, confirmare în politică. Dacă nu: elimină paragrafele din `privacy.md` și `contact.md`. Incoerența actuală costă încredere exact la cititorul care caută transparență.

**E4 (P2, efort S) — Flux continuu pe prima pagină:** buton „încarcă mai multe” care cere `/local/2/` și inserează cardurile (fără JS: link normal, deja există). Crește paginile/sesiune fără să crească HTML-ul inițial.

**E5 (P2, efort M) — „Urmărește subiectul”:** buton pe pagina de articol care salvează `story_id` în `localStorage` și afișează o secțiune „subiectele tale” pe prima pagină (model identic cu „Județul meu”, deja implementat). Zero server, zero tracking, retenție reală.

**E6 (P3, efort S) — Stare de încărcare pentru hartă:** skeleton + `aria-live` (azi textul „Se încarcă datele…” e static), plus buton „încarcă harta” pentru conexiuni lente (vezi și §8, privacy).

---

## 7. F. Accesibilitate

### Ce funcționează (verificat)

- **Contrast:** toate perechile de text trec AA — calculat: `ink/paper` 16,73:1, `ink-2` 7,02:1, `ink-3` 4,73:1, `gold-strong` 4,74:1, `danger` 5,07:1, alb pe `gold-strong` 5,08:1. Comentariile din CSS documentează exact pragurile — rar.
- **Focus vizibil** (`:focus-visible`, 4 reguli), **`prefers-reduced-motion`** respectat (inclusiv `scroll-behavior: auto`), animații doar pe `transform` și doar sub `@supports`.
- **Semantică:** un singur `<h1>` pe fiecare pagină (0 excepții), `<main>`, `<nav aria-label>`, breadcrumb cu `aria-label`, `aria-current="page"`, `role="status"` pentru mesaje, imagini decorative cu `alt=""` (0 imagini fără atribut `alt`).
- **Formulare:** search cu `<label class="visually-hidden">`, filtre cu `aria-pressed`, `role="group"` + `aria-labelledby`.
- **Declarație de accesibilitate** publicată, cu referire la WCAG 2.1/2.2 AA.

### Ce lipsește (verificat)

| Problemă | Dovadă | Efect |
|---|---|---|
| **Fără link „sari la conținut”** | 0 apariții în `templates/` | utilizatorul de tastatură traversează ~20 de linkuri de navigație pe fiecare pagină, mai ales pe prima pagină cu 60 de carduri |
| **Emoji în titluri** | `📅 Ce urmează`, `🧮 Instrumente`, `📌 Ghiduri`, `📌 Pe scurt` | cititorul de ecran rostește „calendar”, „abac”, „pushpin” înaintea titlului |
| **ID duplicat** | `art-gold-grad` × 10–17 pe pagină | HTML invalid; referințe de gradient fragile |
| **Ținte de atingere** | o singură regulă `min-height: 44px` | butoanele din subsol (`Text normal`, `Text mare`, `Spațiere`, `Tipărește`) sunt mici pe mobil |
| **`autofocus` pe căutare** | `templates/search.html` | pe iOS deschide tastatura și sare peste context; cititorii de ecran pierd începutul paginii |
| **Fără audit automat în CI** | nu există `axe`/`pa11y` în workflow-uri | regresiile de accesibilitate se descoperă manual |

### Propuneri

**F1 (P1, efort S) — Link „Sari la conținut”** ca prim element din `<body>`, vizibil la focus, țintă `#main`. O linie de HTML + 6 de CSS.

**F2 (P1, efort S) — Emoji mutat în decor:** `<span aria-hidden="true">📅</span> Ce urmează` sau `::before` cu `aria-hidden` implicit. Nu schimbă designul.

**F3 (P1, efort S) — ID-uri unice** (vezi B1) și verificare în `html_check.py`: adaugă testul „0 ID-uri duplicate pe pagină” — azi ar prinde cele 7/300 pagini din eșantion.

**F4 (P2, efort S) — Ținte de 44 px** pe toate butoanele din subsol, tema și acțiunile cardului; `autofocus` scos de pe căutare (păstrat doar la click pe iconița de căutare).

**F5 (P2, efort M) — `pa11y`/`axe` în CI** pe 20 de pagini reprezentative (home, articol cu foto, articol oficial, categorie, hartă, căutare, ghid, dosar), raport-only la început, blocant după stabilizare. Lor le place istoric `pa11y` (comentariul din CSS arată 305 erori corectate).

---

## 8. G. Securitate și confidențialitate

### Ce funcționează (peste medie)

- **CSP strict** cu 4 hash-uri pentru scripturile inline, `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'none'`, `upgrade-insecure-requests`; HSTS cu `includeSubDomains`; `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` (inclusiv `interest-cohort=()`).
- **Zero JS de la terți în paginile normale**, fonturi auto-găzduite, fără cookie-uri de urmărire, fără bară de consimțământ (corect, pentru că nu e nevoie).
- **Secretele nu sunt în repo**: cheile VAPID și `PUSH_ADMIN_TOKEN` stau în Cloudflare (`infra/PUSH-SETUP.md`), confirmat prin scanare (singurele potriviri sunt fixture-uri de test pentru redactare).
- **Criptografie testată:** `tests/test_push_criptare.py` rulează criptarea RFC 8291 în Node și o decriptează cu cheia clientului; `push.js` validează endpoint-urile cunoscute și impune o alertă/zi.
- **Ingestie defensivă:** `defusedxml`, allowlist de surse, gardă de conținut cu autotest, `grounding_gate` pentru citate/cifre, CodeQL + Semgrep săptămânal.

### Ce lipsește

| Problemă | Detaliu | Risc |
|---|---|---|
| **Terți nedivulgați** | harta cere `https://tiles.openfreemap.org/styles/*`, tile-uri și glife | politica de confidențialitate spune că cererile ajung doar la Cloudflare; IP-ul cititorului ajunge la un al treilea — neconformitate GDPR (informare) și contradicție cu textul public |
| **`style-src 'unsafe-inline'`** | necesar pentru `fonts_css` inline și atribute `style` (portrete, `--pw/--px`) | suprafață de atac XSS mai mare; se poate închide prin hash pentru blocul de fonturi |
| **CSP fără raportare** | nu există `report-uri`/`report-to` | nu afli niciodată când o regulă CSP blochează ceva legitim |
| **Fără COOP/CORP** | lipsesc `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy` | izolare de proces mai slabă (risc mic la un site static, dar ieftin de adăugat) |
| **Politica de confidențialitate nu menționează serviciul de push** | notificările trec prin serviciul browserului (Google/Mozilla/Apple) | textul spune „date tehnice păstrate de noi”, nu și cine le transportă |

### Propuneri

**G1 (P0, efort S) — Divulgă harta sau o intermediază.** Varianta minimă: un paragraf în `privacy.md` („harta încarcă tile-uri de la OpenFreeMap; cererea conține IP-ul tău, ca orice cerere web”). Varianta bună: rută `/harta/tiles/*` în Workerul existent, cu cache 7 zile — elimină terțul, rezolvă privacy și reduce latența pentru cititorii români.

**G2 (P1, efort S) — Închide `style-src`:** mută `fonts_css` într-un fișier static versionat (deja există `static/fonts.css`), păstrează doar atributele `style` (permise de `style-src-attr 'unsafe-inline'`) — sau hash-uiește blocul inline existent, ca la scripturi.

**G3 (P2, efort S) — `report-to` către o rută `/csp-report`** în Worker, cu numărare agregată; 30 de linii, vizibilitate completă asupra încălcărilor.

**G4 (P2, efort S) — Antete suplimentare:** `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Resource-Policy: same-origin` (cu excepția „/static/*” dacă e nevoie), `X-Permitted-Cross-Domain-Policies: none`.

---

## 9. H. Legal, etică, AI Act

### Ce funcționează (foarte bine)

- **Divulgarea AI este completă și mecanică:** `meta name="digitalSourceType" content="trainedAlgorithmicMedia"`, badge „Titlu sintetizat automat”, `ai-note` în corp, `trust-label` pe card, pagina `/legal/method/` care explică metodologia. Maparea pe AI Act art. 50(2)/(4) este explicită în `REGULI-SINTEZA.md`.
- **Politica imaginilor** este cea mai riguroasă parte a site-ului: allowlist pozitiv de licențe pentru `og:image` (doar CC0/PD), credit complet obligatoriu pe pagina de articol, interdicție de preluare din presă, criterii pentru persoane vulnerabile.
- **Corecții și takedown** cu flux public, `content/editorial/corrections.json`, feed separat de corecții.
- **Fără reclame, fără profilare, fără cookie-uri** — o poziție etică asumată, nu un accident.

### Ce lipsește

1. **Identificarea operatorului doar prin inițiale** (`S.A.N.`) în politica de confidențialitate. Pentru un serviciu de presă, opacitatea numelui slăbește încrederea și complică exercitarea drepturilor; GDPR cere identitatea operatorului, nu neapărat publicarea numelui complet pe site — dar un „Despre” cu nume și adresă de contact reală este standardul de facto.
2. **Politica de confidențialitate e în urmă cu realitatea** la trei puncte: newsletter (nu există), harta (terț), push (transport prin serviciul browserului).
3. **Accesibilitatea:** declarația invocă „spiritul EAA” — onest, dar ar trebui să spună și ce nivel de conformare e verificat și cu ce (WCAG 2.2 AA, audit extern la data X). Azi nu există un audit extern citat.
4. **Lipsă politică pentru crawlerii AI** (`GPTBot`, `CCBot`, `Google-Extended`): `robots.txt` permite tot. Este o decizie de business (vizibilitate în răspunsuri AI vs protecția muncii editoriale) care trebuie luată explicit, nu implicit.
5. **Drepturile editorilor de presă (art. 15 DSM / Legea 8/1996):** rezumatele sunt originale și scurte, cu link — poziție defensabilă; totuși, un paragraf în „Termeni” despre neutilizarea extraselor protejate ar întări poziția.

### Propuneri

**H1 (P1, efort S) — Actualizează `privacy.md`:** newsletter (doar dacă se lansează), tile-uri hartă, serviciu de push al browserului, durata de păstrare pentru log-uri Cloudflare. Un text de 10 rânduri care aliniază politica la realitate.

**H2 (P1, efort S) — „Cine răspunde”:** pagină `/despre/redactie/` cu operator, date de contact, procedura de corectare, timp de răspuns. Nu cere date personale suplimentare; cere doar consistență cu rolul editorial asumat.

**H3 (P2, efort S) — Politică explicită pentru crawleri AI** în `robots.txt` + un paragraf în „Termeni” (de exemplu: allow pentru indexare, disallow pentru antrenare, sau invers — decizie a proprietarului).

**H4 (P3, efort M) — Audit extern de accesibilitate** o dată pe an și citarea lui în declarație (cine, când, ce nivel, ce a rămas deschis).

---

## 10. I. Operațional, CI/CD și stocare

### Date

| Indicator | Valoare |
|---|---:|
| Workflow-uri | 35 (14 cu `cron`) |
| Rulări programate | build orar, deploy orar, monitor la 10 min, restul zilnic/săptămânal |
| Durată randare | 49 s (7.678 pagini) |
| Teste | 3.100 trec / 62 s; 4 sărite, 8 xfail |
| Lint | `ruff` curat |
| Deploy | 11.090 fișiere, 485 MB |
| `.git` | 206 MB (clonă shallow) |
| `media/` comis | 214 MB (3.374 fișiere) |
| gh-pages (oglindă) | **851,5 MB / 1 GB** (doc intern, 3 nov.) |
| Creștere oglindă | **~19 MB/zi** |
| Timp până la plafon (est.) | **~8 zile** |

### Analiză

Pipeline-ul este matur: gardă anti-cadere AI cu exit code, dispatch imediat după commit (pentru că GitHub livrează `schedule` cu întârziere de ore), probă de release cu timeout de 65 min, IndexNow cu coadă persistentă și redeschidere la eșec, mirror cu `keep_files` ca arhivă. Astea sunt lucruri pe care majoritatea proiectelor nu le au.

Problema nu e fiabilitatea, ci **creșterea de stocare**, care e singura resursă cu plafon dur în arhitectura actuală:

- **Oglinda gh-pages** păstrează toate paginile pensionate (`keep_files: true`), plus tot ce nu încape pe Worker. La 851,5 MB din 1 GB și +19 MB/zi, în câteva zile publicarea pe oglindă începe să eșueze — iar atunci permalink-urile expirate întorc 404, exact scenariul pe care Workerul de fallback a fost construit să-l evite.
- **`media/` în git** (214 MB, 3.374 fișiere) crește cu fiecare build; ștergerea fișierelor nu șterge istoricul.
- **`output/` 485 MB** e reconstruit integral la fiecare rulare; upload-ul diferențial ajută, dar manifestul de assets e mare.
- **Suita de teste rescrie `output/`** — intenționat și documentat, dar înseamnă că orice măsurătoare făcută după `pytest` descrie fixture-ul (vezi §1).

### Propuneri

**I1 (P0, efort M) — Plan de stocare, cu alertă la 90%:**
1. Job săptămânal care raportează dimensiunea arborelui gh-pages și a `.git` (există deja o măsurătoare manuală în doc).
2. Retenție pe oglindă: păstrează 12 luni de pagini; peste asta, o pagină „știrea a expirat” cu titlul, sursa și linkul către arhivă — nu un 404.
3. Coperțile: mută-le din git în R2 (10 GB gratuit) sau regenerează-le determinist la nevoie; `media/` comis nu mai e sustenabil la 20 MB/zi.
4. Blochează deploy-ul la >95% din plafon, ca la bugetul de fișiere.

**I2 (P1, efort S) — Dashboard de capacitate:** un fișier `output/capacity.json` (fișiere, bytes, media, oglindă) publicat la fiecare build, plus istoric în `data/`. Cifrele există deja în loguri; lipsesc agregarea și trendul.

**I3 (P1, efort M) — Testele să blocheze măcar partea de randare.** Azi `build.yml` rulează `pytest` raport-only (IZZ-0415). Propunere: `pytest -m "render or template"` blocant (probabil 400–600 de teste, sub 20 s), restul rămâne raport-only. Regresiile de șablon sunt cele care ajung pe site nevăzute.

**I4 (P2, efort S) — Recomandă `--enforce` pe `asset_budget.py` în jobul de deploy** (nu doar raport), ca plafonul de 17.000 să nu fie depășit accidental de o categorie care explodează.

**I5 (P3, efort M) — Observabilitate:** un fișier `status.json` public (ultimul build, articole, surse moarte, durata, erori de fetch) generat de pipeline. Site-ul are deja cultura transparenței; un status public e consecința firească și ajută și debugging-ul.

---

## 11. J. Model de business și sustenabilitate

**Situația actuală:** cost marginal ~0 (Cloudflare Free + GitHub Actions public), fără reclame, fără conturi, fără newsletter, fără API, fără donații. Finanțarea este, practic, timpul proprietarului.

**Riscul:** un produs excelent din punct de vedere etic, cu zero mecanisme de supraviețuire. Când timpul proprietarului scade, scade tot.

**Propuneri (în ordinea raportului cost/valoare):**

| # | Idee | De ce se potrivește | Efort |
|---|---|---|---|
| J1 | **Newsletter zilnic** (Brevo, deja contractat) cu briefingul de 7 titluri din `/azi/` | infrastructura există, politica o promite deja; canal propriu, independent de algoritmi | S |
| J2 | **„Susține IZZ”** — un singur buton, Stripe/LemonSqueezy, fără paywall | audiența care apreciază „zero reclame” e exact cea care plătește | S |
| J3 | **Membru** (3–5 €/lună): fără reclame (deja nu sunt), dar cu `dosare` complete, export, alertă pe subiect | monetizează diferențiatorul (context, nu volum) | M |
| J4 | **API/feed B2B** pentru redacții mici, primării, ONG-uri: „ce s-a întâmplat în județul X azi” | datele și pipeline-ul sunt deja acolo; piață mică, dar plătitoare | M |
| J5 | **Sponsorizare etichetată** în `/discounturi/` (rubrică existentă) | singura secțiune comercială compatibilă cu poziția editorială, dacă e marcată clar | S |
| J6 | **Granturi / fonduri pentru presă independentă** (UE, fondații) cu pagina de metodologie ca dosar | documentația și transparența sunt deja la nivel de dosar de finanțare | M |

**Condiție prealabilă pentru toate:** o măsurătoare de audiență agregată. Fără ea, nu poți demonstra nimic unui sponsor sau unui finanțator. Varianta compatibilă cu politica actuală: **Cloudflare Web Analytics** (fără cookie-uri, agregat) sau un contor propriu în Worker (numără pagini servite, fără IP stocat) — cu o linie adăugată în `privacy.md`. Alternativa zero este să rămână totul pe intuiție, ceea ce e o decizie, nu o strategie.

---

## 12. Matrice de priorități

Impact: 1 (mic) – 5 (decisiv). Efort: S (< 1 zi), M (1–5 zile), L (> 1 săptămână).

| ID | Propunere | Dimensiune | Impact | Efort | Metric de succes |
|---|---|---|---:|---|---|
| **I1** | Plan de stocare: retenție oglindă, coperți în afara git, alertă 90% | Operațional | 5 | M | gh-pages < 800 MB stabil; 0 eșecuri de publicare |
| **B1** | `<defs>` SVG o singură dată pe pagină | Performanță/A11y | 4 | S | 0 ID-uri duplicate; −4 KB/card |
| **B2** | Plafon artă inline + `content-visibility` | Performanță | 5 | M | home ≤ 200 KB; gzip ≤ 45 KB |
| **C1** | `seo_title` ≤ 60 caractere | SEO | 4 | M | 100% titluri ≤ 60; CTR ↑ |
| **C2** | Normalizare titluri oficiale | Editorial/SEO | 5 | M | 0 titluri > 90 la anunțuri; 0 duplicate |
| **E1** | Bandă de context pe articol (județ, entități, 3–5 conectate) | UX/SEO | 5 | M | pagini fără link intern → 0; timp/pagină ↑ |
| **B3** | `srcset` 240/480/960 | Performanță | 4 | S | −50% bytes imagine mobil |
| **C4** | `og:image` per articol pentru știrile importante | SEO/Social | 3 | M | ≥ 60% partajări cu imagine proprie |
| **G1** | Divulgare/proxy tile-uri hartă | Legal | 4 | S/M | privacy acoperă toți terții |
| **E3** | Newsletter livrat sau promisiune retrasă | Produs/Legal | 3 | S | 0 contradicții politică–site |
| **D2** | Sinteze C la 15–20% | Editorial | 4 | M | % C raportat lunar |
| **F1** | Link „Sari la conținut” | A11y | 3 | S | prezent pe toate paginile |
| **F2** | Emoji în decor (`aria-hidden`) | A11y | 2 | S | 0 emoji în titluri anunțate |
| **F4** | Ținte 44 px + fără `autofocus` | A11y | 3 | S | toate butoanele ≥ 44 px |
| **B4** | Un CSS + critical inline + `theme.js` inline cu hash | Performanță | 3 | S | 1 cerere blocantă în loc de 4 |
| **B5** | Buget de greutate blocant în CI | Operațional | 3 | S | build roșu la depășire |
| **C3** | Descrieri unice pentru anunțuri | SEO | 3 | S | 0 descrieri duplicate |
| **C5** | Legături conectate pe 100% | SEO/UX | 3 | S | median 9 linkuri interne |
| **E2** | Disclaimer condensat | UX | 3 | S | 1 rând vizibil + link |
| **D3** | Curățenie `ai_cat` / `prompt_version` | Date | 2 | S | enum închis, test de validare |
| **I3** | Teste de randare blocante | Operațional | 3 | S | pipeline roșu la regresie de șablon |
| **E5** | „Urmărește subiectul” (localStorage) | Produs | 3 | M | reveniri/sesiune ↑ |
| **C6** | 40–60 subiecte indexabile | SEO | 3 | S | trafic din căutări de entitate |
| **G2/G3** | CSP: fără `unsafe-inline` pe stiluri + raportare | Securitate | 2 | S | 0 încălcări neraportate |
| **J1–J3** | Newsletter + „Susține” + membru | Business | 4 | S/M | primul leu recurent |
| **H1/H2** | Privacy actualizat + „Cine răspunde” | Legal | 3 | S | 0 contradicții |
| **I2/I5** | `capacity.json` + `status.json` public | Operațional | 2 | S | trend vizibil zilnic |

---

## 13. Plan 30 / 90 / 365

**Primele 30 de zile — oprește sângerarea și taie greutatea**
1. I1 (storage): măsurare, alertă, retenție, coperți în afara git.
2. B1 + B2 (SVG): o singură dată pe pagină, plafon de carduri, `content-visibility`.
3. B3 (`srcset`) + B4 (CSS/JS blocant).
4. C2 + C3 (titluri și descrieri oficiale).
5. F1 + F2 + F3 (skip link, emoji, ID-uri unice).
6. E3 (newsletter: livrat sau promisiune retrasă), G1 (privacy hartă).

**Zilele 31–90 — produsul și indexul**
1. C1 (`seo_title`) + C4 (`og:image`), C5 (legături conectate 100%).
2. E1 (bandă de context), E2 (disclaimer), E4 (flux continuu).
3. D2 (sinteze C la 15%), D3 (taxonomie), D5 (poartă pe titluri).
4. I3 (teste blocante), B5 (buget de greutate), F5 (pa11y în CI).
5. C6 (subiecte indexabile), H1/H2 (privacy + redacție), I2 (`capacity.json`).

**Zilele 91–365 — sustenabilitate și relevanță**
1. J1–J3 (newsletter, susținere, membru) + măsurare agregată.
2. E5 (urmărire subiect), hartă cu proxy propriu (G1 varianta bună), PWA rafinat.
3. C7 + H3 + H4 (igienă, crawleri AI, audit extern de accesibilitate).
4. A1/A2 (despărțirea `render.py`, cache de randare), I4/I5.
5. Decizie strategică pe arhivă: oglindă separată sau arhivă pe R2 cu pagini de expirare editoriale.

---

## 14. Indicatori de urmărit (dashboard minimal)

| Indicator | Sursă | Țintă 90 zile |
|---|---|---|
| Greutate home / categorie / articol (gzip) | `analiza/masuratori.py`, `tools/greutate.py` | 45 / 60 / 30 KB |
| Cereri blocante la prima pictare | build | ≤ 2 |
| Titluri ≤ 60 caractere | `masuratori.py` | 100% |
| Descrieri duplicate | `masuratori.py` | 0 |
| Pagini cu fotografie | `masuratori.py` | ≥ 40% |
| Legături interne mediane / articol | `masuratori.py` | ≥ 9 |
| % sinteze C | `editorial-report.json` | ≥ 15% |
| Titluri oficiale > 90 caractere | `title_quality_audit.py` | 0 |
| ID-uri duplicate / pagină | `html_check.py` | 0 |
| Fișiere deploy | `asset_budget.json` | ≤ 15.000 |
| gh-pages | job săptămânal | ≤ 800 MB, stabil |
| Eșecuri de publicare / săptămână | Actions | 0 |

---

## 15. Ce NU recomand

- **Reclame programatice.** Ar demola singurul argument de diferențiere („zero zgomot”) pentru un venit mic.
- **Indexarea tuturor paginilor de subiect.** 777 de pagini de 3 articole ar dilua calitatea domeniului; 40–60 de hub-uri lucrate sunt mai valoroase.
- **Eliminarea artei generative.** Este identitatea vizuală și a înlocuit un build cu Chromium; problema e livrarea, nu ideea.
- **Scoaterea disclamerelor AI.** Sunt obligații (AI Act art. 50) și, bine formulate, sunt un avantaj de încredere. Trebuie condensate, nu eliminate.
- **Goana după scorul Lighthouse.** Scorul nu vede 455 KB de SVG; bugetul de bytes per tip de pagină vede.

---

## Anexă A — Cum se reproduc cifrele

```bash
# 1. Randare reala din starea comisa (49 s)
python -m generator.main --render-only

# 2. Verifica ce s-a randat: article_count trebuie sa fie ~6500, nu ~190
cat output/build.json

# 3. Masuratori
python analiza/masuratori.py        # scrie analiza/masuratori.json

# 4. Uneltele proiectului (comparatie)
python tools/html_check.py --raport
python tools/greutate.py
python tools/asset_budget.py
python tools/title_quality_audit.py
```

**Atenție:** `pytest` re-randează `output/` cu fixture-ul de ~190 de articole. Nu rula teste între randare și măsurători.

## Anexă B — Fișiere atinse de propuneri

| Propunere | Fișiere |
|---|---|
| B1, B2, B3 | `templates/_art.html`, `templates/_card.html`, `templates/article.html`, `static/styles.css`, `generator/htmlart.py` |
| C1, C2, C3 | `generator/process.py`, `generator/render.py`, `templates/article.html`, `templates/_card.html` |
| C4 | `generator/covers.py`, `generator/render.py`, `infra/worker.js` (dacă se face endpoint) |
| C5, E1 | `generator/render.py`, `templates/_editorial_relations.html`, `templates/article.html` |
| E3 | `content/newsletter.html` (nou), `templates/index.html`, `content/legal/privacy.md` |
| F1, F2, F4 | `templates/base.html`, `templates/calendar.html`, `templates/ghiduri.html`, `templates/instrumente.html`, `static/styles.css` |
| G1 | `content/legal/privacy.md`, `infra/worker.js`, `wrangler.jsonc`, `output/_headers` |
| G2, G3, G4 | `generator/render.py` (`_write_headers`), `infra/worker.js` |
| I1, I2 | `.github/workflows/build.yml`, `.github/workflows/deploy-worker.yml`, `tools/asset_budget.py` |
| I3, B5 | `.github/workflows/build.yml`, `tools/greutate.py` |

## Anexă C — Ce rămâne de verificat manual

1. **Search Console:** CTR pe titluri, acoperire, pagini excluse, „Descoperire” din Google News.
2. **Cloudflare Analytics:** trafic, cache hit ratio, TTFB pe regiuni.
3. **Lighthouse/WebPageTest** pe home, articol și `/local/` (mobil, 4G) — cifrele reale de LCP/CLS/INP.
4. **Audit de accesibilitate cu axe/pa11y** pe 20 de pagini (vezi F5).
5. **Verificare live a antetelor** (CSP, HSTS, cache) — nu pot fi confirmate din repo, doar din răspunsuri.
