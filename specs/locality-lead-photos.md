# SPEC — lead photos de LOCALITATE pentru stirile locale

**Goal:** articolele din `local` / `zonal` care provin de la o primarie primesc ca imagine
principala fotografia REALA a localitatii (Wikidata P18, auto-gazduita), in locul copertei
generate cu pictograma — de la 0 fotografii reale azi la ~67% din primariile GOLD.

## Verified premises (masurate pe repo + retea, 2026-08-01)

- `data/leadphotos.json` are **1684 intrari, 0 hit-uri** — pipeline-ul de fotografii reale
  nu produce nimic. Verificat: `python -c "import json;d=json.load(open('data/leadphotos.json'));
  print(len([k for k,v in d.items() if not v.get('miss')]))"` -> `0`.
- Cauza: `tools/fetch_leadphotos.py::lead_for_article` cauta P18 pe **entitatile-persoana** din
  articol si cere simultan *landscape >= 1.2* SI *PD/CC0*. Portretul unui primar e vertical si
  aproape intotdeauna CC-BY -> intersectie vida.
- Ruta localitate, masurata pe cele 120 de primarii GOLD (`scratchpad/probe4.py`):
  | etapa | acoperire |
  |---|---|
  | rezolvate la localitatea corecta (judet potrivit obligatoriu) | 120/120 (100%) |
  | au P18 | 108/120 (90%) |
  | P18 utilizabil (>=1200px latime, landscape, licenta libera) | **81/120 (67%)** |
  | din care ar trece filtrul PD/CC0 de azi | 11/120 (9%) |
- Clasele Wikidata corecte sunt `Q659103` (comuna, 2860), `Q16858213` (oras, 216),
  `Q640364` (municipiu, 102) — 3178 in total, exact structura administrativa a Romaniei.
  `P31/P279* Q486972` da timeout 504 pe endpoint; `P31/P279* Q15284` **rateaza toate orasele**.
- Potrivirea de judet e OBLIGATORIE: fara ea, 12 din 120 se rezolva la omonime din alt judet
  (Zarnesti/Buzau in loc de Zarnesti/Brasov) -> fotografie gresita pe stire locala.
- Linia de credit pe pagina de articol **exista deja**: `templates/article.html:37`
  (`figcaption.art-credit` cu autor, link Commons, licenta), stilizata la `static/styles.css:490`.
  Se alimenteaza din `a["lead_credit"]`, setat in `generator/render.py:420`. Nu se rescrie nimic.
- Atribuirea NU e obligatorie pe carduri: CC 4.0 §3(a)(2) si CC 3.0 §4(c) permit indeplinirea
  obligatiei printr-un link catre o resursa care contine informatiile — cardul linkuieste
  articolul, care poarta creditul. Deci §7 ramane neatins: cardurile nu primesc niciun element nou.
- `data/articles.json`: 456 articole `local`+`zonal`, din care 168 de la surse `pl_*`
  (57 primarii distincte). Slug-ul sursei (`pl_<judet>_<localitate>`) e determinist si
  reversibil — e cheia de rezolvare, nu entitatile din text.

## Decizii de proprietar (confirmate 2026-08-01)

1. Se accepta **PD/CC0 + CC-BY + CC-BY-SA**. Fara credit ars in pixeli.
2. Creditul apare pe **pagina de articol** (deja implementat). Cardurile raman curate.
3. Fotografia e **ilustratie de localitate**, nu document al evenimentului — legenda trebuie
   sa spuna asta explicit.

## Scope — fisiere autorizate

1. `generator/localities.py` — **creare**. Pur, testabil offline, zero retea:
   - `parse_source_slug("pl_vrancea_municipiul_focsani") -> ("VRANCEA", "Focsani")`
     (prefixele `MUNICIPIU(L)` / `ORAS(UL)` / `COMUNA` se elimina pe cuvant intreg —
     acelasi bug pe care `local_sources._ORAS_RE` il trateaza deja corect; `ORAS X` fara `-UL`
     e forma majoritara in CSV).
   - `match(judet, nume, dataset) -> record | None` — potrivire pe nume normalizat
     (fara diacritice) SI judet. **Fara fallback pe alt judet**: niciun candidat in judetul
     corect -> `None`.
   - `usable(info) -> bool` — `width >= 1200` AND `width >= height * 1.2` AND licenta in
     lista libera (PD/CC0/CC-BY/CC-BY-SA/Copyrighted free use). GPL, "fair use", necunoscut -> False.
2. `data/localities.json` — **creare** (comis). Dataset static: `{qid, label, judet, img, pop}`
   pentru cele ~3178 de UAT-uri. Generat de (3), citit de (1). Fara retea la build.
3. `tools/fetch_localities.py` — **creare**. Construieste (2) din Wikidata prin SPARQL
   (XML, nu JSON: raspunsul JSON de ~2 MB vine trunchiat intermitent prin proxy, parse error
   determinist). Se ruleaza rar, manual, nu in `build.yml`.
4. `tools/fetch_leadphotos.py` — **modificare**:
   - ruta noua `lead_for_locality(a)`, incercata **inaintea** rutei pe entitati, doar pentru
     articolele `local`/`zonal` cu `source` care incepe cu `pl_`;
   - poarta de licenta: `is_public_domain` ramane neatinsa pentru ruta pe entitati; ruta
     localitate foloseste `localities.usable` (accepta CC-BY/BY-SA);
   - latime minima 1200 px pe ambele rute (azi lipseste: 450x338 ar trece de raportul landscape);
   - intrarea scrisa in `data/leadphotos.json` primeste `kind: "locality"` + `artist`,
     `license`, `page` — campurile pe care `figcaption.art-credit` le consuma deja.
5. `templates/article.html` — **modificare minima**: legenda devine
   `Ilustratie: <Localitate>. Foto: <autor> · <Wikimedia Commons> · <licenta>` **doar** cand
   `lead_credit.kind == "locality"`; ruta pe entitati isi pastreaza textul actual.
6. `tests/test_localities.py` — **creare**. Cazuri obligatorii:
   - `ORAS TEIUS` / `MUNICIPIU BACAU` / `COMUNA HEMEIUS` -> nume corect extras;
   - Zarnesti-Brasov NU se potriveste cu Zarnesti-Buzau (regresia de judet);
   - `usable`: 450x338 PD -> False (prea mica); 2592x3243 CC-BY-SA -> False (portret);
     2560x1920 GPL -> False (licenta); 3840x2160 CC BY-SA 4.0 -> True;
   - articol `sport` sau sursa non-`pl_` -> ruta localitate nu se declanseaza.

Nu se atinge: `generator/cluster.py`, logica de sinteza/atribuire (§10), `_card.html`,
`generator/covers.py`, `generator/htmlart.py`, `.github/workflows/`.

## Acceptance criteria

- [x] `python -m pytest tests/ -q` — **226 verzi** (CLAUDE.md §4 spunea 38; suita crescuse
      demult, iar dupa merge-ul cu `main` numarul real e cel de aici). 48 dintre ele sunt noi.
- [ ] `python tools/fetch_localities.py` produce `data/localities.json` cu >= 3000 intrari.
- [ ] `python tools/fetch_leadphotos.py` pe starea reala produce **>= 25 hit-uri** de tip
      `locality` (prag prudent fata de cele 67% masurate, pentru ca doar 57 de primarii
      distincte apar in `articles.json` curent).
- [ ] `python -m generator.main --render-only` — exit 0, sit construit.
- [ ] Verificare in ROL DE UTILIZATOR (§16): pe pagina construita, un articol local cu
      fotografie afiseaza imaginea reala SI legenda cu autor + licenta + link Commons;
      cardul aceluiasi articol afiseaza fotografia FARA element de credit si cu `Sursă`
      neschimbat.
- [ ] `frontend-auditor` (tools/audit.sh): Lighthouse Perf/A11y/BP/SEO si pa11y raportate
      inainte/dupa. Prag: A11y ramane 100, pa11y 0 erori, Perf nu scade sub 85.
- [ ] `editorial-guard`: confirma ca formula de atribuire (§7) e neschimbata pe carduri/hero.

## Riscuri asumate

- Fotografiile sunt ilustratii generice ale localitatii (Predeal -> muntele Postavaru,
  Slanic Moldova -> cazinoul). Mitigare: cuvantul "Ilustratie:" in legenda. Daca la review
  arata inselator langa titluri de tip "Consiliul Local se reuneste", se poate restrange
  ulterior la un subset (panorame/centru civic) — decizie separata, nu in acest slice.
- CC-BY-SA cere ca imaginea decupata sa fie ea insasi BY-SA. Nu afecteaza restul site-ului.
  Confirmat ca pozitie CC pentru colectii; merita confirmare de avocat IP daca miza creste.
- Wikidata poate returna 429/504. Toate apelurile au retry cu backoff; esec -> articolul
  pastreaza coperta generata (fail-safe, §7 "no mangled output").

**Branch:** `claude/scraping-romanian-public-data-u63sqz`.
