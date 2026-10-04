# Dovezi: căutarea Pagefind livrează căutare reală (PR #435)

Măsurători din 2026-10-04, pe branch-ul `arena/01a1034b-izz-ro`, pe starea completă comisă
(10.518 articole în `data/articles.json`, 9.451 publicate după dedup și poarta editorială).
Fiecare număr de mai jos are comanda care l-a produs. Ce nu am putut măsura e spus ca atare
la secțiunea 5.

Documentul răspunde la trei întrebări, în ordinea în care se poate minți:

1. indexul chiar e generat de build, nu adus de mână? (§1)
2. indexul chiar răspunde la căutări, nu e un fișier gol cu nume frumos? (§2)
3. pagina `/cauta/` chiar folosește indexul acela, nu o potrivire pe titlu? (§3)

---

## 1. Indexul e generat în pipeline

O singură comandă, cea pe care o rulează deja Cloudflare Workers Builds și `tests.yml`:

```
$ PAGEFIND_STRICT=1 python -m generator.main --render-only
>> cautare: index Pagefind pentru 9451 pagini in 52 fisiere (10.46 s); 9458 fisiere de fragment sterse din bugetul gazdei
>> output: 14535 fisiere (buget 17000, marja 2465)
>> Render-only: 10518 articole din state -> output/          (46,5 s in total)

$ python -m generator.pagefind_index --verify output
>> verificat: 9451 pagini in index, 52 fisiere, fara fragmente
```

Ce rămâne pe disc, verificat după rulare:

| lucru | valoare măsurată |
|---|---|
| `output/_pagefind/` | 52 de fișiere, 1,7 MB |
| `output/_pagefind/fragment/` | **absent** — șters de `curata_bundle()` după citirea id-urilor |
| `output/search-index.json` | `{"v":2,...}`, 9.451 intrări, **9.451 cu id Pagefind**, 2.039.055 B |
| `output/build.json` → `search` | `{"ok": true, "pagini": 9451, "mapate": 9451, "fisiere": 52, "sterse": 9458, "motiv": ""}` |
| `output/build.json` → `file_count` | 14.535 (plafonul gazdei 20.000, rezerva configurată 4.400, marja 2.465) |
| `pagefind-entry.json` | `{"version":"1.5.2","languages":{"ro":{"hash":"ro_c8e5a11885","wasm":"ro","page_count":9451}}}` |
| active cu hash | `/static/search.js?v=50ab4b76` în `/cauta/index.html` |

Nicio comandă nouă nicăieri: `render.build()` cheamă `pagefind_index.ruleaza()` după ce a
scris tot HTML-ul și înainte de numarătoarea de fișiere.

**Eșecul nu e tăcut.** Ambele căi au fost executate, nu doar scrise:

```
$ PAGEFIND_STRICT=1 PAGEFIND_BIN=/nonexistent/pagefind python -m generator.main --render-only   → EXIT 1
$ PAGEFIND_BIN=/nonexistent/pagefind python -m generator.main --render-only                     → EXIT 0
   ERROR:root:!! indexul de cautare NU s-a construit (binarul Pagefind lipseste …) — /cauta/ ramane pe cautarea simplificata
   build.json.search = {"ok": false, "pagini": 0, "mapate": 0, "motiv": "binarul Pagefind lipseste …"}
   search-index.json: 9451 intrari, toate cu id null
```

Poarta HTML din CI trece pe aceleași comenzi: `count_output.py` → „sub buget, marja 2465
fisiere", `html_check.py` → „OK: legaturi interne, ancore, active si `alt`",
`title_quality_audit.py` → „OK: toate titlurile oficiale afișate respectă limita".

---

## 2. Indexul răspunde la căutări reale

Interogările de mai jos nu trec prin codul nostru de căutare: sunt date direct motorului
Pagefind (`output/_pagefind/pagefind.js` + `wasm.ro.pagefind`), adică exact binarului pe care
îl încarcă browserul. Rezultatele sunt numărate de motor, titlurile sunt luate din mapă.

**Diacritice** — același număr cu și fără:

| interogare | rezultate |
|---|---|
| „inundații" / „inundatii" | **15 / 15** |
| „licitație" / „licitatie" | **77 / 77** |
| „hotărâre" / „hotarare" | **144 / 144** |

**Stemmer de română** — formele unui cuvânt dau aceeași mulțime:

| interogare | rezultate |
|---|---|
| „buget" / „bugetul" / „bugetele" / „bugetare" | **218 / 218 / 218 / 218** |
| „primarul" / „primăriei" | **556 / 556** |

**Prefix** — de asta funcționează search-as-you-type de la a treia-patra literă:

| interogare | rezultate |
|---|---|
| „buge" → „buget" | 224 → 218 |
| „inund" | 15 |
| „consil" | 415 |

**Expresii și filtre:**

| interogare | rezultate |
|---|---|
| „buget local" | 34 (primul: *Consiliul Local Blaj a aprobat rectificarea bugetară…*) |
| „apă caldă" | 11 |
| „concurs" + `filters:{tip:"concursuri"}` | 123 din 208 nefiltrate |
| „buget" + `filters:{categorie:"economic"}` | 59 din 218 |
| fără termen, `filters:{oficial:"da"}`, `sort:{data:"desc"}` | 1.100, prima intrare e cea mai nouă (3 oct 2026, 11:12) |

Filtrele chiar există în index (`pf.filters()`): 15 categorii (`local` 3.156, `extern` 1.019,
`sport` 1.184, `economic` 759, `politic` 636, …), `oficial.da` 1.100, `tip`: `oficiale` 858,
`concursuri` 128, `hotarari` 100, `achizitii` 14. Timpul unui search: **6 ms** (`timings`).

**Zero zgomot, cu limita lui spusă pe șleau.** Indexarea e restrânsă la titlu, rezumat și
titlul integral al instituției; etichetele și meta-datele paginii nu intră. Măsurat:
„Rezumat" → **1** rezultat (ar fi fost fiecare pagină), „octombrie" → 482 (toate din textul
știrilor, nu din meta cu data), „joi" → 54, „izz.ro" → 46.

Ce NU am rezolvat, măsurat și el: Pagefind potrivește prefix **în ambele direcții** — un
cuvânt indexat care e prefixul interogării se potrivește. Deci un șir absurd care începe ca
un cuvânt scurt din index aduce paginile acelui cuvânt:

| interogare | rezultate | de ce |
|---|---|---|
| „xqzwplmkqqq" | 6 | toate conțin tokenul „X" (platforma X, Vivo X Fold6, „Principesa X") |
| „asdfgh" | 19 | toate conțin „AS" (AS Roma) |
| „zzzzzzzz" | 2 | „Galaxy Z Fold8" |
| „qx", „qqqqqq" | 0 | niciun token indexat nu e prefixul lor |

Confirmat ca mecanism, nu ghicit: „x" → 121, „xy" → 1, „xyzabc" → 1, „as" → 1.339,
„asroma" → 19, „bugetxyz" → 170. UI-ul taie deja cuvintele sub două litere (`w.length > 1`
în `static/search.js`), dar nu poate face potrivire strictă: API-ul Pagefind nu expune
această opțiune per interogare. Nu sunt rezultate inventate — fiecare e o pagină reală cu un
token real potrivit — dar „zero zgomot" înseamnă „nimic fabricat", nu „niciodată zero
rezultate la un șir absurd".

---

## 3. Pagina `/cauta/` folosește indexul

Pagina reală (`output/cauta/index.html` + `/static/search.js?v=50ab4b76`), rulată în
happy-dom. Motorul e cel real: pagina face același `import()` dinamic ca în browser, iar
`search()` ajunge la `wasm.ro.pagefind` din `output/_pagefind/` (detalii despre punte la §5).

| acțiune în pagină | ce afișează | rezultat în listă |
|---|---|---|
| tastezi „inundații" | „15 rezultate pentru „inundații”." | 15, cu `<mark>` pe *Inundații*/*inundații* |
| tastezi „inundatii" | „15 rezultate pentru „inundatii”." | aceleași 15, `<mark>` tot pe forma cu diacritice |
| tastezi „buget local" | „34 rezultate pentru „buget local”." | 34 |
| tastezi „buget" | „Primele 50 din 218 rezultate." | 50 (plafonul afișat, nu al motorului) |
| tastezi „qx" | „Niciun rezultat pentru „qx”. Încearcă un termen mai general sau o altă categorie." | 0 — fără listă de rezervă |
| alegi categoria Economie | „Primele 50 din 59 rezultate pentru categoria „Economie”." | 50 |
| apeși „Concursuri" | „…pentru concursuri · categoria „Economie”." | `aria-pressed="true"` pe buton |
| apeși „Toate anunțurile oficiale" | „Primele 50 din 1100 rezultate pentru anunțuri oficiale." | 50 |
| apeși „Toate" (resetare) | status gol | 0 — nu revărsăm arhiva |
| deschizi `/cauta/?q=inundații` | câmpul preumplut, „15 rezultate pentru „inundații”." | 15, cu `<mark>` |

Numerele din pagină sunt identice cu cele date de motor la §2 (15, 34, 218, 59, 1100) —
adică UI-ul nu numără altceva decât indexul. Consola: fără erori.

**Un bug găsit de proba asta și reparat.** La golirea câmpului, `ruleaza()` curăța lista și
ieșea devreme fără să invalideze cererile în drum; un răspuns Pagefind plecat cu ~200 ms
înainte (debounce) își găsea contorul neschimbat și redesena lista peste pagina goală.
Măsurat înainte de fix: „camp golit, fara filtre" → **1100 rezultate vechi**; după fix:
**0**. Fixul e `cerere++` în ramura aceea, iar `tests/test_cautare_pagefind.py` are acum o
gardă care pică dacă dispare (verificat: cu linia scoasă, testul eșuează).

---

## 4. Testele

```
$ python -m pytest tests/test_cautare_pagefind.py -q        → 14 passed
$ python -m pytest tests/ -q                                → 1891 passed, 4 skipped, 8 xfailed
$ python -m pytest tests/ -q -p no:randomly                 → 1891 passed, 4 skipped, 8 xfailed
$ python -m ruff check .                                    → All checks passed!
```

Cele 14 acoperă: legarea id Pagefind → articol (fericit + index lipsă + semnătură schimbată
+ fragment negzipat, fiecare cu cazul ei negativ), curățarea bundle-ului, mapa de rezultate
(id prezent / id `null`), semnalele `data-pagefind-*` din `article.html` pentru o știre
obișnuită și pentru un anunț oficial, deriva între `search.html` și constanta `SUBDIR`,
poarta `--verify` (bundle incomplet, fragmente rămase), invalidarea cererilor în drum (§3)
și o rulare cap-la-cap pe `output/` real, care se sare cu motiv dacă binarul lipsește.

În CI (`tests.yml`, jobul `html-gate`) randarea rulează cu `PAGEFIND_STRICT=1` și e urmată
de `python -m generator.pagefind_index --verify output`: un index care nu se mai construiește
oprește PR-ul, nu ajunge pe live.

---

## 5. Ce nu dovedește documentul ăsta

- **Un browser real.** Chromium nu se descarcă în sandbox (`playwright install` → download
  eșuat), iar happy-dom nu poate executa modulul Pagefind real: modulul își derivă
  `basePath` din `import.meta.url`, pe care happy-dom îl încarcă în afara unui context ESM
  (`Cannot use 'import.meta' outside a module`). Puntea folosită aici înlocuiește doar
  transportul — pagina face `fetch` la un endpoint local, iar dincolo de el rulează motorul
  real, pe indexul real, în Node. Codul de UI testat (`static/search.js`) e cel adevărat,
  neatins. Rămâne de apăsat într-un browser: prima tastă → rezultate, și `<mark>` în dark
  mode.
- **Un deploy real pe Cloudflare.** Necesită preview. Semnalul de verificat acolo:
  `/build.json` → `"search": {"ok": true, …}` și `/_pagefind/pagefind.js` cu 200.
- **Logurile joburilor GitHub Actions** nu se pot citi din sandbox (blobele de loguri sunt
  pe un host inaccesibil de aici). Verificarea CI se bazează pe starea check-urilor, nu pe
  textul logurilor.

## Cum se reproduce

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m generator.main --render-only                  # indexul apare singur
python -m generator.pagefind_index --verify output
python -m http.server 8899 --directory output           # → /cauta/ in browser, motor real
python -m pytest tests/test_cautare_pagefind.py -q
```

Pentru interogările de la §2 și probele UI de la §3 e nevoie de Node (motorul Pagefind e
wasm și se încarcă și în Node, cu `fetch` adaptat pentru `file://`); rețeta e în PR, în
comentariul de dovezi.
