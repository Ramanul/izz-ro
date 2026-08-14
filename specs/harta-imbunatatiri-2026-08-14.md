# Harta știrilor — plan de execuție pentru o sesiune ieftină (Sonnet / Haiku)

**Scris de:** sesiune Opus, cont A, 14 aug 2026
**Pentru:** o sesiune Claude Code cu model ieftin, care execută feliile de mai jos
**Sursa:** audit extern „Manus AI" (14 aug 2026, commit `8e282c3`) + **reverificare independentă
pe cod și pe live** făcută de sesiunea care a scris fișierul ăsta.

> **Citește DOAR fișierul ăsta plus fișierele numite explicit în felia pe care o execuți.**
> Nu redeschide auditul, nu reaudita pagina, nu explora repo-ul „ca să înțelegi contextul".
> Tot ce trebuie verificat a fost deja verificat; cifrele de mai jos sunt măsurate, nu estimate.
> Dacă un fapt de mai jos nu se potrivește cu ce vezi în cod, **oprește-te și raportează** —
> înseamnă că altcineva a modificat între timp, nu că trebuie să improvizezi.

---

## 0. Înainte de orice — trei comenzi obligatorii

```bash
cd "C:/claude desktop/izz" && git pull --ff-only && git log --oneline -1
```

Motiv: pe 14 aug 2026, ora scrierii, copia locală era **7 commit-uri în urmă** față de
`origin/main`, iar `static/harta-stiri/index.html` de pe `origin` diferă de cel local (căi
absolute vs relative). Botul de conținut comite la ~2h, deci `main` local e aproape mereu vechi.

```bash
cd "C:/claude desktop/izz" && python tools/registru.py find harta
```

Motiv: registrul conține deja decizii pe hartă. **Citește-le înainte să atingi ceva** — una din
ele blochează explicit felia 4 (vezi §2).

```bash
cd "C:/claude desktop/izz" && python -m pytest tests/ -q 2>&1 | tail -3
```

Motiv: ai nevoie de o linie de bază verde ÎNAINTE să modifici. Dacă e roșu de la început,
raportează și oprește-te — nu repara teste care nu țin de harta.

---

## 1. Fapte verificate — NU le reverifica

Toate au fost confirmate fie prin citirea codului, fie prin cerere HTTP către `https://izz.ro`
pe 14 aug 2026. Coloana „cum" spune exact ce dovadă există.

| # | Fapt | Cum a fost stabilit |
|---|---|---|
| F1 | `renderList()` produce `li > a + span`; niciun element nu primește clasă | citit `static/harta-stiri/harta-stiri.js:336-354` |
| F2 | CSS-ul stilizează `.news-item`, `.news-meta`, `.news-title`, `.news-place`, `.badge` — **clase pe care nimeni nu le mai emite**; nu există nicio regulă pentru `#news-list li`, `li a` sau `li span` | citit `static/harta-stiri/harta-stiri.css:29` |
| F3 | Consecința lui F1+F2: `a` și `span` rămân `display:inline` → titlul și metadatele se lipesc (`NăvodariNAVODARI`, `ConstanțaCONSTANTA`) | dedus din F1+F2, confirmat de capturile auditorului `initial-390.png` / `initial-1440.png` |
| F4 | Defectul **e în producție**, nu doar local: JS-ul live conține `li.append(a, meta)`, CSS-ul live conține `.news-item` și **nu** conține `#news-list li` | `curl https://izz.ro/static/harta-stiri/harta-stiri.{js,css}` → 200, verificat pe conținut |
| F5 | Containerul `#news-list` este un **`<div>`**, iar `renderList()` îi bagă `<li>` înăuntru → imbricare HTML invalidă, zero semantică de listă pentru cititoarele de ecran | `curl https://izz.ro/static/harta-stiri/` → `<div id="news-list" class="news-list">`; același lucru în `origin/main:static/harta-stiri/index.html:55` |
| F6 | `panel-count` afișează `${items.length} știri`, adică „120 știri", deși `filtered()` poate întoarce mult mai multe | citit `harta-stiri.js:352-353` |
| F7 | Datasetul curent: **497 articole** (428 `local`, 69 `judetean`), **141** cu `x/y` (28,4%), **145** cu SIRUTA (29,2%), **38** județe reprezentate | `python` peste `static/harta-stiri/data/map.json` |
| F8 | În `buildMap()`, `matchesSearch` se calculează **fără să refere `county`** — e un boolean global recalculat identic la fiecare iterație a buclei pe județe | citit `harta-stiri.js:173-178` |
| F9 | Click pe un marker de localitate scrie localitatea în `state.search` și în `#map-search` — filtrarea pe localitate e implementată prin câmpul de căutare full-text | citit `harta-stiri.js:308-318` |
| F10 | `filtered()` caută în `title`, `locality`, `county` **și `source`**, deși eticheta câmpului spune „Caută județ / localitate…" | citit `harta-stiri.js:55-64` + `index.html:39-40` |
| F11 | Hit-testul de click se face **doar pe bulinele de numărare**, nu pe poligonul județului — deși obiectele `Path2D` sunt deja construite și păstrate în `state.paths` | citit `harta-stiri.js:167-188, 302-334` |
| F12 | Nu există stare în URL: nivel, căutare și județ trăiesc doar în memorie | citit `harta-stiri.js` integral, zero `history.pushState` / `location.search` |
| F13 | `/static/harta-stiri/*` are `Cache-Control: public, max-age=300, must-revalidate` → **un fix ajunge la utilizator în ≤5 minute, fără cache-bust** | header-ul răspunsului live; regula e scrisă în `generator/render.py:1211-1218` |
| F14 | `tools/visual_check.py` face captura „mobilă" **după** bucla de resize care se termină la 1024px → `harta-mobile-regression.png` are **1024×1186**, identic cu cea de desktop | citit `tools/visual_check.py:40-54`; măsurat pe PNG-urile din arhiva auditului |
| F15 | Cele 6 teste din `tests/test_harta_interactions.py` sunt asserții pe **text din fișier**, nu pe DOM randat. Nu pot prinde niciunul din F1-F12 | citit `tests/test_harta_interactions.py` |

**Ce a greșit auditul extern** (ca să nu te ia pe urma lui):
`phase2_code_audit.md` §8 zice că stilurile moarte sunt doar „cod mort" și că „UX nu se strică".
Fals — sunt exact cauza lui F3, iar auditul principal spune corect că e P0. Când cele două se
contrazic, **auditul principal are dreptate**. Auditul extern **nu a găsit** F5, F8 și F9.

---

## 2. Ce e interzis fără GO explicit de la proprietar

| Interdicție | De ce |
|---|---|
| Mărirea zonei de tap / hit-area pe poligon **ca decizie proprie** | `IZZ-0176` e marcat `blocat`: „Soluția … e decizie de proprietar, netranșată". Felia 4 e scrisă, dar **nu o executa** fără „go". |
| Tab / filtru „Regional" pe hartă | `IZZ-0179` = `respins` de proprietar: „nu merită efortul suplimentar". |
| Orice atingere a `generator/` , `data/articles.json`, `moderation.yaml` | Feliile astea sunt 100% în `static/harta-stiri/` + `tools/visual_check.py`. Dacă simți nevoia să ieși de acolo, te-ai rătăcit. |
| Merge în `main` de la o sesiune de fundal | `CLAUDE.md §14b`: deschizi draft PR și te oprești. Dacă lucrezi în sesiune interactivă cu proprietarul de față, el decide. |
| Refactorizări „de curățenie" în afara feliei | `CLAUDE.md §5.6` — diff minim. |

---

## 3. Protocol de verificare (se aplică la FIECARE felie)

Trei stări, cu cuvintele exacte. Nu le amesteca în raport:

- **„reparat în cod"** — ai scris diff-ul. Nu ai voie să spui mai mult.
- **„verificat local"** — ai rulat serverul local, ai condus pagina în browser real și ai văzut
  simptomul dispărut.
- **„confirmat pe live"** — ai cerut `https://izz.ro/...` după deploy și ai citat răspunsul.

### Server local pentru harta (nu e nevoie de pipeline)

Harta e statică și autonomă. Nu rula `python -m generator.main` — nu-ți trebuie și costă timp.

```bash
cd "C:/claude desktop/izz" && python -m http.server 8765 --directory static/harta-stiri
```

Pagina e la `http://localhost:8765/`. `./data/map.json` se rezolvă corect de acolo.
Linkurile către articole (`../../categorie/slug/`) vor da 404 local — **e normal și nu e bug**.

### Verificare DOM cu Playwright (instalat, verificat 14 aug 2026)

Scriptul de mai jos e unealta ta principală. Salvează-l în
`C:/claude desktop/izz/tools/harta_dom_check.py` la felia 1 și extinde-l la fiecare felie.
Rulează-l cu serverul local pornit în paralel.

```python
#!/usr/bin/env python
"""Verificare DOM randat pentru harta stirilor. Ruleaza cu serverul local pornit:
   python -m http.server 8765 --directory static/harta-stiri
Asserteaza pe STRUCTURA VIZIBILA (id-uri + taguri), nu pe clase CSS -- clasele s-au dovedit
de doua ori identificatori morti in repo-ul asta (vezi IZZ-0177, IZZ-0182)."""
import os, sys
from playwright.sync_api import sync_playwright

BASE = os.getenv("MAP_URL", "http://localhost:8765/")
fails = []

def check(cond, label):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}")
    if not cond:
        fails.append(label)

def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(args=["--no-sandbox"])
        p = br.new_page(viewport={"width": 1280, "height": 900})
        p.goto(BASE, wait_until="domcontentloaded")
        p.wait_for_selector("#news-list li a", timeout=15000)

        # --- FELIA 1: lista de rezultate ---
        box = p.evaluate("""() => {
          const li = document.querySelector('#news-list li');
          const a = li.querySelector('a'), s = li.querySelector('span');
          const ra = a.getBoundingClientRect(), rs = s.getBoundingClientRect();
          return {
            tag: document.querySelector('#news-list').tagName,
            aDisplay: getComputedStyle(a).display,
            sDisplay: getComputedStyle(s).display,
            sameLine: Math.abs(ra.top - rs.top) < 2,
            gap: rs.top - ra.bottom,
            count: document.querySelector('#panel-count').textContent.trim(),
          };
        }""")
        print("  ", box)
        check(box["tag"] == "UL", f"#news-list este <ul> (e {box['tag']})")
        check(box["aDisplay"] == "block", f"titlul e bloc ({box['aDisplay']})")
        check(box["sDisplay"] == "block", f"meta e bloc ({box['sDisplay']})")
        check(not box["sameLine"], "titlul si meta NU sunt pe acelasi rand")
        check(box["gap"] >= 3, f"exista spatiu vertical intre titlu si meta ({box['gap']:.1f}px)")
        check(" din " in box["count"], f"panel-count arata totalul ('{box['count']}')")

        br.close()
    if fails:
        print("\nFAIL:"); [print(" -", f) for f in fails]; return 1
    print("\nOK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Captura mobilă corectă

`tools/visual_check.py` **nu** produce o captură mobilă reală (F14). Până repari asta în felia 3,
fă capturile mobile cu un script separat care face `screenshot()` **înainte** de orice resize.

---

## 4. Feliile

Ordinea e obligatorie. **O felie cap-coadă, verificată, comisă — apoi următoarea.**
Nu începe felia N+1 până felia N nu are commit verde.

---

### FELIA 1 — Lista de rezultate (P0)

**Scop.** Titlul și metadatele fiecărui rezultat devin blocuri separate, lizibile; containerul
devine listă reală; numărul afișat spune adevărul despre plafonul de 120.

**Fișiere atinse:** `static/harta-stiri/index.html`, `static/harta-stiri/harta-stiri.css`,
`static/harta-stiri/harta-stiri.js`, `tools/harta_dom_check.py` (nou).

**Ce faci, exact:**

1. În `index.html`, linia ~55: schimbă containerul din `<div>` în `<ul>`, și placeholder-ul din
   `<p>` în `<li>` (un `<p>` direct în `<ul>` e invalid):
   ```html
   <ul id="news-list" class="news-list">
     <li class="loading">Se încarcă…</li>
   </ul>
   ```
   Închide cu `</ul>`, nu `</div>`.

2. În `harta-stiri.css`, **adaugă** (nu înlocui blocul existent `.news-list{...}`):
   ```css
   #news-list{list-style:none;margin:0;padding:0}
   #news-list li{padding:.85rem 1rem;border-bottom:1px solid var(--border)}
   #news-list li:last-child{border-bottom:0}
   #news-list li:hover{background:var(--surface-2)}
   #news-list li a{display:block;font-size:.91rem;line-height:1.35;font-weight:600;text-decoration:none;color:var(--text)}
   #news-list li a:hover,#news-list li a:focus-visible{text-decoration:underline}
   #news-list li span{display:block;margin-top:.35rem;font-size:.72rem;line-height:1.4;color:var(--muted)}
   ```

3. **Șterge clasele moarte** din CSS — dar întâi dovedește că sunt moarte:
   ```bash
   cd "C:/claude desktop/izz" && grep -rn "news-item\|news-meta\|news-title\|news-place\|\.badge" static/ templates/ generator/ tools/ tests/ | grep -v "harta-stiri.css"
   ```
   Ce **nu** apare nicăieri altundeva, se șterge din `harta-stiri.css`. Ce apare, **rămâne**.
   Dacă grep-ul întoarce ceva neașteptat, spune-o în raport.

4. În `harta-stiri.js`, funcția `renderList()` (linia ~336): calculează totalul o singură dată și
   scrie-l în `#panel-count`:
   ```js
   function renderList() {
     const list = $("#news-list");
     if (!list) return;
     const all = filtered();
     const items = all.slice(0, 120);
     list.replaceChildren();
     for (const item of items) {
       // ... corpul buclei ramane NESCHIMBAT ...
     }
     const count = $("#panel-count");
     if (count) {
       count.textContent = all.length > items.length
         ? `${items.length} din ${all.length} știri`
         : `${items.length} știri`;
     }
   }
   ```

**Criterii de acceptare (toate, măsurate):**
- `python tools/harta_dom_check.py` → `OK`, cu toate cele 6 verificări verzi.
- `python -m pytest tests/ -q` → același număr de teste trecute ca la linia de bază, 0 eșecuri.
- `node --check static/harta-stiri/harta-stiri.js` → fără erori (asta rulează și CI-ul, în
  `.github/workflows/harta-data.yml:42`).
- Captură la 1280px și la 390px (cu scriptul separat de la §3) în care **se vede** că titlul și
  metadatele sunt pe rânduri diferite.

**Commit:** `fix(map): result list had no styles at all -- title and meta ran together`

---

### FELIA 2 — Două bug-uri de logică în filtrare (P1)

**Scop.** Repari două defecte de corectitudine pe care auditul extern **nu** le-a găsit.
Zero schimbare de design, zero fișier nou.

**Fișier atins:** `static/harta-stiri/harta-stiri.js`.

**Bug A — `matchesSearch` nu se uită la județ (F8).**
În `buildMap()`, liniile ~173-178, ai:
```js
const query = norm(state.search);
const matchesSearch = !query || state.visible.some((item) =>
  norm(`${item.county} ${item.locality}`).includes(query));
```
`matchesSearch` nu conține `county` din bucla curentă — e o constantă, recalculată de 42 de ori.
Efect: la o căutare care se potrivește doar pe titlu (ex. un cuvânt din titlu care nu e nici
județ, nici localitate), `matchesSearch` devine `false` **pentru toate județele**, deci harta se
estompează integral, inclusiv județele care CHIAR au rezultate.

Corect:
```js
const matchesSearch = !query || state.visible.some((item) =>
  item.county === county && norm(`${item.county} ${item.locality}`).includes(query));
```
Scoate și `const query = norm(state.search);` din buclă, deasupra ei — se recalcula degeaba.

**Bug B — click pe localitate scrie în câmpul de căutare (F9).**
În `onCanvasClick()`, liniile ~308-318, selectarea unui marker de localitate face
`state.search = locality` + `search.value = locality`. Două consecințe reale:
(a) șterge ce scrisese utilizatorul în câmp; (b) fiindcă `filtered()` caută și în `title` și
`source` (F10), un click pe „Aiud" aduce și articole din alte județe al căror **titlu** conține
„Aiud".

Corect: adaugă un câmp propriu de stare și filtrează pe el, fără să atingi căutarea.
```js
// in obiectul `state`, langa selectedCounty:
selectedLocality: null,

// in filtered(), dupa filtrul de judet:
if (state.selectedLocality) {
  const want = norm(state.selectedLocality);
  if (norm(item.locality) !== want) return false;
}

// in onCanvasClick(), ramura zoomCounty:
state.selectedLocality = marker.localities[0] || marker.locality;
state.visible = filtered();
renderList();
updateStats();
```
Nu uita: `resetSelection()` și handler-ul de schimbare de nivel din `bindControls()` trebuie să
pună `state.selectedLocality = null` — altfel rămâne o localitate lipită de o stare resetată.

**Criterii de acceptare:**
- Extinde `tools/harta_dom_check.py` cu două verificări noi, rulate în browser real:
  1. tastezi în `#map-search` un cuvânt care apare doar în titluri (alege-l citind `map.json`),
     apoi verifici că **nu toate** județele cu rezultate sunt estompate. Verificare practicabilă:
     `#panel-count` arată > 0 rezultate ȘI canvasul nu e uniform — cel mai simplu e să asertezi
     că `state`-ul intern nu mai e accesibil, deci **verifică vizual cu o captură** și descrie
     ce vezi. Dacă nu poți asserta programatic, spune-o explicit în raport, nu inventa un „ok".
  2. click pe un marker de localitate (după ce ai intrat pe un județ) **nu** modifică
     `document.querySelector('#map-search').value`.
- `node --check` + `pytest` verzi.

**Commit:** `fix(map): per-county search dimming and locality click no longer hijacks the search box`

---

### FELIA 3 — Captura „mobilă" care nu e mobilă (P2, unealta noastră)

**Scop.** `tools/visual_check.py` produce o captură de 1024px pe care o numește „mobile" (F14).
Orice verificare mobilă făcută cu ea de acum înainte e falsă.

**Fișier atins:** `tools/visual_check.py`.

**Ce faci:** în `main()`, liniile 53-54, mută `screenshot()` **înaintea** apelului `check_map()`,
fiindcă `check_map()` conține bucla de resize `[1100,900,700,390,1280,1024]` care lasă pagina la
1024px:
```python
mob = br.new_page(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True)
goto(mob, BASE+'/static/harta-stiri/', 'mobile', 'domcontentloaded')
mob.wait_for_selector('#news-list li a', timeout=15000)
mob.screenshot(path=f'{SHOT_DIR}/harta-mobile-regression.png', full_page=True)  # INAINTE de resize
check_map(mob, True)
```
Adaugă un comentariu de o linie care spune **de ce** ordinea contează — repo-ul are convenția
asta și te scutește de a treia repetare a greșelii.

**Criteriu de acceptare:** rulezi `python tools/visual_check.py` cu `BASE_URL=https://izz.ro` și
verifici cu `PIL` sau `System.Drawing` că `harta-mobile-regression.png` are **lățimea 390**,
nu 1024. Citează dimensiunea măsurată în raport.

**Commit:** `fix(tools): the "mobile" regression screenshot was captured at 1024px`

---

### FELIA 4 — Click pe poligonul județului (P1) — **NU EXECUTA FĂRĂ „GO"**

`IZZ-0176` e `blocat`, cu motivul: 24 din 42 de județe au zona de apăsat sub minimul de 44px, iar
soluția e **decizie de proprietar, netranșată**. Felia e scrisă ca să fie gata de executat în
momentul în care primești „go", nu ca s-o execuți acum.

**Ce ar fi de făcut, tehnic:** obiectele `Path2D` sunt deja în `state.paths` (F11), deci nu e
nevoie de bibliotecă GIS și nici de recalcularea geometriei. În `onCanvasClick()`, ramura fără
zoom, după ce `closestHit` pe buline nu găsește nimic:
```js
// Canvasul are deja transformarea aplicata din buildMap(), deci isPointInPath
// primeste coordonate in spatiul viewBox-ului, exact ca `p`.
const ctx = canvas.getContext("2d");
const hit = state.paths.find((e) => e.count > 0 && ctx.isPointInPath(e.path, p.x, p.y));
```
Atenție la o capcană reală: `isPointInPath` se raportează la transformarea **curentă** a
contextului. `buildMap()` o setează la final și nu o resetează, dar dacă altcineva desenează
între timp, testul cade silențios. Verifică-l cu un click programatic pe interiorul unui județ
mare (ex. Timiș) și pe unul mic, și **citează coordonatele folosite**.

**Criteriu de acceptare:** click în interiorul poligonului, departe de bulină, produce **aceeași**
stare ca și click-ul pe bulină (același județ selectat, aceeași listă).

---

### FELIA 5 — Selectarea județului cu tastatura (P0 accesibilitate)

**Scop.** Canvasul are `role="img"` și e nefocusabil (F11 + `index.html:47`). Un utilizator fără
mouse **nu poate selecta niciun județ**. Nu înlocui canvasul; adaugă un echivalent HTML.

**Fișiere atinse:** `static/harta-stiri/index.html`, `harta-stiri.css`, `harta-stiri.js`.

**Ce faci:**
1. Sub hartă, un `<div id="county-picker" class="county-picker" role="group" aria-label="Alege
   județul">`, populat din JS cu câte un `<button type="button" data-county="CLUJ">` pentru
   fiecare județ **care are rezultate vizibile**, cu text `Cluj · 53`.
2. Butonul apelează **exact aceeași** funcție de tranziție ca `onCanvasClick()`. Ca să nu ai două
   căi divergente, extrage întâi din `onCanvasClick()` o funcție `selectCounty(county)` și
   cheam-o din amândouă. Asta e singurul refactor permis în felia asta.
3. Butonul județului selectat primește `aria-pressed="true"`.
4. `#map-stats` are deja `aria-live="polite"` (`index.html:27`) — nu adăuga altă regiune live,
   ar produce anunțuri duble.

**Criterii de acceptare:**
- Cu `Tab` ajungi la butoanele de județ; cu `Enter` selectezi; lista se filtrează.
- Playwright: `page.keyboard.press("Tab")` până la primul `#county-picker button`, apoi `Enter`,
  apoi asertezi că `#panel-count` s-a schimbat.
- `#county-picker` se actualizează la schimbarea nivelului și la căutare.

**Commit:** `feat(map): keyboard-operable county selector alongside the canvas`

---

### FELIA 6 — Starea în URL (P1)

**Scop.** `?judet=CLUJ&nivel=local&q=...` — link partajabil, refresh care nu pierde contextul,
back/forward funcțional (F12).

**Fișier atins:** `static/harta-stiri/harta-stiri.js`.

**Ce faci:** o singură funcție `applyState({level, county, locality, query}, {push})` care
actualizează `state`, apoi cheamă `buildMap(); renderList(); updateStats();` și, dacă `push`,
`history.pushState`. Toate cele patru locuri care mută starea azi (`onCanvasClick`,
`bindControls` × 2, `resetSelection`) trec prin ea. `popstate` reaplică starea **fără** push.
Citirea inițială se face în `init()`, înainte de primul `buildMap()`.

**Criteriu de acceptare:** deschizi direct `?judet=CLUJ&nivel=local`, vezi starea corectă fără
niciun click; apeși Back și revii la starea anterioară.

**Commit:** `feat(map): serialize map state into the URL`

---

### FELIA 7 — Ce face căutarea, de fapt (P1) — **CERE DECIZIA PROPRIETARULUI ÎNTÂI**

Eticheta zice „Caută județ / localitate…", codul caută și în titlu și în sursă (F10). Nu poți
repara asta fără să știi care e intenția. Trei variante, **nu alege singur**:

| Variantă | Ce se schimbă | Cost |
|---|---|---|
| A. Strict geografic | `filtered()` scoate `title` și `source` din haystack | 1 linie |
| B. Full-text, etichetat onest | placeholder devine „Caută în titluri, surse sau locuri" | 1 linie |
| C. Două controale | „Loc" + „Cuvinte-cheie" separate | ~40 de linii, HTML + CSS + JS |

Recomandarea sesiunii care a scris fișierul: **A**, fiindcă pagina se numește „Harta știrilor" și
site-ul are deja căutare globală pentru text. Dar e decizia lui Alexandru, nu a ta.

---

## 5. Ce raportezi la finalul fiecărei felii

Antet obligatoriu, în ordinea asta:

```
Stare: felia X din 7
Verdict: <o propoziție, fără jargon>
Ai de făcut: NU  /  DA → <ce anume>
Încredere: n/10 — <ce o ține sub 10>
```

Apoi, sub antet: ce ai schimbat, ieșirea reală a comenzilor (nu parafrazată), și **care din cele
trei stări** ai atins — „reparat în cod" / „verificat local" / „confirmat pe live".

Dacă n-ai putut verifica ceva, spune care rol a rămas neverificat și de ce. Un „merge" nesusținut
de o ieșire de comandă e mai rău decât un „n-am reușit să verific".

## 6. Registrul de decizii — o linie per felie

Feliile care produc commit sunt preluate automat de `tools/registru.py sync`. Ce **nu** produce
commit — o felie amânată, o variantă respinsă, o măsurătoare care s-a dovedit falsă — primește un
rând manual, în aceeași tură:

```bash
cd "C:/claude desktop/izz" && python tools/registru.py add --stare <implementat|respins|blocat|masurat-fals> --subiect harta --titlu "..." --motiv "..." --dovada "..."
```

`--motiv` e obligatoriu pe `respins`, `abandonat`, `anulat`, `masurat-fals`.

## 7. Ce NU e o problemă, deși pare

Ca să nu pierzi timp „reparând" lucruri corecte:

- **Canvas în loc de bibliotecă GIS** — decizie deliberată, corectă. Nu propune Leaflet.
- **Agregarea pe județ în loc de pini exacți** — decizie editorială: doar 28% din articole au
  coordonate (F7). Harta refuză deliberat să inventeze precizie. E un avantaj, nu un defect.
- **Un singur `<canvas>` reutilizat, `setTransform` resetat, `ResizeObserver` care ignoră
  schimbările de înălțime** — sunt fix-uri pentru bug-uri reale de dedublare pe mobil, cu
  comentarii explicative în cod. Nu le „simplifica".
- **Linkurile 404 la articole pe serverul local** — normal, calea e `../../categorie/slug/`.
- **`Cache-Control: max-age=300`** — deliberat (F13). Nu adăuga cache-busting; nu e nevoie.
