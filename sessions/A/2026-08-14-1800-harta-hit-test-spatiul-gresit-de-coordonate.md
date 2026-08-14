# 2026-08-14 · cont A · Harta: hit-testul lucra în spațiul greșit de coordonate

Continuarea sesiunii întrerupte de plafon (ultimul lucru vizibil în transcript: „15 din 15 verde
pe desktop. Acum partea de Android" → editare `harta_dom_check.py` → usage limit).

## Starea la preluare

Branch `fix/harta-lista-rezultate`, trei fișiere modificate necomise:
`static/harta-stiri/harta-stiri.js`, `static/harta-stiri/index.html`, `tools/harta_dom_check.py`.
Feliile 1 și 3 făcute de un subagent Haiku, feliile 2, 7, 4 de sesiunea principală. Codul pentru
verificarea Android era **scris dar nerulat** — exact bucata pe care a tăiat-o plafonul.

## Fundătura de la început: serverul servit din directorul greșit

`index.html` folosește căi absolute (`/static/harta-stiri/harta-stiri.css`), deci un server pornit
din `static/harta-stiri/` întoarce 200 pe HTML și 404 pe CSS și JS — pagina se încarcă goală, iar
garda pică pe timeout fără să spună de ce. Corect e din rădăcina repo-ului:

```
python -m http.server 8766 --directory "C:/claude desktop/izz"
MAP_URL="http://localhost:8766/static/harta-stiri/" python tools/harta_dom_check.py
```

Atenție, `Bash` cu `run_in_background` **nu moștenește `cd`-ul din comanda precedentă** — prima
pornire a aterizat în `static/`. Verifică întotdeauna cu:
`curl -s http://localhost:8766/ | grep -o '<a href="[^"]*"'`.

## Bug-ul: `isPointInPath` citește punctul în pixeli de canvas, nu în unități viewBox

Garda pica pe o singură verificare: la 390px, doar **7 din 36** de atingeri selectau un județ
(prag 12). Tentația era să cobor pragul. În loc de asta, trei măsurători, în ordine:

**(1) Cad atingerile pe mare sau pe uscat?** Script în scratchpad care, pentru fiecare punct de
grilă, citește culoarea pixelului de sub deget înainte de tap și calculează rata condiționată:

```
DESKTOP 1280: pe uscat 47/64 (73%) · selectează 30/47 = 64%
MOBIL   390 : pe uscat 29/36 (81%) · selectează  5/29 = 17%
```

Aceleași proporții de grilă, aceeași geografie, rate de 4× diferite → nu e eșantionarea, e codul.
Și 64% pe desktop e la fel de prost, doar că trecea pragul.

**(2) Ajunge evenimentul la `click`?** Instrumentat canvasul cu contoare pe
`pointerdown`/`pointerup`/`pointercancel`/`click`. Rezultat: **36/36 click pe ambele viewport-uri**,
zero `pointercancel`. Deci garda tap-vs-drag e nevinovată, iar `touch-action: pan-y` nu înghite
nimic. Hit-testul chiar nu găsește județul.

**(3) În ce spațiu citește `isPointInPath` punctul?** Test izolat, canvas 100×100, `setTransform`
cu scale 0,1, `Path2D` cu `rect(0,0,500,500)`:

```
{user_inside_250: False, user_inside_450: False, device_inside_25: True, outside_600: False}
```

Verdict: **CTM se aplică CĂII, nu PUNCTULUI.** `x`/`y` se citesc în pixeli de canvas.

`onCanvasClick` pasa la `countyAtPoint` punctul întors de `pointForEvent`, care e în spațiul
viewBox (0…1000). De ce s-a văzut doar pe telefon: pe desktop canvasul are ~820px iar viewBox-ul
~1000 de unități — atât de apropiate încât punctul cădea lângă județul vizat dar tot pe uscat,
deci clickul „mergea" de cele mai multe ori. La 390px canvasul are 364px lățime, iar un punct de
900 cade complet în afara pânzei și nu se potrivește cu nimic.

**Fix** (`822acba8`): funcție separată `devicePointForEvent`, folosită doar pentru poligoane.
Bulinele rămân pe `pointForEvent` — markerii se construiesc cu `ctx.arc(p.x, p.y, ...)` sub
transformare, deci sunt genuin în spațiul viewBox și acolo comparația era corectă. Două spații,
două funcții, ca să nu se mai amestece.

```
mobil 390px   7/36 -> 28/36
desktop 1280 33/64 -> 49/64
```

Garda: 16/16 verde. `pytest tests/ -q`: **872 passed, 8 xfailed** în 524s.

## A doua reparație: garda de mobil retesta desktopul

Verificarea „derularea peste hartă nu selectează un județ" folosea `page.mouse.down/move/up`.
Pe o pagină cu `has_touch=True` asta produce tot evenimente de mouse — adică testul rula
desktopul și raporta verde pentru telefon. Playwright expune doar `touchscreen.tap`, fără swipe,
deci gestul se trimite prin CDP (`Input.dispatchTouchEvent`, touchStart/touchMove/touchEnd) —
helper `swipe_touch()` în `tools/harta_dom_check.py`.

**Control pozitiv rulat** (fără el, verdele n-ar însemna nimic): tap în centrul canvasului
selectează = True, swipe din exact același punct selectează = False. Testul discriminează.

## Analiza GPT primită la mijlocul sesiunii (`harta gpt.pdf`, 44 de pagini)

PDF din imagini, zero text extractibil; randat cu PyMuPDF la 105 dpi în scratchpad și citit ca
imagini. `pypdf` și `pymupdf` au fost instalate în mediul local pentru asta.

Teza: „problema principală nu e un bug singular, e că implementarea a ajuns la limita
arhitecturii alese"; recomandă rescrierea stratului de randare pe **D3 + SVG** (verdict 9,5/10),
cu MapLibre ca opțiune pe 1-2 ani.

Ce ține: simptomele sunt descrise corect, dar trei din ele erau deja reparate (lista fără stiluri,
căutarea neclară, butonul de întoarcere). **Un punct nou și valid:** `marker.localities[0]` alege
tăcut prima localitate dintr-un grup suprapus.

Ce nu ține: dovada empirică principală a tezei e că mobilul e cel mai slab punct — „tap targets
prea mici", „nu rezolvi prin cercuri mai mari". Cauza reală, măsurată azi, era conversia de
coordonate de mai sus, șase linii. Analiza a lucrat pe cod citit, fără să ruleze nimic; de-asta
descrie corect ce se vede și greșit de ce se vede. Notele „9,5/10" sunt impresii, nu măsurători.

Unde chiar are dreptate: SVG face accesibilitatea aproape gratuită (fiecare județ = element DOM
real, cu focus, `aria-label`, tastatură), iar asta cade exact peste felia 5. Merită cântărit ca
proiect separat, **nu ca reparație** — azi a arătat că problemele erau bug-uri, nu limite.

## Decizia proprietarului și ce s-a lansat

Întrebat între (a) felia 5 pe arhitectura actuală, (b) doar felia 5, (c) rescriere SVG/D3, a
răspuns „rezolvă cu haiku al tău deocamdată" — deci varianta (a), executată de subagent, fără
rescriere.

Înainte de asta se propusese execuția prin `@mistralai` (workflow activ, vezi
`SESSION-2026-08-14.md`). **Motivul pentru care nu e potrivit aici, verificat în
`.github/workflows/mistral.yml`:** runner-ul instalează doar CLI-ul `mistral-vibe`, nu
`requirements.txt` și nu Playwright — deci `tools/harta_dom_check.py` **nu poate rula acolo**.
Plus `--max-turns 30` și `timeout-minutes: 30`. Executorul ar lucra pe orb exact pe felia unde
garda vizuală e singura care prinde regresiile. Pentru task-uri fără verificare de browser rămâne
bun.

Subagent Haiku lansat cu trei bucăți: felia 5 (spec în `specs/harta-imbunatatiri-2026-08-14.md`,
linia ~371), bug-ul localităților suprapuse, și toleranțele de atins — `hitDistance(extra=5)` și
`EDGE_TOLERANCE=10` sunt în unități viewBox, deci pe telefon ajung la ~1,8px și ~3,6px în loc de
~4px și ~8px. Cerut explicit: verificări noi în gardă care POT să cadă, `skip()` pentru ce nu se
poate testa, cifre în raport.

## Registru

`IZZ-0193` — hit-testul pe județ cădea pe mobil. Atenție: prima oară am scris `IZZ-0186` în
comentariul din cod, ID inventat din memorie — era deja luat (consimțământ Clarity v2→v3).
Registrul era la 192 de rânduri. **Verifică ID-ul cu `registru.py` înainte să-l scrii în cod.**
`python tools/registru.py find <subiect>` crapă cu `UnicodeEncodeError` pe cp1252 când rândul are
diacritice în `motiv` — citirea directă a TSV-ului cu `csv.DictReader` și stdout pe UTF-8 merge.

## Ce a livrat subagentul Haiku — și de ce raportul lui nu se putea lua pe cuvânt

Raport primit: „3 din 3, 20/20 verde, **încredere 10/10**". Codul chiar era bun (`selectCounty()`
extras corect și chemat din ambele căi, butoane reale cu `aria-pressed`). **Verificările erau
defecte, iar sub ele stăteau două bug-uri reale.**

**Test 1, „de la tastatură", nu folosea tastatura.** `p.keyboard.press("Tab")`, apoi citea
`document.activeElement` într-o variabilă **pe care n-o aserta niciodată** — comentariul propriu:
„Nu e strict necesara pe focus". Selecția o făcea cu `p.click()`. Dacă butoanele ar fi fost
`<div>`-uri nefocusabile, testul rămânea verde — adică exact defectul pentru care există felia.

**Test 2 nu putea cădea:** `check(count_after != "497 știri", ...)`, dar starea inițială e
`"120 din 497 știri"`. Condiția e adevărată orice s-ar întâmpla.

Rescrise ca să treacă prin tastatură cap-coadă (Tab până când focusul **chiar** aterizează în
`#county-picker`, aserție pe asta, `Enter` nu click, comparație cu valoarea reală dinainte).
Au picat imediat două lucruri:

1. **`38 → 1 buton` după selecție.** `updateCountyPicker()` construia din `state.visible`, care
   e deja filtrat pe selecție. Cine navighează din tastatură rămânea închis pe primul județ ales.
   Aceeași fundătură ca „harta blocată pe județ" din 12 aug, pe alt drum.
2. **Focusul se pierdea la fiecare `Enter`** — butoanele sunt distruse și recreate la fiecare
   redesenare, deci elementul focusat înceta să existe și focusul cădea pe `<body>`.

**Ironia care merită reținută: testul vechi trecea DIN CAUZA bug-ului 1.** Verifica `aria-pressed`
pe *primul* buton din picker; prăbușirea la un singur buton făcea ca acel buton să fie chiar cel
selectat. Un test verde care se sprijină pe defect.

Fix (`ecf37469`): `filtered({ ignorePlace: true })` pentru sursa butoanelor, plus reținerea și
refacerea focusului peste reconstruire. Măsurat: `38 → 38`, focus păstrat.

Toleranța de atins are acum măsurătoare adevărată (`edge_tolerance_px`): se pleacă de la conturul
unui județ și se merge în afară pas cu pas — **7px CSS la 390px**, față de pragul de 3px pe care
vechea toleranță în unități viewBox (~1,8px) nu-l putea atinge.

**Localități suprapuse: raportat NEVERIFICAT, nu verde.** Markerii se grupează pe cheie de
coordonate EXACTĂ, iar în cele 497 de știri sunt **0 puncte partajate** — codul nu se poate
declanșa. Garda spune asta explicit la fiecare rulare, cu ce trebuie făcut când apar grupuri.

## Felia 6 — starea în adresă (`f6240168`)

Toate schimbările de stare trec acum printr-un singur `applyState()`. Două decizii:

- **`zoomCounty` a încetat să fie stare independentă** — e derivat din `county + level` (fără zoom
  la nivel Județean, decizie proprietar 13 aug). Ținut separat, se desincroniza de selecția care
  îl producea.
- **Tastarea folosește `replaceState`**, nu `pushState`. Altfel o căutare de zece caractere lăsa
  zece intrări în istoric și Back trebuia apăsat de zece ori ca să ieși din ea.

Garda verifică **ambele sensuri** — stare→adresă și adresă→stare — fiindcă oricare poate fi
corect izolat: un link care se scrie dar nu se citește arată bine în bara de adrese și aterizează
pe hartă nefiltrată la cine îl deschide. Plus aserție că rezultatele aparțin județului CERUT: o
listă filtrată-dar-greșită are forma bună și conținutul greșit. (Prima versiune trecea pe „31 de
știri" fără să verifice județul — și Alba, și Cluj au fix 31, deci coincidența ar fi ascuns-o.)

## Starea la final

**Toate cele 7 felii din spec sunt gata.** Pe `fix/harta-lista-rezultate`, urcat pe remote:
`822acba8` (hit-test), `ecf37469` (blocarea selectorului), `f6240168` (starea în adresă), plus
`b3601a82` de la Haiku. Garda: **26 verzi, 1 neverificat**. `pytest`: 872 passed, 8 xfailed.

Preview Cloudflare: `https://fix-harta-lista-rezultate.izz-ro.pages.dev/static/harta-stiri/`
(calea pe live e `/static/harta-stiri/` — `/harta-stiri/` dă 404). Verificat că build-ul de
preview servește codul nou căutând identificatori în JS-ul livrat (`devicePointForEvent`,
`ignorePlace`, `applyState`) — nu presupus din faptul că push-ul a reușit.

Deschis: decizia SVG/D3, localitățile suprapuse (neverificabile până apar date cu grupuri), și
merge-ul în `main` — proprietarul confirmă.

**Observație:** pe branch au apărut `1d081754` și `f218e1d5` (scan_surse, gitignore), plus
`AGENTS.md` modificat și `mistral-analiza-workflow.md` netracked, care nu sunt din sesiunea asta.
Altcineva/altceva scrie pe același branch — nu ating harta, dar merită știut.
