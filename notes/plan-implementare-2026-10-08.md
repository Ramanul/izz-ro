# Plan de implementare — 8 octombrie 2026

Două rapoarte, un singur șantier. Nu se implementează tot odată și nu se începe cu spargerea lui `render.py`.

## 0. Ce e adevărat în ambele, și ce nu

Raportul de produs are dreptate pe direcție. Pentru cititor, problema nu e o gaură de securitate. E o pagină de start care nu spune ce contează, un link care poate muri, și un cod în care aceeași decizie editorială are două forme.

Raportul de securitate rămâne adevărat pe alt etaj. Un comentariu de la un străin putea porni botul AI. Un nume public care rezolvă spre o adresă internă putea fi urmat la ingestie. `/push/abonare` putea arde scrierile KV. Astea nu fac homepage-ul lung. Pot cheltui cota sau atinge un runner. Sunt deja petecite pe ramura de lucru, **necomise**. Nu se amestecă cu CSS-ul.

Ce am măsurat eu acum, pe `data/articles.json` și pe cod, nu pe capturi:

| afirmație din raportul de produs | verdict |
|---|---|
| `render.py` 2.224 linii, `schema.py` lipsește, TTL 12, grid `minmax(310px, 1fr)` | adevărat |
| 11.533 articole, 58 fără slug, 7 coliziuni `(categorie, slug)`, 631 model C din care 314 au `members` și `story_id` | adevărat, pe discul ăsta |
| `regional` 17, `discounturi` 21, `HOME_CARDS_PER_CATEGORY = 4` | adevărat. 15 secțiuni × 4 carduri explică homepage-ul de ~35.000 px fără să fie nevoie de captură |
| `process_cluster` nu pune `members` / `story_id`, `_prep_cluster_rep` pune | adevărat. A doua cale e lotul, prima e apelul singular |
| README spune „assets-only, fără `main`”; `wrangler.jsonc` are `main` | adevărat |
| cronul nu e la 30 de minute | adevărat. `build.yml` e `13 * * * *`, cu poartă la ~105 minute. Fraza „la fiecare 30 de minute” e doar starea goală din `templates/index.html` |
| `sitemap.xml` folosește `published`, JSON-LD folosește `updated` | adevărat pentru sitemapul principal (`render.py`, bucla din `_write_sitemap`). `sitemap-priority.xml` folosește deja `updated or published` |
| `state.merge()` compară URL-uri brute și de-aia apar duplicate | fals ca incident. Funcția există și compară `a["url"]` brut, dar **nu e chemată în producție**. Comentariul din `main.py` o spune. Calea reală deduplică pe `url` deja trecut prin `normalize_url`. Cele două `normalize_url` din `tools/check_*.py` sunt scripturi de scan, nu ingestia |
| linkul expiră și rămâne 404 | pe jumătate. TTL-ul de 12 zile există din cauza plafonului de 20.000 de fișiere. Oglinda (`infra/worker-404-mirror.js`, `keep_files: true`) e făcută tocmai ca permalinkul vechi să răspundă de pe gh-pages, sub același host. 404-ul local e plasa când oglinda nu are pagina. Nu se construiește a doua arhivă |
| ID-uri SVG duplicate pe județe | nu le-am găsit. Harta desenează `path` cu `data-judet`, nu cu `id`. Nu intră în plan până nu e reprodus |
| 2.057 teste, Lighthouse 94/97, CLS măsurat | măsurătorile lor, nu ale mele. Nu le folosesc ca poartă. Nu am rerulat suita întreagă și nu am rulat Lighthouse în sesiunea asta |
| worktree curat, doar `.venv/` | fals pe ramura asta. Patch-ul de securitate e modificat și necomis |

## 1. Reguli de șantier

1. Un val, un tip de risc. Securitatea nu intră în același diff cu homepage-ul.
2. Nu se sparge `render.py` înainte de o plasă de echivalență. `tools/echivalenta.py` există pentru asta. O mutare de funcții fără diff de output e cum se strică sitemapul.
3. Nu se urcă TTL-ul ca să „repare SEO”. Urcarea umple plafonul și taie altceva.
4. Nu se editează `data/articles.json` de mână. Slugurile lipsă le scrie pipeline-ul, la următoarea rulare, și le comite el.
5. Orice invariant nou are un test care pică pe codul de dinainte. Altfel e un comentariu.
6. Setările din dashboard (checks obligatorii, environment `production`, ștergerea runnerului) nu sunt cod. Rămân la proprietar.

## 2. Valul 0 — patch-ul care e deja scris

**Intră singur, înainte de orice altceva.** E pe working tree, nu pe `main`.

- porțile de workflow, zero interpolare de input în `run:`, CUA scos de pe runnerul Windows;
- DNS fixat la conectare în `generator/fetch.py`;
- cotă și plafon de corp pe `/push/abonare`.

Nu se mai adaugă nimic în diff-ul ăsta. Dashboard-ul rămâne deschis: fără checks obligatorii, un workflow reparat nu oprește un push.

## 3. Valul 1 — primul ecran, fără schimbare de model

Scop: la 320 px nu mai există overflow, iar primul rezumat nu stă sub bară. Fără briefing, fără „localitatea mea”, fără rescrierea homepage-ului.

### 1.1 Grid

`static/styles.css`, regula `.grid`:

`repeat(auto-fill, minmax(min(310px, 100%), 1fr))`

Un test care citește fișierul și pică dacă `minmax(310px, 1fr)` revine fără `min(`. Nu e un test vizual. E garda împotriva revenirii. Verificarea vizuală la 320 / 375 / 412 rămâne manuală, pe un preview, nu pe o captură veche.

### 1.2 Header și subnav

Subnav-ul nu mai e `position: sticky` sub 720 px. Nu se promite „150 px” până nu se măsoară pe preview. Criteriul e: după pliere, primul titlu de știre e în primul ecran la 320 px, fără scroll. Dacă nu e, se taie din hero (mărime de titlu, nu din funcție), nu se mai adaugă reguli.

### 1.3 Bara de consimțământ

Rămâne jos, rămâne textul legal. Se strânge la o linie plus două butoane. `body` primește `padding-bottom` egal cu înălțimea bării cât timp bara e vizibilă, ca să nu acopere ultimul card. Nu se mută în header.

### 1.4 Homepage, doar doza

`HOME_CARDS_PER_CATEGORY` rămâne 4 pe desktop. Pe mobil, șablonul nu mai emite decât 2 carduri per categorie. `display: none` pe carduri deja emise lasă DOM-ul lung pentru cititorul de ecran și pentru Pagefind, deci tăierea e în datele date șablonului, nu în CSS.

Categoriile cu sub 8 articole în fereastră (`regional`, `discounturi` azi) nu mai primesc secțiune pe homepage. Rămân în nav. Asta e o decizie de produs luată aici, ca să nu blocheze valul: o secțiune de 4 carduri pentru 17 articole nu e o rubrică, e zgomot. Dacă proprietarul vrea rubricile vizibile oricum, se revine într-o linie.

### 1.5 Nav

`aria-current="page"` lângă clasa `active`, în `templates/base.html`. Clasa rămâne pentru stil.

### 1.6 404, doar meta

`404.html` e servit de `not_found_handling: 404-page`. Statusul HTTP nu se pune din HTML. Ce se pune:

- `noindex, follow` pe șablonul folosit de 404, nu pe categorii;
- fără canonical către `/404.html`;
- textul care spune deja că articolul a expirat rămâne. Nu se promit „articole similare” calculate pe un URL pe care pagina statică nu îl cunoaște.

Pagina mai deșteaptă, cea care știe ce permalink a murit, e în Worker, valul 3. Nu aici.

### 1.7 Căutare

Limita de 50 rămâne ca pagină, nu ca tavan. Buton „încă 50” care taie din lista deja calculată. Nu se încarcă un al doilea index.

### Ce nu intră în valul 1

Dialogul de profil (focus, Escape, `aria-modal`) e real și mic, dar nu e motivul pentru care homepage-ul are 35.000 px. Intră imediat după 1.1–1.4, în același PR doar dacă diff-ul rămâne în `personalize.js` plus un test de tastatură dacă există harness. Dacă nu există harness, PR separat, cu pași manuali scriși în descriere. Nu se construiește un browser de test pentru un dialog.

PWA cu căi absolute e corect pe `izz.ro`. Nu e defectul de produs. Nu se atinge `site.webmanifest` în valul ăsta.

## 4. Valul 2 — un singur contract de articol, nu o rescriere

### 2.1 O singură cale pentru modelul C

`process_cluster` își construiește reprezentantul singur și uită `members` și `story_id`. `_prep_cluster_rep` le pune. Prima funcție trebuie să cheme a doua și să păstreze doar apelul AI. Test: același grup, cu provider `None` și cu provider fals, produce aceleași chei structurale (`model`, `sources`, `members`, `story_id`, `updated` când e actualizare).

Cele 317 sinteze C deja comise nu se repară editând JSON-ul. La următoarea salvare, o funcție de reparare, idempotentă:

- dacă lipsește `story_id`, îl derivă din `published` + `original_link` sau `url`, cu aceeași funcție `_story_id`;
- dacă lipsesc `members`, un singur membru: articolul însuși. Nu se inventează un timeline.

Abia după o rulare în care cifra „C fără story_id” e 0 se închide poarta: `save` refuză un C nou fără cele două câmpuri. Înainte de poartă, refuzul ar opri publicarea pe starea de azi.

### 2.2 Slug

`assign_slugs()` repară în memorie și ascunde cele 58 de lipsuri. Pipeline-ul trebuie să salveze slugul pe care l-a atribuit. Test pe o stare minimă: un articol fără slug intră, iese cu slug, a doua rulare păstrează același slug. Coliziunile (7 perechi) nu se rezolvă redenumind în repo. Se rezolvă prin regula deja existentă de slug, aplicată o dată și persistată. Un slug deja public nu se schimbă: ar rupe permalinkul pe care oglinda încă îl servește.

### 2.3 `merge()`

Nu se „repară” ca și cum ar fi gaura de dedup. Se face una din două, într-un commit de igienă, nu în același diff cu slugurile:

- fie dispare, iar testul se mută pe dedup-ul din `main.py`;
- fie `main.py` o cheamă, pe URL-ul deja normalizat, și comentariul care spune că nu e folosită se șterge.

Nu se unifică `normalize_url` din scripturile de primării cu cea din `generator/util.py` în valul ăsta. Au alt contract (pun `https://` și taie slash-ul). Amestecul le strică scanarea.

### 2.4 Validator, nu TypedDict

`specs/arhitectura-cuplare.md` cere `schema.py` ca adnotare, și spune că fără mypy e documentație. Nu se adaugă mypy ca să se justifice un fișier. Se adaugă o funcție mică, chemată înainte de `save`, care verifică forma:

- `url`, `category`, `slug`, `published`, `model` prezente după reparare;
- `model == "C"` implică `story_id` și `members`;
- `published` e ISO cu `+00:00` (invariantul pe care `state.py` îl impune deja).

Eșecul la salvare oprește publicarea. Eșecul la citirea stării vechi nu oprește nimic până trece repararea din 2.1 și 2.2. Altfel poarta pedepsește corpusul pentru un cod care încă nu a rulat.

### 2.5 Ce nu se sparge

`render.py` rămâne un fișier lung până când un diff de mutare trece `echivalenta` de două ori, pe aceeași stare. Primul candidat de extras, când se ajunge acolo, e sitemapul (`_write_sitemap` și frații), pentru că e pur și are teste. Nu Jinja, nu imaginile, nu bugetul, în același pas.

`.coverage` și `static/styles.dark.bak.css` ies într-un commit de igienă, împreună cu `.venv/` în `.gitignore`. Nu în diff-ul de sitemap.

## 5. Valul 3 — continuitatea linkului, în plafonul care există

Nu se urcă `ARTICLE_TTL_DAYS`. Lanțul e deja scris în `notes/plan-master-izz-2026-10-03.md`: fișiere → TTL → link mort. Oglinda e răspunsul construit. Valul ăsta o verifică și îi închide restul.

### 3.1 Proba de oglindă

Înainte de cod nou: un permalink mai vechi de 12 zile, cerut pe izz.ro, trebuie să vină de pe oglindă cu 200, nu cu pagina „Pagina negăsită”. `verify_release.py` e unealta. Dacă proba pică, se repară lista pozitivă din `worker-404-mirror.js`, nu se inventează alt storage.

### 3.2 Sitemap

`_write_sitemap` pune `lastmod` din `published`. JSON-LD pune `dateModified` din `updated or published`. O funcție, folosită de ambele sitemapuri de articole: `(updated or published)[:10]`. Categoriile iau maximul aceleiași valori, nu doar `published`. Test pe un articol cu `updated` mai nou decât `published`.

Paginile `/categorie/2/` nu intră în sitemap. Primesc `noindex, follow`. Sunt navigație, nu pagini de aterizare, și au același title cu pagina 1. Titluri distincte fără conținut distinct nu ajută. Asta contrazice varianta „bagă-le în sitemap” din raport. Varianta cealaltă, `noindex`, e cea corectă aici.

### 3.3 Pagina de județ

`/harta/<judet>/` are title și description unice și o listă care spune „Se încarcă…”. În `_render_harta_shell` se injectează în `#news-list` primele 8 știri deja localizate pe județul ăla, cu dată, sursă și link. JavaScript-ul le înlocuiește când are datele lui. Fără pagini noi, fără fișiere în plus față de cele 42 de județe care se emit deja.

Sursa listei e aceeași atribuire ca pe harta mică (`judetean` / `local` + județul sursei), nu un al doilea clasificator.

### 3.4 RSS

Nu se deschid feeduri noi în valul ăsta. Se adaugă, în feedul existent, `category` și sursa, din câmpuri care există. Imaginea doar dacă e `cover_propriu`, ca să nu se pună în feed o copertă de categorie repetată. Feed pe județ și „localitatea mea” sunt valul 4: cer pin în browser și o regulă de produs, nu un tag.

## 6. Valul 4 — produsul, după ce primele trei țin

Ordinea din planul de pe 3 octombrie rămâne bună. Nu se reface.

1. Briefingul promis și neemis (`content/newsletter.html` lipsește, blocul nu se randează).
2. Legătura știre → ghid, determinist, fără AI.
3. „Localitatea mea”: pin în `localStorage`, secțiunea județului înaintea celorlalte. Datele există.
4. Timeline doar pe C cu cel puțin 3 domenii, din `members`. Fără `members` uniform, timeline-ul minte. De asta stă după valul 2.
5. Controale de text și print. După primul ecran, nu înainte.

Homepage-ul în cinci blocuri („ce s-a întâmplat”, „ce te poate afecta”, „ce urmează”, „din surse diferite”, „explorează”) înlocuiește cele 15 secțiuni doar după valul 1. Altfel se reproiectează o pagină care încă dă overflow.

## 7. Ce rămâne decizie, nu task

| întrebare | recomandarea din plan | de ce nu e task |
|---|---|---|
| Portal național sau instrument local? | ambele, în ordinea asta pe homepage: țara, apoi județul ales | fără pin, „local” e o rubrică goală |
| Linkurile rămân permanente? | da, prin oglindă, nu prin TTL infinit | plafonul de 20.000 nu se negociază în cod |
| AI publică fără om? | da, asta e sistemul de azi; garda de conținut e cea existentă | un om pe 11.533 de articole nu e un patch |
| Categoriile subțiri pe homepage? | nu, până au 8 în fereastră | reversibil într-o constantă |
| PWA e strategic? | nu în valurile 1–3 | căile absolute sunt corecte pe domeniul rădăcină |
| Se plătește ca să dispară plafonul? | nu e necesar cât timp oglinda răspunde | de verificat live înainte de orice discuție de plan plătit |

## 8. Ordinea de PR

1. Securitate, diff-ul deja scris. Fără UX.
2. Igienă: `.gitignore`, `.coverage`, backup-ul CSS, fraza de 30 de minute, README-ul care încă spune „fără `main`”, comentariul din `render.py` care încă vorbește de 20–30 de zile. Zero comportament.
3. Primul ecran: grid, header, bară, două carduri pe mobil, `aria-current`.
4. 404 meta + `noindex` pe paginare + `lastmod`.
5. O cale pentru modelul C + reparare la salvare. Poarta de formă rămâne oprită până cifra e 0.
6. Slug persistat, fără redenumirea celor deja publice.
7. Lista de județ în HTML-ul inițial.
8. Abia apoi extras de sitemap din `render.py`, dacă echivalența e verde de două ori.

`continue-on-error` de pe testele din `build.yml` nu se scoate în PR-ul 1. Workflow-ul separat de CI poate fi deja blocant pe PR-uri umane. Commitul botului pe `main` nu pornește workflow-uri. Fără checks obligatorii în Settings, scoaterea comutatorului nu oprește publicarea. Se scoate după ce proprietarul bifează check-ul, nu înainte.

## 9. Gata, pentru valurile 1–3

- la 320 px, niciun scroll orizontal pe homepage și pe un articol;
- primul titlu vizibil fără ca bara să-l acopere;
- 404 cu `noindex` și fără canonical către `/404.html`;
- un URL de articol mai vechi de 12 zile răspunde 200 de pe oglindă, verificat live, nu din comentariu;
- zero articole C noi fără `story_id` și `members`;
- zero sluguri noi lipsă după o rulare de pipeline;
- `sitemap.xml` și JSON-LD spun aceeași zi pentru un articol actualizat;
- `/categorie/2/` are `noindex, follow`;
- `/harta/<judet>/` are în HTML, fără JS, cel puțin un link de știre când județul are știri în fereastră;
- patch-ul de securitate e pe `main` sau e abandonat explicit. Nu rămâne amestecat cu valul 1.

## 10. Ce s-a implementat pe 8 octombrie, după plan

Patch-ul de securitate stă în același arbore. Nu s-a putut despărți pe un al doilea PR: sesiunea are o singură ramură.

Făcut: igienă (`.gitignore`, `.coverage` și backup-ul CSS scoase din index), README, fraza de 30 de minute, comentariul de TTL, grid, header nesticky sub 720 px, bară strânsă, două carduri emise în DOM pe mobil (celelalte două, până la 4, stau într-un `<template>` și intră în grilă doar de la 641 px), rubrici sub 8 articole scoase de pe homepage, `aria-current`, 404 `noindex` fără canonical, paginile 2+ `noindex`, `lastmod` din `updated`, o singură pregătire pentru modelul C, reparare la salvare, slug pe tot corpusul salvat, `merge()` pe URL normalizat, lista de județ în HTML, categorie și sursă în feed, „încă 50” la căutare, dialog cu focus și Escape.

Valul 4, fără cont Brevo și fără text nou: pagina `/azi/` (titlu, link, număr de surse), legătură deterministă știre → ghid, „localitatea mea” în `localStorage` cu secțiunea județului înaintea rubricilor, timeline doar pe modelul C cu cel puțin 3 domenii, controale de text și tipărire. Flux RSS și pe categorie, nu pe județ.

Nefăcut, dinadins: proba live a oglinzii (rețeaua de aici nu ajunge la izz.ro), checks din Settings, scoaterea lui `continue-on-error`, extrasul sitemapului din `render.py`, feed pe județ, embed Brevo. Poarta de la salvare refuză un C doar dacă repararea nu a putut scrie `story_id`. Nu refuză înainte de reparare și nu oprește corpusul de azi.

## 11. Planul, punct cu punct

Asta se implementează. Nimic din lista asta nu așteaptă un răspuns nou, în afara punctelor marcate „după probă”.

1. Comit separat pentru patch-ul de securitate deja scris: porți de workflow, DNS la conectare, cotă și plafon de corp pe `/push/abonare`. Fără CSS, fără `articles.json`.
2. Checks obligatorii, environment `production`, ștergerea runnerului Windows. Nu e cod. Rămâne la proprietar. Nu blochează punctele 3–16.
3. `.venv/` în `.gitignore`. Scoaterea lui `.coverage` și a lui `static/styles.dark.bak.css` din Git. Commit de igienă, zero comportament.
4. README-ul spune că `wrangler.jsonc` are `main` și că publicarea nu mai e assets-only. Ștergerea frazei „robotul rulează la fiecare 30 de minute”. Comentariul din `render.py` care încă vorbește de 20–30 de zile se aliniază la TTL 12.
5. Grid: `minmax(min(310px, 100%), 1fr)`. Test care pică dacă revine `minmax(310px, 1fr)` fără `min(`.
6. Subnav-ul nu mai e sticky sub 720 px. Hero-ul se micșorează doar dacă, după asta, primul titlu tot nu încape în primul ecran la 320 px.
7. Bara de consimțământ: o linie și două butoane. `padding-bottom` pe `body` cât bara e vizibilă.
8. Pe mobil, homepage-ul emite 2 carduri per categorie, nu 4. Categoriile cu sub 8 articole în fereastră nu mai au secțiune pe homepage. Rămân în nav.
9. `aria-current="page"` lângă clasa `active` în `templates/base.html`.
10. 404: `noindex, follow`, fără canonical către `/404.html`. Statusul HTTP rămâne cel pus de `not_found_handling`.
11. Căutarea: buton „încă 50”, nu ridicarea plafonului dintr-o dată.
12. Dialogul de profil: `aria-modal`, focus la deschidere, Escape, focus înapoi la buton. PR separat dacă nu există harness.
13. `process_cluster` cheamă `_prep_cluster_rep`. Test: aceleași chei structurale pe ambele căi.
14. La salvare, reparare idempotentă: C fără `story_id` îl primește din articolul însuși; C fără `members` primește un singur membru, el însuși. Nu se editează `articles.json` de mână.
15. După o rulare în care „C fără story_id” e 0, `save` refuză un C nou fără `story_id` și `members`. Până atunci poarta stă oprită.
16. Slugul atribuit în memorie se salvează. A doua rulare păstrează același slug. Un slug deja public nu se redenumește.
17. `merge()`: fie dispare și testul se mută pe dedup-ul din `main.py`, fie `main.py` o cheamă pe URL-ul deja normalizat. Nu se unifică `normalize_url` din scripturile de primării.
18. Paginile `/categorie/2/` și următoarele: `noindex, follow`. Nu intră în sitemap.
19. `lastmod` în `sitemap.xml` din `updated or published`, la fel ca JSON-LD. Categoriile iau maximul aceleiași valori.
20. După probă live: un permalink mai vechi de 12 zile pe izz.ro răspunde 200 de pe oglindă. Dacă pică, se repară lista din `worker-404-mirror.js`. Nu se urcă TTL-ul.
21. În `/harta/<judet>/`, `#news-list` primește în HTML primele 8 știri ale județului. JS le poate înlocui după încărcare.
22. În feedul existent: `category` și sursa. Imaginea doar dacă `cover_propriu`.
23. Extrasul sitemapului din `render.py`, doar dacă `echivalenta` e verde de două ori pe aceeași stare.

Nu se implementează acum: urcarea TTL-ului, a doua arhivă, spargerea lui `render.py` ca prim pas, scoaterea lui `continue-on-error` înainte de checks, PWA pe subpath, ID-uri SVG care nu se reproduc, briefingul, „localitatea mea”, timeline-ul, ghidurile legate de știri, feedurile pe județ.

## 12. Întrebările din date. Ce are răspuns și ce nu

Datele nu sunt un interviu. Unde corpusul sau codul răspund, o spun. Unde am ales eu ca planul să nu stea, o marchez ca decizie, nu ca fapt.

1. **Portal național sau instrument local?** Nu are răspuns în date. Corpusul e național: 10.902 articole B, homepage-ul listează toate categoriile. Județul există ca hartă și ca rubrică, nu ca prima pagină. Am decis pentru implementare: țara întâi, județul ales după ce există pin. Nu e ce vrea proprietarul. E ce poate codul fără un pin care încă nu există.
2. **Linkurile trebuie să rămână permanente?** Da, în codul deja scris. TTL 12 e plafonul de fișiere, nu o decizie editorială de a ucide URL-ul. Oglinda e făcută să păstreze permalinkul. Nu am verificat live că un URL vechi chiar răspunde 200. Răspunsul de arhitectură e da. Răspunsul de funcționare e punctul 20.
3. **AI-ul publică fără om?** Da. Asta e sistemul care rulează: pipeline-ul procesează și comite, nu există poartă umană pe publicare. Datele nu spun dacă proprietarul o vrea schimbată. Planul nu adaugă una. Un om pe 11.533 de articole nu e un patch.
4. **Cine e utilizatorul principal: mobil rapid, locuitor de județ sau ghiduri?** Nu are răspuns în date. Nu există analitice în ce am primit. Am pus mobilul primul pentru că defectul măsurat e acolo: overflow la 320 px și homepage de ~35.000 px. Județul și ghidurile sunt puncte ulterioare, nu pentru că am măsurat că sunt secundare.
5. **Categoriile subțiri se afișează sau se ascund?** Datele spun cât au: `regional` 17, `discounturi` 21. Nu spun ce vrea proprietarul. Am decis: sub 8 în fereastră, fără secțiune pe homepage, rămân în nav. E reversibil într-o constantă. Nu e un fapt măsurat despre utilizatori.
6. **PWA-ul e strategic sau experiment?** Nu are răspuns de la proprietar. În cod e prezent și nu e pe calea care strică primul ecran. Pe `izz.ro` căile absolute sunt corecte. L-am scos din valurile 1–3. Asta e o tăiere de scope, nu o măsurătoare că nu e folosit.
7. **Care e indicatorul de succes?** Nu am răspuns. În date nu e timp până la click, revenire, click pe sursă, abonare RSS sau folosirea ghidurilor. Fără cifra asta, planul optimizează defectele văzute (overflow, 404, contract de date), nu un obiectiv de produs. Dacă unul din cei cinci contează mai mult, ordinea punctelor 8, 21 și a valului 4 se schimbă.
8. **Se plătește ca să dispară plafonul de 20.000?** Nu am răspuns. Nu e în repo. Recomandarea tehnică: nu e nevoie cât timp punctul 20 trece. Dacă oglinda nu ține permalinkul, întrebarea devine reală. Până atunci, plata nu e un task.
