# Întrebarea 7, măsurată: câte pagini din `output/` n-au `og:image` funcțional

**Data:** 2026-10-03 · **Commit de referință:** `093cb47` (+ fixul de mai jos)
**Unealta:** `tools/og_image_audit.py` · **Testele:** `tests/test_og_image_audit.py` (12)
**Dovada brută:** `notes/og-image-audit-2026-10-03.json`

> **Cerut:** întrebarea 7 din `notes/30-intrebari-imagini-2026-10-03.md` transformată în
> măsurătoare concretă — script care numără paginile fără `og:image` valid, raport cu numere,
> fix propus în 2-3 rânduri. **Livrat:** toate trei, plus garda de regresie.

## Spec (3-8 rânduri, cum cere `CONTRIBUTING.md`)

- **Scop:** răspunsul la „câte pagini ajung fără o previzualizare socială funcțională".
- **Intrare:** un `output/` randat (`python -m generator.main --render-only`).
- **Ieșire:** numere pe tipuri de defect + tipuri de imagine, exemple de pagini vinovate,
  raport JSON opțional (`--json`), cod de ieșire 1 la defecte blocante (0 altfel).
- **Criterii de acceptare:** (a) prinde un URL relativ, o origine străină și un fișier lipsă;
  (b) nu dă fals-pozitiv pe paginile bune (11.113 la prima rulare); (c) e determinist și fără
  rețea; (d) are test cu răspuns cunoscut, construit deliberat.
- **În afara scopului:** dacă imaginea e *bună* vizual sau dacă CDN-ul o servește (aici se
  verifică doar ce e pe disc, după randare).

## Ce măsoară, pe fiecare pagină HTML din `output/`

1. există `<meta property="og:image">` și are conținut;
2. URL-ul e absolut **și** pe originea site-ului (relativ = card gol la WhatsApp/Facebook);
3. fișierul la care trimite chiar există în `output/` (calea, fără `?v=`);
4. `og:image:width/height` se potrivesc cu dimensiunile reale (citite din header PNG/JPEG,
   fără Pillow);
5. `twitter:image` nu contrazice `og:image` și nu există două valori `og:image` diferite.

Verificarea e statică, fără browser și fără rețea, pe modelul `tools/greutate.py` (dimensiunea 5):
altfel spus, e un **plafon comparabil între randări**, nu o predicție despre ce vede crawlerul live.

## Numerele (randare completă, 11.114 pagini HTML)

| | Înainte de fix | După fix |
|---|---|---|
| Pagini cu `og:image` funcțional | **11.113 / 11.114 (99,991%)** | **11.114 / 11.114 (100%)** |
| Defecte blocante | **1** (`fara-tag`) | **0** |
| Cod de ieșire | 1 | 0 |

**Defectul, singurul din 11.114 pagini:** `static/harta-stiri/index.html` — pagina hărții.
E singura pagină publică care nu se randează prin `templates/base.html` (are HTML propriu),
deci singura care nu moștenea `og:image`. Linkul hărții pe WhatsApp/Facebook/LinkedIn ieșea cu
card gol.

**Ce a ieșit curat din prima** (avertismente: 0 din 4 categorii):
- **0** URL-uri relative, **0** pe altă origine;
- **0** fișiere lipsă — toate cele **1.216 URL-uri distincte** trimit la fișiere existente;
- **0** dimensiuni declarate greșit (toate 1200x630, inclusiv `static/og-image.png`);
- **0** `twitter:image` divergente, **0** pagini cu două `og:image`.

**De unde vine imaginea fiecărei pagini** (nu e un defect, e designul documentat în
`render.py` — dar acum e măsurat):

| Tip | Pagini | Pondere | Câte fișiere |
|---|---|---|---|
| Coperta proprie a articolului (`cover.jpg`) | 1.200 | 10,8% | 1.200 |
| Coperta categoriei (`og/<cat>.jpg`) | 8.251 | 74,2% | **15** |
| Generic (`static/og-image.png`) | 1.663 | 15,0% | **1** |

Fereastra `OG_COVER_MAX_ARTICLES = 1200` acoperă 1.200 din 10.518 articole (11,4%); restul
stau pe coperta categoriei — **74% din pagini împart 15 imagini**. Consecința de știut: un
articol vechi redistribuit arată identic cu alte mii. Nu e o regresie, e plafonul de fișiere
al Workers Free (`specs/cloudflare-free-2026-09.md`), care preferă 15 fișiere în loc de 10.000.

## Fixul (3 rânduri, în `static/harta-stiri/index.html`)

```html
<meta property="og:image" content="https://izz.ro/static/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
```

Fișierul e scris de mână (nu-l generează niciun tool — verificat), deci fixul îi aparține.
`og:title`/`og:description` nu sunt necesare: platformele cad pe `<title>` și pe
`<meta name="description">`, care există deja. Cele trei linii sunt suficiente pentru ca harta
să aibă card social, iar dimensiunile sunt exact cele ale fișierului de refugiu (testat).

## Cum se rulează

```bash
python -m generator.main --render-only          # output/ din starea comisă
python tools/og_image_audit.py                  # raport; exit 1 dacă găsește defecte
python tools/og_image_audit.py --json raport.json
python -m pytest tests/test_og_image_audit.py -q   # 12 passed
```

Garda de regresie (`test_output_randat_nu_are_pagina_fara_og_image_functional`) rulează pe
eșantionul din fixtura `output_randat` (200 de articole, IZZ-0415), care randează toate
tipurile de pagină în ~3 secunde — deci prinde o pagină nouă fără `og:image` fără costul unei
randări complete. Nu e încă în CI ca pas separat: `Asset census` din `deploy-worker.yml` e locul
natural, dar e o felie separată, nu o strec în asta.

## Ce NU rezolvă (limite, ca să nu se citească „100%" ca „totul e în regulă")

- **Nu validează vizual.** O copertă tipografică generată e „funcțională" pentru crawler; dacă
  e și *bună* e întrebarea 3 din listă, nu asta.
- **Nu verifică HTTP live.** Fișierul există pe disc după randare; că CDN-ul chiar îl servește
  e verificat de `smoke_live.py`/`verify_release.py`, nu aici.
- **Cifrele depind de fereastra de coperți.** Numărul „pe coperta de categorie" se schimbă cu
  `OG_COVER_MAX_ARTICLES`, nu cu calitatea: raportul trebuie re-citit după ce se schimbă pragul.
- **Nu cântărește imaginea.** Cardul funcționează și dacă poza are 900 KB; costul în octeți e
  măsurat de `tools/greutate.py` (dimensiunea 5), nu aici.
- **Numără doar fișiere `.html`.** O pagină servită cu altă extensie nu ar intra în scanare —
  azi nu există niciuna (verificat: toate paginile publice sunt `index.html`).
- **Găsit, dar nu reparat în felia asta:** `og:image:alt` / `twitter:image:alt` **nu există
  nicăieri** în site (0 apariții în `templates/` și `static/`) — asta e întrebarea 24, nu 7, și
  merită tratată ca atare, pe toate paginile deodată.
