# Randarea din teste — 97% din suită stă într-o singură fixtură

> **Spec, nu implementare.** Măsurătoarea e făcută și nu trebuie refăcută; decizia de design și
> execuția rămân pentru o felie proprie, **după** ce aterizează PR-urile de reguli în zbor
> (#227, #228), fiindcă remediul atinge cod de producție și nu are ce căuta într-un flux de
> igienă a regulilor.

## Măsurat 2026-08-29

`python -m pytest tests/ -q --durations=25`, local, container curat:

```
1194 passed, 1 skipped, 8 xfailed in 647.50s (0:10:47)

626.40s  setup  tests/test_entities_verified.py::test_eticheta_si_avertismentul_se_exclud_pe_fiecare_ghid
  9.28s  call   tests/test_ai_budget_reserve.py::test_run_pastreaza_rezerva_cand_exista_restanta
  2.47s  call   tests/test_state_resync.py::test_starea_reala_e_vindecata_la_load
  ... restul, sub 1s fiecare
```

**626,40 s din 647,50 s — 97% — sunt setup-ul unei singure fixturi.** Tot restul suitei, 1194 de
teste, înseamnă ~21 de secunde. În CI aceeași suită ia ~23 de minute (măsurat de două ori:
23m16s și 23m07s), deci fiecare PR așteaptă ~20 de minute pentru o randare.

Cifra e atribuită primului test care cere fixtura; nu e vina lui `test_entities_verified`.

## Ce face fixtura și de ce e legitimă

`output_randat` (`tests/conftest.py`, `scope="session"`) rulează
`python -m generator.main --render-only` ca subproces, pe starea reală: **5.799 de articole →
34.898 de fișiere**. E **necondiționată** deliberat, iar motivul e scris în docstring-ul ei și e
un incident real: varianta veche randa doar dacă `output/ghiduri` lipsea, deci în rest valida
fișiere rămase pe disc **de pe alt commit**. „Un test lent e mai ieftin decât un test care minte."

**Nu e o fixtură risipitoare** — e partajată de cinci fișiere de teste, fiecare cu nevoie reală de
HTML emis, nu de șablon:

| fișier | ce verifică pe output real | are nevoie de scară? |
|---|---|---|
| `test_entities_verified` | eticheta „Verificat" și avertismentul se exclud pe fiecare ghid | nu |
| `test_jsonld_graph` | un singur bloc JSON-LD/pagină, zero referințe orfane | nu |
| `test_pagina_404` | pagina 404 emisă | nu |
| `test_pagination` | paginarea | **da, dar mărginit** — câteva pagini, nu 5.799 de articole |
| `test_sitemap_editorial` | structura sitemap-ului | **poate** — dacă există prag de împărțire a indexului |

## Ce am verificat că NU merge

- **`pytest-xdist` / paralelizare:** exclus. `output/` e cale fixă partajată, iar `render.build()`
  o golește **fără lock**. Două procese `pytest` pe același clone se calcă — măsurat 2026-08-16,
  documentat în docstring-ul fixturii și în registru. Nu e o limitare de ocolit, e o cauză.
- **Override de cale pentru stare:** `generator/config.py` **nu are** niciun `os.getenv` pentru
  calea stării sau a output-ului (are pentru bugete, provideri, `LOCAL_GOLD_LIMIT` — nu pentru
  astea). Deci un corpus mărginit nu se poate obține azi fără cod nou.

## Opțiunile, cu costul lor

1. **Corpus mărginit implicit, complet la cerere.** Fixtura randează ~200 de articole (destule
   pentru paginare), iar randarea completă rămâne pe un job programat / `workflow_dispatch`.
   Cere: un mecanism de limitare în `generator/` — fie `--limit N` pe `main.py`, fie un
   `os.getenv` pentru calea stării, ca fixtura să-i dea o copie trunchiată.
   **Câștig: ~20 min per PR.** **Risc: o regresie care apare doar la scară trece de CI-ul de PR**
   — de aceea randarea completă nu dispare, se mută pe alt ritm.
2. **Cache în Actions pe `output/`**, cu cheie = hash de conținut peste tot ce influențează
   randarea (`data/articles.json`, `templates/`, `generator/`, `static/`, `media/`).
   **Câștig: PR-urile doar-documente sar randarea complet.** **Risc măsurabil de verificat
   întâi:** `output/` are ~507 MB (registru, `IZZ-0237`) — upload/download-ul poate mânca
   economia, iar limita de cache pe repo e 10 GB.
3. **Nimic.** 20 de minute per PR e un cost real, dar plătit de mașină, nu de om.

**Recomandarea mea: (1), cu randarea completă mutată pe un job nocturn.** (2) merită măsurat
înainte de a fi respins — dar numai după ce se știe timpul real de transfer al celor 507 MB.

## Criterii de acceptare

- [ ] Suita completă locală scade sub **60 s**, cu aceleași 1194 de teste trecute.
- [ ] Cele cinci fișiere de mai sus trec pe corpusul mărginit — **inclusiv `test_pagination`**,
      care trebuie să vadă în continuare mai multe pagini.
- [ ] Randarea completă rulează în continuare undeva, pe un ritm declarat, și pică vizibil dacă
      se rupe.
- [ ] Fixtura rămâne **necondiționată**: nu se reintroduce „randează doar dacă lipsește".
- [ ] Măsurat înainte/după cu `--durations=25`, nu estimat.
