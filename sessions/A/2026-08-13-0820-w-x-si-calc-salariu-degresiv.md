# 2026-08-13 08:20 — cont A — lucrare W/X comisă, item 4 rezolvat, calculator salariu fix degresiv

## Context
Sesiune pornită cu „continua implementare", extinsă de proprietar la „hotărăște tu pentru toate,
cum e mai logic, eficient și armonios" — deleg autonom decizia de ordine și abordare pentru lista
`## Open` din `specs/STATE.md`, cu excepția celor patru itemi marcați explicit
„owner decision pending" (vezi mai jos, ce am lăsat neatins).

## Ce am făcut, în ordine, fiecare comis separat pe verde

1. **`11c9a45a`** — item W (patru feature-uri necomise, deja verzi): cascada Ollama local ca
   fallback automat (`providers/cascade.py` + `providers/ollama.py`), scraper cu randare JS
   pentru primării (`fetch._fetch_html_list_js`, crawl4ai), fix `_fallback_href` în
   `_GenericListParser`, `tools/scan_surse.py` (scan live pe cele 129 surse oficiale prin gardă).
   Verificat: 827 passed, 8 failed (cele cunoscute de la itemul X, nelegate), 8 xfailed.

2. **`8590537f`** — item X (`IZZ-0177`, cele 8 teste roșii permanent de la hartă). Am rulat
   testele, nu doar citit codul: `assert "markerMap" in js` verifica un identificator care nu
   există deloc în `harta-stiri.js`. Am citit codul REAL (`ensureCanvas`, `byCoordinate`,
   `host.replaceChildren()`) și am rescris `test_harta_interactions.py` pe identificatorii
   adevărați. `test_harta_playwright.py` + `test_harta_playwright_v2.py` — ȘTERSE, nu reparate:
   verificau text inline JS în `.github/workflows/visual.yml`, o premisă căzută de când
   verificarea reală de interacțiune s-a mutat în `tools/visual_check.py` (Playwright, scroll
   tactil real + hash de pixeli + numărare canvas), pe care același workflow îl cheamă deja.
   Acoperirea nu s-a pierdut, doar nu mai era duplicată greșit. Verificat: 829 passed, 0 failed,
   8 xfailed.

3. **Item 4 (`WS-0025`, `# nosemgrep` la `render.py:15-16`) — REZOLVAT prin măsurare, nu ghicit.**
   „local semgrep e stricat" era interpretat greșit — de fapt nu era instalat. `pip install
   semgrep`, apoi test direct: fișier probă cu ACELAȘI import fără comentariul de suprimare →
   1 constatare pe regula exactă `r/python.lang.security.use-defused-xml.use-defused-xml`;
   `render.py` (cu suprimarea completă) → 0 constatări. Suprimarea funcționează. Nimic de comis
   în cod — doar linia din `STATE.md` închisă.

4. **`5dc92ca7`** — item 2, calculatorul de salariu. Deducerea personală era `salariuMinim * 0.2`
   fix, indiferent de brut. Am CITIT legea (nu inventat): art. 77^1 Cod Fiscal (Legea 227/2015,
   modif. OG 16/2022) — 20% la salariul minim, scade 0,5pp la fiecare 50 lei peste minim, 0% peste
   minim+2.000 lei. Verificat din **două surse independente** (salariile.ro, lege5.ro — care
   citează direct alin. 3-4), consistente intern (20→0 pe exact 40 de trepte de 0,5pp = banda de
   2.000 lei / 50 lei declarată). Implementat în `calc-salariu.js`, text explicativ actualizat în
   `calculator.html` + `_calc_salariu.html` (inclusiv un „1.950 lei" greșit → plafonul real e
   2.000). **Verificat local, în browser** (nu doar în cod): la 5.000 lei brut → deducere 584 lei
   (era 865), la 7.000 (peste plafon) → deducere 0.
   **Neclarificat**: cifra „~2.699" din nota veche a lui `STATE.md` nu a putut fi reprodusă — la
   brut = salariul minim exact, formula corectă dă ACELAȘI rezultat ca varianta flat (2.616 lei),
   fiindcă rata de 20% nu depinde de metodă la acel punct. Fie sursa citată inițial folosea alt
   salariu minim de referință, fie altă metodologie. Nu am inventat o explicație fără sursă —
   las nota în `STATE.md` pentru proprietar, dacă știe sursa exactă a cifrei.

## Ce NU am atins — owner decision pending, marcat explicit în `STATE.md`
- **Item 1 (Cernavodă)** — clasificare AI pentru evenimente locale cu miză națională. Design scris
  și autorizat de proprietar, dar fișierul `handoff/to-B/2026-08-07-raza-nationala-si-ce-a-ramas.md`
  NU există în clona `izz` (probabil în workspace-ul separat) — nu l-am putut citi, deci nu am
  ghicit implementarea. Consumă și buget AI în producție — risc prea mare pentru o decizie automată
  fără designul la îndemână.
- **Item 0b (`hold_important`)** — poartă de aprobare pre-publicare, legat de AI Act art. 50. Plan
  scris, „awaiting owner go" explicit în `STATE.md`; nu l-am pornit.
- **Item 5** — poze pe carduri (licențiere CC-BY), harta `/surse/`, ghiduri interactive. Toate cer
  decizii de proprietar pe care nu le pot substitui cu o alegere „logică" — sunt alegeri de produs/
  drept de autor, nu bug-uri de reparat.
- **Item 3 (batching Model C)** — rămâne blocat: are nevoie de `stats["deferred"]` din rulări reale
  de GitHub Actions, iar `gh` nu e autentificat în acest mediu (`gh auth status` → not logged in).
  Nu am ghicit cifre.

## Verificări rulate
- `pytest tests/ -q` de trei ori pe parcurs — ultima: **829 passed, 8 xfailed, 0 failed** (7 min).
- Randare `--render-only`, verificat vizual în browser local (Chromium, prin unealta de preview)
  pagina `/instrumente/calculator-salariu/` la trei valori (minim, 5.000, 7.000).
- **Nu am rulat `tools/audit.sh`** (Lighthouse/pa11y) — schimbarea e text + logică JS, fără CSS/
  layout nou; judecată proprie că nu se justifică costul unui audit complet pentru asta. Semnalez
  decizia explicit, nu o ascund.

## Stare la final
`main` la `5dc92ca7`, tree curat în afară de acest jurnal. Nimic în lucru, nimic pe jumătate făcut.
`STATE.md` actualizat cu toate cele patru rezultate de mai sus.
