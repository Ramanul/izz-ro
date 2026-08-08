# Atribuirea știrilor — dosar de cercetare + plan de remediere

> Scris 2026-08-08, cont A, la cererea proprietarului („recercetează toată partea de atribuire pe
> toate fațetele, prezintă concluzii și plan exhaustiv; nu mai vreau să avem aceste probleme").
> Dosarul e sursa de adevăr pentru CE AM AFLAT. Deciziile intră în `registru.tsv`, starea în `STATE.md`.
> **Nu re-cerceta ce e aici fără o descoperire nouă** — costă și s-a plătit o dată.

## 0. De ce a existat problema — cele opt cauze, nu una

Nu e un bug, sunt opt defecte independente care se compun. Enumerate ca să nu se mai repare unul
și să se creadă că s-a rezolvat tot.

| # | Cauza | Simptomul vizibil | Stare |
|---|---|---|---|
| C1 | `geo.clasifica()` întoarce NIVELUL și aruncă NUMELE locului, deși `_potriviri` îl are | eticheta se recalculează din titlu → ratează în 55% din `local` | deschis |
| C2 | Nivelul = `max()` peste toate potrivirile | o singură mențiune de sat face articolul „local" | deschis |
| C3 | „Despre" vs „menționat" tratat cu două trepte euristice (`_locul_e_subiectul`) | 10% eroare pe titluri, 53% când locul e doar în corp | parțial |
| C4 | O singură celulă `category` ține ȘI tema ȘI locul | „o axă, o casă" → un articol economic din Cluj trebuie să aleagă | deschis |
| C5 | Categoria e în permalink (`/local/<slug>/`) | orice corecție de atribuire mută URL-ul → 404; de asta nu se fac migrări retroactive | deschis |
| C6 | Eticheta e ARSĂ în JPEG, `art_id` = SHA1(URL) fără etichetă | badge-ul contrazice categoria de sub card; 2962/2962 coperți învechite | deschis |
| C7 | Două mecanisme cu reguli opuse scriau `category` | 663/1247 articole pe rubrică greșită | **reparat #165** |
| C8 | Nicio măsurare continuă a corectitudinii atribuirii | nimeni nu știa că 663 erau greșite | gold set de 40 există (`64999bf0`), nelegat de o poartă |

## 1. Cum fac alții — șapte sisteme, ce e de furat din fiecare

### 1.1 NLGF (WebSci '26, cod MIT: `github.com/wm-newslab/NLGF`)
Cel mai apropiat de problema noastră. **Două ieșiri separate**, nu una: nivelul de geo-focus
(local / state / national / international / **none**) și locurile de focus.
- fiecare toponim primește un **nivel inițial raportat la locația publicației**: „stat = statul
  publicației → nivel state; alt stat → national; județ în statul publicației → local";
- nivelul final NU e maximul, ci XGBoost peste **15 trăsături**: nume în titlu per nivel,
  distribuția nivelurilor inițiale, **poziția** (primele cinci toponime), **diversitatea**
  (câte locuri distincte);
- locul: `focus_score = frecv_titlu + frecv_articol + frecv_lead + frecv_GPE`, prag α = 0.25.

F1: local **0.87** · state 0.88 · national 0.86 · international 0.94 · none 0.89 · macro 0.89.
Baseline pe frecvență (Cliff-Clavin): macro 0.62, iar pe local doar **0.49**.
Eșecul pe care îl numesc explicit: local/state/national se confundă între ele fiindcă „știrile
naționale adoptă adesea o încadrare localizată ca să pară relevante".

### 1.2 CLIFF-CLAVIN (Media Cloud, producție, open source)
Formularea cea mai clară a distincției: **„despre ce e articolul, nu ce menționează"**. Sortează
locurile după frecvență **separat pe fiecare nivel** (țară / stat / oraș), nu un clasament
amestecat. 95% corect la nivel de țară. Demonimele („chinez" → China) sunt configurabile
(`replaceAllDemonyms`).
**Limită de cercetare:** euristicile exacte NU sunt documentate public — PDF-ul MIT dă 405,
academia.edu 403, README-ul e doar despre API. Cine vrea detaliul trebuie să citească codul Java.

### 1.3 NewsCatcher Local News API — checklistul practic, ordonat după precizie
1. `dedicated_source` — sursa acoperă un singur loc (precizie maximă, merge și fără mențiune în text)
2. `local_section` — secțiunea geografică din URL
3. `regional_source` — contextul regional al sursei dezambiguizează omonimele
4. `standard_format` — „Oraș, Județ"
5. `proximity_mention` — localitate și județ în 15 cuvinte
6. `ai_extracted` — LLM, ultimul strat, pentru referințe indirecte

Recomandarea lor: pornește cu 1-2 (precizie), adaugi 4-5 pentru acoperire, 6 la final.
**Noi avem 1 și parțial 3.** Măsurat la noi: 2 nu se aplică (vezi §3).

### 1.4 EMM / JRC (Comisia Europeană, ~20.000 articole/zi, multilingv)
Validează arhitectura noastră: gazetteer + euristici independente de limbă. Dificultatea centrală
pe care o numesc e exact ce păzesc `_AMBIGUE` / `_COMPUSE_NEGEO`: **loc vs persoană** și alegerea
între omografe. Aici nu suntem în urmă.

### 1.5 GDELT — contra-model
10M de locuri, 65 de limbi, geocodează **fiecare** mențiune la centroid, fără noțiune de focus.
Bun pentru hărți. Dacă am copia GDELT, am înrăutăți exact problema noastră.

### 1.6 Mordecai3 (Halterman, open source Python)
NER → candidați din Geonames → **model neural de ranking** → geocodare de eveniment. Partea
interesantă: separă „unde s-a întâmplat evenimentul" de „ce locuri sunt menționate" folosind un
**model de question-answering** peste text. Adică pune întrebarea „unde s-a întâmplat?", nu numără
aparițiile.

### 1.7 iMatrics / ConceptCore (NTB, Livingdocs — producție nordică)
Lecția e operațională, nu algoritmică: **nimeni nu rulează auto-tagging nesupravegheat.** Produsul
include Concept Management, Concept Suggestions inbox și Tag Quality Assurance. Echivalentul
nostru ar fi `moderation.yaml`, azi nefolosit pentru atribuire.

### 1.8 Ce fac SITE-urile de știri (verificat direct, nu presupus)
- **Digi24** `/regional`: URL-uri `/regional/digi24-iasi/<slug>` — **secțiuni per redacție locală**,
  zero clasificare din text.
- **Patch** (1.200+ orașe SUA): ediție per oraș, editorii atribuie.
- **Google News**: secțiunile sunt definite de publisher; Google „categorizează" pe deasupra.

**Concluzie:** publisherii nu au problema noastră — o rezolvă structural (birou în Iași → secțiunea
Iași). Problema e a **agregatorului**. De asta codul deschis vine din cercetare și agregatoare, nu
de la ziare.

## 2. Standardele — și de ce contrazic regula „o axă, o casă"

**IPTC NewsCodes** ține vocabulare **separate** pentru tipuri diferite de concept: Media Topic
(subiect), Genre (natura jurnalistică), World Region (geografie). Formularea din ghid: acestea
„operate as independent metadata layers rather than integrated concepts". Un item poartă simultan
subiect ȘI loc — nu alege între ele.

**schema.org** are trei proprietăți distincte pe care noi le-am colapsat într-una:
- `contentLocation` — locul DESPRE care e conținutul
- `locationCreated` — unde a fost scris
- `dateline` — textul afișat („FOCȘANI —")

**Convenția AP:** știrile locale **omit** dateline-ul; el există pentru articolele venite din altă
parte decât redacția. Inversul intuiției.

**Media Topics** are 17 categorii de nivel înalt care seamănă izbitor cu rubricile noastre:
Politics, Economy/Business/Finance, Health, Education, Crime/Law/Justice, Disaster/Accident,
Environment, Science/Technology, Sport, Arts/Culture/Media, Labour, Religion, Weather,
Lifestyle/Leisure, Conflict/War/Peace, Human Interest, Society.

**Clasificator public gata făcut:** `classla/multilingual-IPTC-news-topic-classifier` (MIT,
XLM-RoBERTa). Macro-F1 0.746; filtrat la încredere ≥0.90 urcă la 0.80.
⚠️ **Antrenat pe 21.000 de texte în 4 limbi — croată, slovenă, catalană, greacă. Româna NU e
printre ele.** Fiind multilingv ar putea transfera, dar asta e ipoteză, nu fapt. De testat pe 50
de articole ale noastre înainte de orice decizie. Încredere 5/10.

## 3. Măsurători pe corpusul nostru (2026-08-08)

**Numele de UAT găsite, `local` (513) / `zonal` (517), snapshot 2938 articole:**

| unde se caută | local: 0 nume | 1 | 2+ | zonal: 0 nume | 1 | 2+ |
|---|---|---|---|---|---|---|
| doar titlu (ce citea eticheta) | 55% | 41% | 4% | 28% | 65% | 7% |
| titlu+teaser (ce citește `clasifica`) | 28% | 53% | 19% | 9% | 66% | 24% |

Mutarea sursei etichetei de pe titlu pe textul deja scanat scade „nu știu locul" de la 55%→28%
(local) și 28%→9% (zonal), **fără interogări noi și fără AI**. Prețul: nume concurente cresc la
19-24%, unde e nevoie de scorul de focus.
*Limita măsurătorii:* scanerul folosește `_potriviri`, care acoperă doar indexul de UAT-uri, NU
ramura de sate — deci cifra e subestimare.

**Coperți învechite (măsurat 2026-08-08 18:5x):** din 2962 articole, **2808** au coperta generată
înainte de #164 și **154** între #164 și #165. **Zero** generate după #165. 1319 sunt pe axa
geografică. Cauza: `htmlart.art_id()` = SHA1(URL), fără etichetă; `render.py:543` refolosește
`media/<aid>.c.jpg` dacă există; `tools/gen_images.py:83` sare peste imaginile existente fără
`FORCE_REGEN=1`.

**Ipoteză picată → `IZZ-0157 masurat-fals`:** semnalul `local_section` (locul în path-ul URL-ului).
70/2938 articole (2,4%); unde județul apare în URL coincide cu `judet_sursa` **36/36** — zero
informație nouă. Cauza: 1155/2938 de URL-uri au un singur segment (`domeniu/slug`), iar sursele cu
secțiune geografică (tion, bihon) își declară deja județul în `config.SOURCES`.

## 4. Două lucruri care schimbă ce se poate face

**4a. Categoria în permalink e un defect cunoscut în industrie.** Recomandarea SEO standard e
`/<slug>/` fără categorie, **exact fiindcă structura se rupe la recategorizare**. La noi asta a
produs `/local/` 404 vs `/zonal/` 200 pe același slug, și e motivul pentru care corecțiile se
livrează fără migrare retroactivă. **Atâta timp cât categoria e în URL, datele greșite nu se pot
repara — doar expiră.**

**4b. Scorul de încredere raportat de un LLM nu e o poartă.** Cercetare 2026: modelele raportează
încredere medie 74-97% când riscul real e 3-80%; Expected Calibration Error între 0.05 și 0.61.
Deci „lasă modelul să spună cât e de sigur și taie sub 0.8" **nu** e o soluție. Ce funcționează:
praguri calibrate pe un gold set propriu + coadă de revizuire prioritizată.

## 5. Plan exhaustiv de remediere — șase etape, în ordinea asta

Ordinea nu e negociabilă: E0 și E1 deblochează tot restul. A repara calitatea atribuirii înainte
de ele înseamnă îmbunătățiri pe care nimeni nu le vede și date care nu se pot corecta.

### E0 — Coperta să nu mai mintă  ·  *deblochează vizibilitatea oricărei alte reparații*
- `htmlart.art_id()` include un hash scurt al textului vizibil (etichetă + subtitlu), nu doar URL-ul.
  O schimbare de etichetă produce nume nou de fișier → regenerare automată; imaginea veche e
  curățată de mecanismul `wanted` care există deja în `gen_images.py`.
- Regenerare pe loturi a celor 2962 (`FORCE_REGEN=1`, `MAX_IMAGES_PER_RUN`).
- Fișiere: `generator/htmlart.py`, `tools/gen_images.py`.
- Acceptare: două articole cu categorie schimbată manual produc două fișiere diferite; badge-ul
  citit din JPEG (OCR sau inspecție vizuală) coincide cu eticheta HTML.
- Cost: ~204 MB rescriși în repo, 2 randări Chromium/articol, build-uri Cloudflare (plafon ~500/lună).

### E1 — Permalink stabil, decuplat de categorie  ·  *deblochează corectarea retroactivă*
- URL-ul devine `/<slug>/` (sau `/stiri/<slug>/`), categoria rămâne doar navigare.
- 301 de la vechile `/<categorie>/<slug>/`.
- Fișiere: `generator/render.py`, `templates/`, sitemap, `_redirects` (Cloudflare Pages).
- Acceptare: un articol care își schimbă categoria păstrează URL-ul; vechiul URL dă 301, nu 404.
- **Decizie de proprietar necesară** — atinge SEO și Google News. Nu se face fără „go" explicit.

### E2 — Locul devine câmp propriu, scris o dată la ingestie
- `clasifica()` întoarce `(nivel, nume, judet)`; se salvează în `articles.json` ca
  `place` / `place_level` / `place_judet`. Semnătura veche rămâne ca wrapper → zero teste rupte.
- Elimină recalcularea din titlu (C1) și face eticheta, dateline-ul și `contentLocation`
  să citească aceeași sursă.
- Fișiere: `generator/geo.py`, `process.py`, `state.py`, `htmlart.py`.
- Acceptare: „nu știu locul" scade de la 55% la ≤28% pe `local`, măsurat pe corpus.

### E3 — Scor de focus în loc de `max()`
- După CLIFF + NLGF: `scor = 3×titlu + 2×lead + 1×corp`, cu departajare pe nivelul cel mai specific;
  nivelul articolului derivă din locul câștigător, nu din maximul peste toate potrivirile.
- Adaugă `standard_format` („comuna X, județul Y") și `proximity` (localitate lângă județ) — regex,
  nu AI, conform ordinii de precizie NewsCatcher.
- Fișiere: `generator/geo.py`.
- Acceptare: pe gold set-ul de 40 (`64999bf0`), nivelul corect ≥ baseline actual, măsurat înainte/după.

### E4 — Axe separate: temă ȘI loc, ca la IPTC
- `topic` (rubrică tematică) și `place`/`place_level` (geografie) devin câmpuri independente.
  Prezentarea rămâne pe o axă — „o axă, o casă" e regulă de AFIȘARE, nu de model de date.
- Deblochează: un articol economic din Cluj apare și în Economie, și în Cluj, fără duplicat.
- Fișiere: `config.py` (taxonomie), `process.py`, `render.py`, `templates/`.
- **Decizie de proprietar** — schimbă navigarea site-ului.

### E5 — Poarta de calitate, ca să nu se mai repete niciodată
- Gold set-ul de 40 crește la ~150 (`local`/`zonal`/`regional`/`national`/`none`, cu locul corect).
- `tools/` primește un script care rulează atribuirea pe gold set și raportează F1 per nivel + rata
  de „loc greșit". Rulat în `tests.yml`.
- **Prag:** o scădere față de linia de bază pică PR-ul.
- Coadă de revizuire: articolele cu 2+ locuri concurente sau scor sub prag ajung în `moderation.yaml`
  pentru ochi uman, după modelul Tag Quality Assurance de la iMatrics.
- Acceptare: un PR care strică atribuirea nu poate fi merge-uit fără să se vadă în CI.

## 6. Ce a rămas necercetat (3 din 17 fațete)
1. Euristicile exacte CLIFF-CLAVIN — necesită citirea codului Java, nu există documentație publică.
2. Lucrarea germană de geolocalizare (Nature Sci Data `s41597-025-05422-w`) — WebFetch blocat de
   redirect IDP; de căutat versiune arXiv/PMC.
3. Brevetul `US 20240354352` „region specific personalized news" + lucrarea Springer „Automatic
   Extraction of Geographic Locations on Articles of Digital Newspapers".

Valoarea marginală estimată: mică — cele trei ar rafina E3, nu ar schimba ordinea etapelor.

## 7. Validări — unde NU suntem în urmă
Ca să nu se rescrie ce e deja corect:
- gărzile `_AMBIGUE` / `_COMPUSE_NEGEO` / `_TARA_OMONIMA` atacă exact problema pe care EMM o
  numește centrală (loc vs persoană, omografe);
- regexul de sufixe articulate `_ARTICOL` (`ULUI|UL|UI`) e **exact** tehnica standard pentru limbi
  flexionare: „regular expressions have been used to list all possible suffixes and suffix
  combinations";
- potrivirea obligatorie pe județ în `localities.match()` (fără fallback) previne exact eroarea de
  omonim pe care o semnalează toată literatura;
- `clasifica()` care întoarce `None` = clasa „none" din NLGF, cea cu F1 0.89. Nu e o scăpare, e
  design corect.
