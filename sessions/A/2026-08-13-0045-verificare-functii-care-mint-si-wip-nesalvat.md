# 2026-08-13 00:45 · cont A · verificarea „funcțiilor care mint" + WIP nesalvat în arbore

**Cerut de proprietar:** „caută în absolut toate sesiunile despre izz.ro ce trebuia implementat și
nu am implementat pentru website și de ce", apoi „reanalizează codul din GitHub, STATE.md, handoff
și orice altceva, refă analiza", apoi „verifică, analizează și rezolvă".
**Livrat:** verificarea, analiza corectată, și **zero reparații** — oprit deliberat, motivele mai
jos. Ultima instrucțiune a proprietarului: „tu oprește-te și scrie tot în STATE ca să facem data
viitoare, și în jurnal sau handoff".

---

## 0. Ce trebuie să știe următoarea sesiune, în trei rânduri

1. **Sunt patru funcționalități verzi, NECOMISE, în arbore** (Ollama fallback + scan_surse +
   scraper JS + fix href). Suita trece cu ele. Vezi §3. **Ăsta e lucrul cu cel mai mare risc.**
2. **Rula o a doua sesiune cont A în același arbore, simultan**, și comitea pe `main` în timp ce
   analizam. De-aia n-am comis nimic. Vezi §5.
3. Analiza pe care o ceruse proprietarul mai devreme **în aceeași conversație era greșită** în două
   feluri care contează. Vezi §2, ca să nu fie re-derivată.

---

## 1. Ce am verificat direct în cod (metoda: citit + rulat, nu presupus)

| # | Afirmație | Verdict | Dovada |
|---|---|---|---|
| 1 | `hold_important` nu blochează nimic | **CONFIRMAT** | `grep -rn "hold_important"` → 8 apariții; `main.py:298` îl bagă în `stats`, `main.py:359-360` doar `print`. Nimic nu porțează. |
| 2 | `guard.anomalie` e scris și nechemat | **INFIRMAT — e legat** | `fetch.py:248,506,637` + `moderation.py:138`. Confirmă `9f3e3ad2` din 12 aug. |
| 3 | `state.merge()` e cod mort | **CONFIRMAT, dar nu e bug** | definit `state.py:95`, unic apelant `tests/test_state.py:14`. Dedup-ul real e inline la `main.py:227-236`. |
| 4 | Calculatorul de salariu are 20% hardcodat | **CONFIRMAT** | `static/calc-salariu.js`: `var deducere = Math.round(salariuMinim * 0.2);` |
| 5 | Suita de teste | **827 passed, 8 failed, 8 xfailed, 420s** | `python -m pytest tests/ -q` |
| 6 | Cele 8 picate = `IZZ-0177` | **CONFIRMAT** | asserțiunea e `assert "markerMap" in js`; numele nu există în fișierul livrat. |

Comenzile, verbatim, ca să fie re-rulabile:

```bash
grep -rn "hold_important" --include=*.py --include=*.yaml --include=*.md .
grep -rn "anomalie" --include=*.py .
grep -rn "\.merge(\|def merge" --include=*.py .
python -m pytest tests/ -q
```

Ieșirea care contează, verbatim:

```
8 failed, 827 passed, 8 xfailed in 420.12s (0:07:00)
>       assert "markerMap" in js
E       assert 'markerMap' in '(() => {\n  "use strict";\n\n  const DATA_URL = "./data/map.json";...'
```

**Cifrele astea înlocuiesc „676 passed, 2 xfailed, 27 errors" din capul lui `STATE.md`** — erorile
din `test_sitemap_editorial.py` au dispărut, iar suita a crescut la 843 colectate.

---

## 2. Unde greșise analiza precedentă (din aceeași conversație) — NU o re-deriva

**(a) N-a văzut WIP-ul nesalvat.** A produs un inventar de ~16 „mișcări blocate" fără să se uite
o dată la `git status`. Lucrul cu cel mai mare risc din tot repo-ul — muncă verde, necomisă, care
moare dacă pică sesiunea — n-a apărut deloc în listă. Precedentul e documentat: 2 august, cont B,
jurnal de 198 de linii pierdut integral fiindcă n-a fost pushat.

**(b) A numărat decizii de proprietar drept eșecuri de implementare.** Reactivarea Rovinari,
mărimea tap-target-elor pe hartă, decuplarea permalinkului de categorie, fotografiile pe carduri —
toate escaladate **corect** la proprietar. Un agent care le-ar fi „rezolvat" singur ar fi produs o
greșeală, nu o livrare. Formularea „0 neimplementate din greșeală" era și ea falsă: `hold_important`
e implementat-dar-mincinos, ceea ce e mai rău decât lipsă.

**(c) Detaliu de acuratețe:** a raportat `guard.anomalie` ca reparat pe 12 aug — corect. Dar a
prezentat lista de blocaje ca și cum ar fi fost toate descoperite atunci, când majoritatea erau
deja consemnate în `STATE.md` cu motiv.

---

## 3. WIP-ul din arbore — inventar complet (§W din STATE.md)

`git status --short` la 00:42:

```
 M generator/config.py
 M generator/fetch.py
 M generator/process.py
 M tests/test_fetch_scraper.py
?? generator/providers/cascade.py
?? generator/providers/ollama.py
?? tools/scan_surse.py
```

(`static/harta-stiri/harta-stiri.js` era și el modificat la începutul sesiunii — **a fost comis de
cealaltă sesiune în timp ce lucram**, vezi §5.)

### 3.1 Fallback automat pe Ollama local
`config.py`: `AI_FALLBACK_OLLAMA = os.getenv("AI_FALLBACK_OLLAMA", "1") == "1"` — **implicit ON**.
`process.get_provider()` rescris: construiește o listă `[primary, OllamaProvider()]`, filtrează pe
`available()`, și dacă rămân două întoarce `CascadeProvider`. Cloud-ul e **mereu** încercat întâi;
Ollama intră doar când cloud-ul eșuează propriu-zis.

**De ce contează:** azi un 429 (cotă Gemini epuizată) sau o cheie lipsă amână articolul complet —
regula „No mangled output" din §7. Un model local, gratuit, pornit pe mașină, ar putea totuși să-i
scrie titlul.

**De ce e sigur:** în CI Ollama nu rulează → `available()` cade rapid pe conexiune refuzată →
cascada devine providerul cloud singur → comportament neschimbat. Argumentat în docstring.

### 3.2 `tools/scan_surse.py` — cea mai valoroasă piesă
Scanează feedurile **VII** ale celor 129 de surse oficiale prin garda de ingestie și raportează ce
ar fi respins. Nu ingerează, nu scrie în `data/`.

Docstring-ul conține argumentul care lipsea din sesiunea de pe 12 aug: **scanul peste
`data/articles.json` e parțial CIRCULAR.** Articolele ingerate DUPĂ ce garda a început să
funcționeze au fost deja filtrate la fetch, deci „0 respingeri" pentru ele nu dovedește că sursa e
curată — dovedește că garda și-a făcut treaba. Cele 8 de la Rovinari se vedeau acolo doar fiindcă
fuseseră ingerate ÎNAINTE de gardă.

Cost declarat: 129 de cereri HTTP = exact cât face o rulare normală de pipeline.

```bash
python tools/scan_surse.py                # doar surse oficiale (pl_/cj_/pr_)
python tools/scan_surse.py --toate        # inclusiv presa
python tools/scan_surse.py --json out.json
```

**Asta răspunde la întrebarea rămasă deschisă în HANDOFF:** „54,3% din catalog scanat efectiv,
restul e NECUNOSCUT, nu curat — cea mai mare suprafață necunoscută rămasă."

### 3.3 `fetch._fetch_html_list_js` — randare în Chromium headless
Pentru primăriile care își construiesc lista de anunțuri în JavaScript (Next.js/React), unde
`urllib` primește doar bundle-ul gol. **Măsurat 2026-08-12 pe `primariatm.ro/noutati`:** urllib →
**0** linkuri utile; crawl4ai cu 3s de așteptare → **12** anunțuri reale, cu titlu/link/dată.

`crawl4ai` e **dinadins neinclus în `requirements.txt`** — ar împinge un download de ~200MB în
fiecare build CI (§17, bugetul de build). Fără pachet, sursa eșuează curat: eroare de sursă, nu
crash de pipeline. Instalare locală: `pip install crawl4ai && crawl4ai-setup`.

### 3.4 Fix `_GenericListParser._fallback_href`
Href-ul nu se prindea niciodată când titlul e imbricat în ACEEAȘI ancoră (un singur `<a>` care
învăluie tot cardul), fiindcă condiția existentă cere `title_at` deja setat înainte de `<a>`. Acum
primul href din item se reține ca rezervă și se folosește la închiderea itemului.

---

## 4. A treia instanță din clasa „mecanism care minte" (§X din STATE.md)

Proprietarul a cerut să găsesc ce nu s-a implementat. Tiparul care iese, a treia oară:

- `hold_important` — steag care promite blocare și nu blochează (**încă deschis**);
- `guard.anomalie` — funcție scrisă și nechemată din 9 până în 12 aug (**reparat**, `9f3e3ad2`);
- **cele 8 teste roșii de hartă** — par să păzească harta, se uită după `markerMap`, nume care nu
  există în fișierul livrat (**deschis**).

Un test roșu permanent nu păzește nimic: dacă munca la hartă strică ceva acum, nimic nu poate
semnala, fiindcă alarma sună deja. Nivel **N3** — intern, cititorul nu vede nimic azi. Dar e fix
mecanismul care a lăsat defacement-ul Cajvana două zile pe site.

Reparat ieftin: ori se șterg testele, ori se rescriu pe identificatorii reali din fișier.

---

## 5. De ce n-am comis nimic — cursa pe `main`

Am pornit analiza pe o stare și starea s-a mutat sub mine:

| moment | HEAD | observație |
|---|---|---|
| început sesiune | `5aec8608` | `harta-stiri.js` apărea ca modificat necomis |
| mijlocul analizei | `783f5482` | trei commit-uri noi; `harta-stiri.js` **dispăruse** din modificări |

`git log`: `a4b03b17` la 00:32:24, `783f5482` la 00:36:32, iar `date` dădea 00:40:03 — deci
cealaltă sesiune comitea **acum trei minute și jumătate**, live.

Am descoperit-o abia când un `git diff` pe `harta-stiri.js` a întors gol la a doua rulare, după ce
`--stat` raportase 27 de linii schimbate. **Ăsta e L7 pe viu** (stare partajată, citită o dată și
presupusă stabilă), iar HANDOFF avertizează explicit: „DOUĂ SESIUNI A pot rula simultan".

Decizii luate, cu motivul:

- **N-am comis WIP-ul** — §14 „nu face curse pe `main`". În plus, nu e munca mea; dacă cealaltă
  sesiune e mid-write pe `cascade.py`, un commit ar îngheța o stare intermediară.
- **N-am reparat `hold_important`** — e parcat explicit pe „go" de la proprietar în `STATE.md` 0b,
  și atinge `main.py` cât timp altcineva lucrează în arbore.
- **N-am atins `state.merge()`** — refactorizare oportunistă, §5.6.
- **N-am rulat `scan_surse.py`** — 129 de cereri HTTP către primării, sub sesiune concurentă, fără
  ca proprietarul să fi ales între variante.

Testele au rulat 7 minute peste un arbore care se schimba, deci rezultatul lor **nu e atribuibil
unui commit anume**. E totuși informativ: cele 8 picate sunt confirmat `IZZ-0177`, deci WIP-ul e
verde.

---

## 6. Ce urmează, în ordine, când arborele e liber

1. **Salvează WIP-ul** (§3). Verde, no-op în CI, cel mai mare risc dacă se pierde. Ideal în trei
   commit-uri separate: cascada Ollama · scraperul JS + fixul de href · `scan_surse.py`.
2. **Rulează `python tools/scan_surse.py`** și pune cifra în `STATE.md`. Închide cea mai mare
   suprafață necunoscută rămasă (câte din 129 de primării mai sunt compromise).
3. **`hold_important`, felia 1** — fă steagul să porțeze cu adevărat. **Azi e pe `false`, deci
   comportamentul public nu se schimbă**; doar încetează să mintă. E singurul mecanism din repo care
   ar putea susține „human review" pentru scutirea de la AI Act art. 50. **Cere „go" de la
   proprietar** — a fost parcat acolo dinadins. NU automatiza review-ul însuși.
4. Cele 8 teste roșii de hartă (§4) — șterse sau rescrise.

**Restul, dacă vrei:** calculatorul de salariu (§2 din STATE — se citește articolul 77 din Codul
Fiscal, nu se inventează), batching Model C (se citește `stats["deferred"]` pe 2-3 rulări reale
întâi).

---

## 7. Întrebări deschise, doar proprietarul poate răspunde

- **Ce se face întâi:** `hold_important` (steagul să nu mai mintă) sau `scan_surse.py` (câte
  primării mai sunt sparte)? — pusă, **fără răspuns la ora scrierii**.
- **Ce e cealaltă sesiune care lucrează la hartă** și e liber arborele? — pusă, fără răspuns.
- Rămân deschise, neatinse de sesiunea asta: reactivarea Rovinari (`IZZ-0175`), drop-ul de
  `stash@{0}` (`IZZ-0172`), tap-target-ele hărții (`IZZ-0176`), fotografiile pe carduri,
  ghidurile interactive, E1/E4 din dosarul de atribuire.

---

## 8. Starea la final

- **Comis de mine:** doar `specs/STATE.md` (§W, §X, §Y) și jurnalul ăsta.
- **Necomis, intact, neatins de mine:** cele 7 fișiere din §3.
- **Suita:** 827 passed / 8 failed / 8 xfailed — cele 8 sunt `IZZ-0177`, preexistente.
- **`main`:** ultimul commit al celeilalte sesiuni, `783f5482`, 00:36:32.
