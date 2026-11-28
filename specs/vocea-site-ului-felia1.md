# SPEC — Felia 1: vocea site-ului (2026-11-28)

Sursa cerinței: `Documents\izz-lectura-claude\lista_implementare_izz_20261030.md`, Felia 1; mandat Alexandru în sesiune, 28.11.2026 („Da, Felia 1”). Cost estimat: mic.

**Goal:** titlurile scrise de site nu mai folosesc violență ca metaforă sau intensificator; știrile despre moarte/violență au un semn „Subiect greu” și o ieșire ușoară; site-ul spune limpede ce este (mașină, cu limite, care nu simte); există un inventar scris al funcțiilor care pot răni.

**Premise măsurate** (28.11.2026, `data/articles.json` de pe `origin/main`, 26.239 articole):
- 941 titluri (3,6%) sunt despre moarte/violență după un lexic larg; 91 conțin verbe violente, majoritatea literale („a ucis”, „incendiul a distrus”) — NU se interzic.
- Doar ~9 titluri au metaforă/intensificator real (ex. „a spulberat-o pe Lens”, „incendiu devastator”). Problema de volum e subiectul greu, nu metafora.
- Pagina de articol arată fotografie reală/ilustrație locală, nu artă generată; „oprește arta” nu se aplică.

**Împărțire în 3 PR (consultare 28.11.2026):**
- PR 1: `generator/ton.py`, `tools/audit_ton.py`, `tests/test_ton.py`, `specs/inventar-ranire-2026-11.md`. Măsurat: 472 titluri (1,8%) primesc semnul; semnul se calculează doar din titlu, cu negația scoasă.
- PR 2: `content/legal/method.md` „Ce este izz.ro", regula de prompt din `generator/process.py`, contorul de metafore.
- PR 3: semnul și ieșirea ușoară în `_card.html`, `article.html`, `styles.css`; opțional oprirea butoanelor de distribuire.

**Scope — fișiere (total):**
1. `generator/ton.py` — nou — `titlu_cu_violenta()` (metafore + intensificatori, doar pentru titlurile site-ului) și `subiect_greu()` (lexic LITERAL: moarte, omor, viol, sinucidere, victime, masacru).
2. `generator/process.py` — prompturile de titlu (B, C, lot): regulă „fără violență ca metaforă și fără intensificatori; verbul literal la victime reale”. `PROMPT_VERSION` NU se schimbă, nu se reprocesează nimic.
3. `generator/render.py` — marchează `a.subiect_greu` la randare (nestocat) + contor în log/QA al titlurilor cu violență metaforică.
4. `templates/_card.html`, `templates/article.html`, `static/styles.css` — semn „Subiect greu” pe card; pe articol o notă scurtă + legătură „Treci la alte știri din {rubrică}”; fără popup, fără blocare, fără ascundere.
5. `content/legal/method.md` — secțiune „Ce este izz.ro”: program care adună și rezumă automat, fără simțire, poate greși; fără promisiuni noi, fără nume de cărți.
6. `specs/inventar-ranire-2026-11.md` — nou — funcțiile existente care pot răni, cu decizie per rând.
7. `tests/test_ton.py` — nou; teste în `tests/` pentru randare.

**Nu se atinge:** logica Model C de atribuire, `moderation.yaml`, workflows, push (partea de trimitere e în Worker), selecția paginii principale.

**Verificare:** `python -m pytest tests/ -q`, `python -m ruff check .`, `python -m generator.main --render-only`, `bash tools/audit.sh` înainte/după (§13), apoi Chromium pe un articol greu și unul obișnuit.

**Branch:** `oc/felia1-vocea` din `origin/main`; PR.
