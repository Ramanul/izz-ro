# Cuplarea reală din `generator/` — măsurată, nu intuită

> **Dosar plătit o dată. NU re-cerceta.** Măsurătorile de aici au costat o sesiune; refacerea
> lor de la zero e exact risipa pe care `specs/atribuire-cercetare-si-plan.md` o documentează
> pentru alt subiect. Dacă ai o întrebare nouă despre structură, **pornește de aici** și
> măsoară doar ce lipsește.
>
> Măsurat 2026-09-02, pe `main` la `56cdec3`. Unealta care le poate reface: comenzile din §6.

## 1. Întrebarea de la care a pornit

Proprietarul, textual: *„cum ar trebui să restructurăm codul ca structurile să fie cât mai
independente una de alta, astfel încât când trebuie să modific ceva să modific cât mai puțin
— să nu trebuiască să modific o ramură care poartă 10 rămurele și 200 de fructe, doar ca să
modific un fruct?"*

Plus: *„să caut doar în zona necesară, să nu trebuiască să citesc tot codul, care oricum va
crește."*

## 2. Prima măsurătoare: graful de importuri

22 de module, 8.515 linii. Structura, după cine-pe-cine importă:

```
RĂDĂCINI (mulți depind de ele, ele de nimeni)
  config     400 linii · 0 funcții  · 9 module depind de el
  util       205 linii · 9 publice  · 9 module
  guard      511 linii · importă ZERO din generator/   ← singurul complet independent

TRUNCHI
  geo        789 · 5 module depind · importă 3
  localities 181 · 2 module

RAMURI GROASE (importă mult, nimeni nu depinde de interiorul lor)
  render    1784 · 59 funcții, doar 2 publice · importă 6
  fetch      899 · importă 3
  process    746 · importă 4

VÂRF   main 566 · importă 10, nimeni nu-l importă
DESPRINSE  agents (238) · local_sources (180) · photojudge (57)  ← fan-in 0, nu-s puncte de intrare
```

## 3. Metrica: nu mărimea, ci fan-in × frecvență

Intuiția „fișierul mare e problema" e **falsă**. Costul unei modificări nu e cât de mare e
fișierul atins, ci câte alte fișiere trebuie atinse ca urmare.

| modul | fan-in | schimbări/90z | **durere** |
|---|---|---|---|
| `config` | 9 | 6 | **54** |
| `util` | 9 | 2 | **18** |
| `geo` | 5 | 2 | **10** |
| `render` | 1 | 9 | **9** |
| `guard` | 3 | 0 | **0** |

**Concluzia contra-intuitivă:** `render.py` are 1784 de linii — de patru ori cât `config` —
dar expune **2 funcții publice** și îl importă **un singur** modul. E deja o cutie închisă.
`config.py` are 400 de linii și fan-in 9: fiecare atingere are rază de 9.

În metafora proprietarului: `render` e un **fruct mare** (greu de ținut în mână, dar îl tai
fără să miști pomul); `config` e **rădăcina** (mică, dar orice tai acolo se simte în coroană).

`guard` — 511 linii, zero importuri interne, zero schimbări în 90 de zile — e **modelul**.
Nu întâmplător e și codul cel mai bine testat din repo.

## 4. A doua măsurătoare: cuplarea pe care graful de importuri NU o vede

Prima analiză a ratat esențialul, și asta e partea cea mai importantă a dosarului.

Cine scrie și cine citește fiecare cheie din dicționarul de articol:

```
cheie            scrisă de              citită de
title            fetch, process         12 module
category         process, state         10
teaser           process, render         6
entities         process                 6
synthesis        process                 6
sources          process, select         5
```

**16 chei fac punte** între module (scrise de unul, citite de altul). `title` e citit de
practic tot `generator/`.

Deci afirmația „`render` are fan-in 1, e izolat" e **greșită**: `render` atinge 10 chei-punte.
Cuplarea trece prin date, nu prin `import`, iar niciun tool static de importuri n-o vede.

### Reformularea care schimbă prioritățile

> `data/articles.json` este cel mai mare API public al proiectului — 175 de chei, 12 consumatori
> — și nu e declarat nicăieri.

`render.py` are 2 funcții publice, documentate, testate. Dicționarul de articol are ~16 chei
publice, **zero** linii de definiție, **zero** gardă, **zero** versiune.

## 5. Vocabularul: connascence

Conceptul academic pentru exact asta (Meilir Page-Jones), cu formula:

> **Connascence = Strength × Degree / Locality**

Aplicat la `title`: **strength** mică (doar un acord asupra șirului `"title"`), **degree 12**
(atâtea module trebuie să fie de acord), **locality ~zero** (12 fișiere diferite).

Și e connascence **dinamică** — invizibilă la compile-time. Literatura spune explicit că forma
statică e preferabilă, fiindcă poate fi analizată din sursă. De-aia prima măsurătoare a ratat-o.

Surse: [Connascence (Wikipedia)](https://en.wikipedia.org/wiki/Connascence) ·
[thoughtbot](https://thoughtbot.com/blog/connascence-as-a-vocabulary-to-discuss-coupling) ·
[Khalil Stemmler](https://khalilstemmler.com/wiki/coupling-cohesion-connascence/)

## 6. Cum se refac măsurătorile

```bash
# graful de importuri + fan-in: ast.ImportFrom cu level>0, filtrat pe modulele din generator/
# frecvența:
for f in generator/*.py; do echo "$(git log --oneline --since='90 days ago' -- $f | wc -l) $f"; done | sort -rn
# cheile-punte: ast.Subscript cu ast.Constant str, separat Store (scriere) de Load (citire),
#   plus Call pe .get("cheie"); punte = scrisă de un modul ȘI citită de altul
```

Detectorul de chei e **euristic**: `a["title"]` pe un dict de config arată identic în AST.
Filtrul scris-de-unul-citit-de-altul reduce zgomotul, nu-l elimină. Cifrele de degree pot fi
supraestimate cu ~10-20%.

## 7. Ce e de făcut, în ordinea raportului câștig/risc

**Treapta 0 — plasa.** `tools/echivalenta.py` (`IZZ-0271`) amprentează `output/`: o
refactorizare se dovedește neutră comparând 42.887 de fișiere, nu citind 8.515 linii. **Deja
livrată.** Nefăcute încă: determinismul între două randări, și coverage (`pytest --cov`).

**Treapta 1 — gardă pe cheile-punte.** Un test care verifică că fiecare cheie e scrisă doar de
proprietarul ei (`title` doar din `fetch`/`process`). Transformă connascence dinamică în
statică. **Înaintea schemei** — garda măsoară, adnotarea doar descrie.

**Treapta 2 — schema.** `generator/schema.py` cu un `TypedDict` peste cele 16 chei. Doar
adnotare, zero runtime, adoptabil incremental. *Obiecție validă:* fără `mypy` configurat
(§4: type-check *neconfigurat*), e documentație, nu verificare — de-aia vine după gardă.

**Treapta 3 — nu acum.** Segregare de interfață pe date: `covers` primește `(title, category,
icon)`, nu tot articolul. Ar tăia degree-ul de la 12 la 3-4 per consumator, dar e rescriere
mare.

**Regula de aur pentru „caut doar în zona necesară":** un modul care nu importă nimic din
proiect se poate citi singur. `guard` e dovada.

## 8. Unde analiza asta poate greși

- **Contraexemplu la propria regulă:** `config.py` are **0 importuri interne** și e cel mai
  dureros modul. „Fan-out zero" identifică rădăcini, iar rădăcinile sunt fie foarte sănătoase
  (`guard`), fie cele mai scumpe (`config`). Criteriul nu e suficient singur.
- **Degree 12 pe `title` nu e neapărat rău.** E conceptul central al unui agregator de știri;
  un câmp de domeniu cu mulți consumatori poate fi coeziune, nu cuplare. Semnalul real de
  alarmă e că **două** module îl scriu — acolo se pot contrazice.
- **Schema nu prinde erori de conținut.** Fixul `Șiria`/`Siria` (`IZZ-0270`) ar fi durat exact
  la fel cu schema declarată. Structura apără forma, nu semantica.

## 9. Legătura cu regulile (aceeași problemă, alt strat)

Întrebarea *„vreau multe reguli fără să se încarce la fiecare cerere"* are același răspuns:
**progressive disclosure**, pe trei niveluri.

| Nivel | Ce | La noi |
|---|---|---|
| 1. Metadate | o linie per regulă, **mereu** încărcat | **lipsește** |
| 2. Instrucțiuni | fișierul complet, la declanșare | ✅ `.claude/reguli/` + hook `PostToolUse` |
| 3. Resurse | detaliu, la cerere | ✅ `specs/`, registru |

Costurile măsurate: `CLAUDE.md` **23.493 B la fiecare tură**; `.claude/reguli/` **3.390 B**,
doar pe calea atinsă. Practica publicată raportează ~94% reducere prin nivelul 1.

**Ce lipsește e un `.claude/reguli/INDEX.md`** — ~20 de linii, o linie per regulă cu
declanșatorul ei, ~1 KB permanent, care înlocuiește ~15 KB. Atunci poți avea 50 de reguli:
costul permanent devine indexul, nu regulile.
