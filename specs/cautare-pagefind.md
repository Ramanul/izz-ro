# SPEC — căutare instantă cu Pagefind (index static în pipeline, plan 100% gratuit)

**Cerere, 2026-10-03:** căutarea de pe `/cauta/` e slabă. Trebuie căutare instantă, index
generat automat la build, diacritice românești, highlight, UI în română, zero rezultate
umplutură — totul pe planuri gratuite (GitHub Actions + Cloudflare Workers Free).

## 1. Fapte verificate (măsurate, nu din memorie)

Toate măsurătorile de mai jos sunt din 2026-10-03, pe `data/articles.json` la acel moment
(11.792 articole în stare) și pe Pagefind 1.5.2.

| Fapt | Cum a fost verificat |
|---|---|
| Randarea publică **9.451** de pagini de articol; `output/` are **14.483** de fișiere înainte de indexare. | `python -m generator.main --render-only` + `tools/count_output.py` |
| Buget configurat 17.000, plafonul gazdei 20.000 (`generator/config.py`), marja reală 2.517 fișiere. | logul randării: `>> output: 14483 fisiere (buget 17000, marja 2517)` |
| Pagefind scrie **un fișier de fragment per pagină**. Nu e o setare: e forma indexului. | `find output/_pagefind/fragment -type f \| wc -l` = 9.458 la 9.451 pagini |
| Fără fragmente, bundle-ul are **52 de fișiere / 1,7 MB**. | `find output/_pagefind -type f \| wc -l` după `curata_bundle()` |
| Indexarea a **9.451** de pagini durează **~10 s**. | log: `>> cautare: index Pagefind pentru 9451 pagini in 52 fisiere (10.37 s)` |
| Binarul `pagefind-bin` (5 MB) produce `wasm.ro.pagefind` și `pagefind.js` **identice octet cu octet** cu ale lui `pagefind-bin-extended` (52 MB). | `md5sum` pe output-urile celor două binare, ambele cu `--force-language ro` |
| Wheel-uri PyPI pentru linux x86_64/aarch64, macOS arm64/x86_64, Windows amd64/arm64. | `pypi.org/pypi/pagefind-bin/json` |
| Pagefind pliază diacriticele în ambele direcții: „inundatii" și „inundații" dau același număr de rezultate. | interogări rulate pe indexul real: 15 / 15 |
| Pagefind face stemming de română: „buget" găsește „bugetară", „bugetar", „bugetul". | „buget" → 218 rezultate, „bugetele" → 218 |
| Pagefind face potrivire pe **prefix**, în ambele direcții. | „buge" → 224, „bugetxyz" → 170, „qx" → 0 |
| Nu există potrivire fuzzy pe distanță de editare: un termen care nu există nu umple lista. | „xqzwplmkqqq" → 0 rezultate în UI |
| Fragmentul e gzip + semnatura `pagefind_dcd` + JSON cu `url`. | `gzip.decompress()` pe un fragment real |
| Id-ul întors de `search()` (`ro_1a2b3c4`) e exact numele fișierului de fragment. | `pagefind.js` 1.5.2: `loadFragment(hash)` cere `fragment/${hash}.pf_fragment` |

## 2. Problema de buget, calculată

Pe Workers Free, o versiune de Worker are cel mult 20.000 de fișiere statice, iar un deploy
supradimensionat e **refuzat tacut** (incidentul din 2026-08-21: job verde, site înghețat
21 de ore). Deci indexul trebuie să încapă în `output/`, nu lângă el.

| Variantă | fișiere în `output/` | față de plafon |
|---|---|---|
| azi, fără căutare indexată | 14.483 | 72% |
| **Pagefind cu fragmente** (forma implicită) | 14.483 + 9.458 = **23.941** | **120% — deploy respins** |
| **Pagefind fără fragmente** (ales) | 14.483 + 52 = **14.535** | 73%, marja 2.465 |

Variantele respinse și de ce:

- **Indexul pe gh-pages** (oglinda existentă, `keep_files: true`). Ar fi păstrat fragmentele,
  deci și excerptele. Cost: bucățile de index au nume-amprentate, deci s-ar adăuga ~50 de
  fișiere noi la fiecare republicare, de ~12 ori pe zi, într-un repo cu plafon 1 GB măsurat
  deja lunar; plus CORS/CSP pe o a doua origine și o dependență nouă de jobul `mirror`.
- **Al doilea Worker** pentru `_pagefind/`. Ar fi respectat plafonul (20.000 per versiune),
  dar cere un al doilea deploy, CORS și un Worker care rulează cod la fiecare cerere de
  index — adică fix complexitatea pe care planul gratuit trebuia să o evite.
- **TTL mai mic** ca să încapă fragmentele. Ar fi tăiat arhiva la ~4 zile ca să plătim o
  funcție de căutare — exact compromisul pe care `ARTICLE_TTL_DAYS` îl refuză (#198).

## 3. Decizia

**Index Pagefind fără fragmente**, servit de pe aceeași origine, cu o mapă de rezultate
generată la build.

```
render.build()  →  scrie tot HTML-ul
                →  pagefind_index.ruleaza(output/)
                     ├─ pagefind --site output --output-path output/_pagefind --force-language ro
                     ├─ harta_url_id(): citește fragmentele și le transformă în {url: id}
                     └─ curata_bundle(): șterge fragment/ și UI-urile nefolosite
                →  _write_search_index(): search-index.json, intrările poartă id-ul Pagefind
                →  _write_build_metadata(): file_count include bundle-ul; build.json poartă
                   starea căutării (ok/pagini/mapate/fisiere/motiv)
```

Ce pierde și ce câștigă această alegere, fără ocol:

| | |
|---|---|
| **Pierdem** | excerptul din corpul articolului sub titlu (fragmentul e sursa lui) |
| **Păstrăm** | potrivirea pe titlu **și** pe textul rezumatului, ierarhia BM25, stemmer de română, plierea diacriticelor, filtrele, sortarea pe dată |
| **Câștigăm** | 52 de fișiere în loc de 9.458; la prima tastă se descarcă bucata de index care conține termenii (~17 KB), nu tot corpusul |

## 4. Ce se indexează (și de ce nu tot)

`data-pagefind-body` stă pe **titlu**, pe **rezumat** și pe **titlul integral al instituției**
(pentru anunțurile oficiale, unde titlul afișat e scurtat). Nimic altceva. Măsurat pe
indexul real, cu `data-pagefind-body` pus inițial pe `<article>` întreg:

| termen | rezultate | de ce e zgomot |
|---|---|---|
| „Rezumat" | toate paginile | eticheta de încredere „Rezumat dintr-o sursă · verifică…" |
| „octombrie" | toate paginile din lună | meta cu data publicării |
| „HotNews" | toate paginile acelei surse | lista de surse |
| „joi" / „izz.ro" | paginile zilei | textul desenat în arta generată |

După restrângere: „Rezumat" → 1 rezultat (un articol care chiar îl are în titlu),
„octombrie" → 482 (toate din textul știrilor, nu din șablon).

Filtrele Pagefind (`data-pagefind-filter`) duc butoanele existente în index, în loc să fie
aplicate client-side peste o listă deja trunchiată: `categorie` (selectorul), `tip`
(concursuri/hotărâri/achiziții/oficiale) și `oficial: da` („Toate anunțurile oficiale").
Sortarea pe `data` e tăiată la secundă — 15 articole din stare au `published` cu
microsecunde, iar Pagefind sortează lexicografic.

## 5. Comportamentul căutării

- **Instant**: `input` cu debounce 200 ms; modulul Pagefind și mapa se încarcă în paralel la
  prima tastă.
- **Diacritice**: indiferent de cum tastezi. Pagefind pliază termenii; mapa e pliată și ea
  pentru marcare și pentru modul simplificat.
- **Highlight**: termenii sunt marcați cu `<mark>` în titlu, pe fondul `--gold-wash` al temei
  (deci se inversează corect în dark mode). Marcarea se face pe șirul pliat, dar taie din
  cel original, ca textul afișat să rămână exact.
- **Zero zgomot**: se afișează exact ce a potrivit indexul. La zero potriviri, mesajul e
  „Niciun rezultat pentru „X"" plus o sugestie, nu o listă de rezervă. Un id pe care mapa nu
  îl cunoaște nu devine rezultat.
- **Fără JavaScript**: `<noscript>` spune că e nevoie de JavaScript și trimite la secțiuni.
- **Legături partajabile**: `?q=` umple câmpul și rulează căutarea; adresa se actualizează la
  tastare.

**Mod degradat, anunțat.** Dacă `_pagefind/` lipsește (build fără binar) sau modulul nu are
API-ul așteptat, pagina cade pe o căutare doar în titluri și **spune asta** în rândul de
stare. Un mod degradat care nu se anunță e mai rău decât o eroare.

## 6. Eșecul în pipeline

| mediu | comportament |
|---|---|
| producție (Cloudflare Workers Builds) | binar lipsă sau Pagefind picat → randarea **continuă**, `/cauta/` cade pe modul simplificat, `build.json.search.ok = false` |
| CI (`tests.yml`, jobul `html-gate`) | `PAGEFIND_STRICT=1` → randarea **pică**; apoi `pagefind_index --verify output` verifică bundle-ul |
| jobul `mirror` (gh-pages) | `PAGEFIND_ENABLED=0` — oglinda nu servește `/cauta/`, iar bucățile de index nume-amprentate ar umfla arhiva degeaba |

Motivul împărțirii: un build care moare din cauza căutării ar îngheța site-ul, exact
incidentul pe care bugetul de fișiere îl apără. Dar un index care încetează să se mai
construiască trebuie să fie roșu undeva — deci e roșu în PR.

`harta_url_id()` **ridică** dacă semnatura fragmentului nu e `pagefind_dcd`. O mapă goală ar
trece testele și ar lăsa `/cauta/` fără niciun rezultat: un eșec tacut, cel mai scump fel.
Versiunea Pagefind e fixată în `requirements.txt` tocmai pentru ca semnătura să nu se miște
sub noi.

## 7. Costuri (toate zero în bani)

| | |
|---|---|
| Build | +5 MB la `pip install` (wheel `pagefind-bin`), +10 s la randare, +1,7 MB în `output/` |
| Runtime | o cerere `/_pagefind/pagefind.js` + una pentru mapa de rezultate + bucata de index care conține termenii (~17 KB) |
| Terți | niciunul: indexul e al nostru, servit de pe izz.ro, fără CDN extern, fără chei |

## 8. Verificări

```bash
python -m ruff check .                      # lint
python -m pytest tests/ -q                  # suita (include tests/test_cautare_pagefind.py)
python -m generator.main --render-only      # randare + index
python -m generator.pagefind_index --verify output
python tools/count_output.py                # bugetul de fișiere
python -m http.server 8000 --directory output   # /cauta/ în browser
```

Ce **nu** poate fi verificat în sandbox și rămâne de confirmat pe preview-ul ramurii:
comportamentul într-un browser real (Chromium nu se descarcă aici). Interogările Pagefind au
fost rulate direct pe indexul real din Node, iar UI-ul a fost rulat în happy-dom cu un stub
care are forma API-ului Pagefind; ramura „modul real încărcat" într-un browser adevărat e
acoperită de `visual.yml` (Playwright + Chromium) după merge.

## 9. Următorul pas, dacă excerptele devin prioritare

Indexul cu fragmente, servit de pe a doua origine (gh-pages sau R2 Free), cu
`pagefind.mergeIndex` sau cu `basePath` explicit. Ar costa: CORS + CSP pe o a doua origine,
curățarea fragmentelor vechi pe oglindă și o dependență de jobul `mirror` pentru o funcție
de pe prima origine. Nu e gratuit în complexitate, de aceea nu e în acest diff.
