# Harta știrilor — feliile 4 și 7, design pe bune practici

**Scris de:** sesiune Opus, cont A, 14 aug 2026
**Statut:** GO de la proprietar („caută bune practici și implementează", 14 aug 2026)
**Deblochează:** `IZZ-0176` (era `blocat`, „decizie de proprietar, netranșată")
**Completează:** `specs/harta-imbunatatiri-2026-08-14.md` §4, feliile 4 și 7

> Feliile 4 și 7 erau scrise acolo ca variante, fără decizie. Fișierul ăsta le înlocuiește cu
> un design unic, argumentat pe surse. Codul de mai jos e cel care se aplică — nu o schiță.

---

## Partea I — Apăsarea pe hartă (felia 4)

### Ce spun sursele

**WCAG 2.2, SC 2.5.8 „Target Size (Minimum)"** cere ținte de minimum 24×24px CSS, dar are două
excepții care se aplică amândouă direct cazului nostru:

- **Excepția „Essential":** „If the size and spacing of the targets is fundamental to the
  information being conveyed … **in digital maps, the position of pins is analogous to the
  position of places shown on the map**." Bulinele noastre codează **volumul** de știri prin rază
  (`radius = 6 + √count × 1.8`, plafonat la 18). A le mări uniform ar șterge exact informația pe
  care o transmit.
- **Excepția „Equivalent":** „The function can be achieved through a different control on the same
  page that meets this criterion." Adică: **calea conformă nu e mărirea bulinelor, ci un control
  HTML echivalent** — exact felia 5 din specul principal.

Sursă: [W3C — Understanding SC 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)

Pragurile de confort (nu de conformitate) sunt **44×44pt** la Apple HIG și **48×48dp** la Material
Design — ambele spun explicit că *pictograma* poate rămâne mică dacă zona de atins e mărită prin
padding invizibil. Asta validează direct abordarea „zonă de atins mai mare decât desenul".

Sursă: [TetraLogical — Foundations: target sizes](https://tetralogical.com/blog/2022/12/20/foundations-target-size/)

Pentru Canvas, tehnica de toleranță consacrată e: **nu îngroșa conturul la desenare**, ci
umflă `lineWidth` **doar înainte** de `isPointInStroke` și resetează-l imediat după —
zona de atins crește fără ca desenul să se schimbe.

Sursă: [Canvas Hit Detection Methods — joshuatz.com](https://joshuatz.com/posts/2022/canvas-hit-detection-methods/)

### Concluzia de design

Varianta „măresc bulinele" din întrebarea pusă proprietarului e **respinsă de surse**, nu de gust:
distruge informația protejată chiar de excepția Essential. Se implementează în schimb o
**cascadă de patru straturi**, de la intenția cea mai precisă la cea mai iertătoare:

| Strat | Ce prinde | Tehnică |
|---|---|---|
| 1. Bulina | intenție precisă: „vreau ăsta" | `closestHit` pe markeri (există deja) |
| 2. Interiorul județului | ținta mare, iertătoare — rezolvă majoritatea ratărilor | `ctx.isPointInPath(path, x, y)` |
| 3. Marginea județului, cu toleranță | județele mici (Ilfov, București, Covasna) unde interiorul e sub deget | `ctx.isPointInStroke` cu `lineWidth` umflat temporar |
| 4. Control HTML echivalent | tastatură, cititor de ecran, județe imposibil de nimerit | felia 5 din specul principal |

Straturile 1-3 sunt felia asta. Stratul 4 rămâne felia 5 și **nu e opțional** — el e cel care
satisface WCAG prin excepția Equivalent; 1-3 doar fac harta plăcută la deget.

### Capcana tehnică (citește înainte să scrii cod)

`isPointInPath(path, x, y)` interpretează `x,y` în **transformarea curentă a contextului**.
`buildMap()` lasă transformarea setată pe viewBox la final, iar `pointForEvent()` întoarce
coordonate în același spațiu — deci azi se potrivesc **din accident**. Orice desen făcut între
timp de altcineva rupe hit-testul **silențios**: nu crapă, doar nu mai nimerește.

De-aia transformarea se **reafirmă explicit** înainte de hit-test, printr-o funcție extrasă și
folosită în ambele locuri. Nu e curățenie opțională — e condiția ca stratul 2 și 3 să fie fiabile.

### Cod

**1. Extrage transformarea într-o funcție** (în `harta-stiri.js`, deasupra lui `buildMap`):

```js
// isPointInPath/isPointInStroke citesc transformarea CURENTA a contextului, nu una salvata.
// buildMap() o lasa setata la final, dar asta e o coincidenta de ordine, nu o garantie: orice
// desen intercalat ar rupe hit-testul silentios -- nu crapa, doar nu mai nimereste. De-aia
// ambele locuri (desen si hit-test) trec prin functia asta.
function applyViewTransform(ctx, canvas, view) {
  ctx.setTransform(
    canvas.width / view.width, 0, 0, canvas.height / view.height,
    -view.x * canvas.width / view.width, -view.y * canvas.height / view.height,
  );
}
```

În `buildMap()`, înlocuiește al doilea `ctx.setTransform(...)` (cel lung, de după `clearRect`) cu
`applyViewTransform(ctx, canvas, view);`. Primul `setTransform(1,0,0,1,0,0)` **rămâne** — el
resetează înainte de `clearRect` și e fix-ul pentru o regresie reală.

**2. Hit-test în cascadă** — funcție nouă, lângă `closestHit`:

```js
// Toleranta pe contur: `lineWidth` se umfla DOAR pentru interogare si se reseteaza imediat,
// deci zona de atins creste fara ca desenul sa se schimbe (tehnica din joshuatz.com/posts/2022/
// canvas-hit-detection-methods). Necesara pentru judetele mici -- Ilfov si Bucuresti au
// interiorul sub dimensiunea unui deget la 390px.
const EDGE_TOLERANCE = 10; // px in spatiul viewBox-ului

function countyAtPoint(ctx, point) {
  const inside = state.paths.find((e) => e.count > 0 && ctx.isPointInPath(e.path, point.x, point.y));
  if (inside) return inside;
  const previous = ctx.lineWidth;
  ctx.lineWidth = EDGE_TOLERANCE;
  try {
    return state.paths.find((e) => e.count > 0 && ctx.isPointInStroke(e.path, point.x, point.y)) || null;
  } finally {
    ctx.lineWidth = previous;
  }
}
```

**3. Garda tap-vs-drag** — necesară pe Android, unde zona mare de atins transformă o atingere
accidentală din timpul derulării într-o selecție de județ. Fără ea, felia asta *introduce* un bug
pe mobil în timp ce îl repară pe cel de pe desktop.

În `ensureCanvas()`, lângă `canvas.addEventListener("click", onCanvasClick)`:

```js
// Zona de atins mare + derulare tactila = selectii accidentale: pe Android, o atingere in
// timpul derularii ajunge la `click` daca degetul nu s-a miscat mult. Pragul de 10px e
// aceeasi ordine de marime cu `touch slop`-ul platformei.
let downAt = null;
canvas.addEventListener("pointerdown", (e) => { downAt = { x: e.clientX, y: e.clientY }; });
canvas.addEventListener("pointercancel", () => { downAt = null; });
canvas.addEventListener("click", (event) => {
  if (downAt && Math.hypot(event.clientX - downAt.x, event.clientY - downAt.y) > 10) {
    downAt = null;
    return;
  }
  downAt = null;
  onCanvasClick(event);
});
```

Șterge vechiul `canvas.addEventListener("click", onCanvasClick);` — altfel se leagă de două ori.

**4. Folosește cascada** în `onCanvasClick()`, ramura fără zoom:

```js
} else {
  const entry = closestHit(p, state.paths, (e) => e.marker)
    || countyAtPoint(canvas.getContext("2d"), p);
  if (entry) {
    state.selectedCounty = entry.county;
    if (state.level !== "judetean") state.zoomCounty = entry.county;
    state.visible = filtered();
    buildMap();
    renderList();
    updateStats();
  }
}
```

`canvas.style.cursor = "pointer"` e deja pus pe tot canvasul (`ensureCanvas`), deci afordanța
vizuală pe desktop devine în sfârșit adevărată — până acum cursorul promitea click pe toată
harta, iar codul îl onora doar pe buline.

### Criterii de acceptare

- Click în interiorul unui județ mare (Timiș), departe de bulină → aceeași stare ca și clickul
  pe bulină: același `selectedCounty`, aceeași listă, același `#panel-count`.
- Click la ~5px **în afara** conturului unui județ mic (Ilfov) → tot îl selectează (stratul 3).
- Click în mare / în afara României → nu selectează nimic, nu aruncă eroare.
- Cu degetul simulat pe Android (Playwright `is_mobile=True, has_touch=True`): o derulare de
  200px care începe pe hartă **nu** selectează niciun județ.
- `node --check static/harta-stiri/harta-stiri.js` fără erori.
- Cele 6 teste din `tests/test_harta_interactions.py` rămân verzi (verifică `setTransform(1, 0,
  0, 1, 0, 0)` — de-aia primul reset **rămâne** neatins).

---

## Partea II — Ce caută lupa de pe hartă (felia 7)

### Ce spun sursele

NN/g, „Scoped Search: Dangerous, but Sometimes Useful", constată că **utilizatorii ignoră, uită
sau înțeleg greșit domeniul căutării** — se așteaptă ca o căsuță de căutare să caute peste tot.
Recomandările concrete:

- „always set the default scope to **'all'**" — site-urile care preselectează un domeniu sunt
  „the worst offenders";
- oferă „a one-click option to **expand the search** to the entire site";
- „make scoped search apparent by using **strong visual cues**", cu eticheta domeniului lipită de
  căsuță **și** în capul rezultatelor.

Sursă: [NN/g — Scoped Search](https://www.nngroup.com/articles/scoped-search/)

### Concluzia de design — și de ce NU varianta A

Varianta A din specul principal („strict geografic, o linie de cod") era recomandarea mea inițială.
**Sursele o infirmă.** Ar restrânge tăcut domeniul căutării exact în felul pe care NN/g îl numește
periculos: cine scrie „accident" sau „primărie" ar primi zero rezultate, fără explicație și fără
cale de ieșire.

Problema reală nu e că se caută prea larg. E că **promisiunea și comportamentul nu coincid**:
eticheta zice „Caută județ / localitate…", codul caută și în titlu și în sursă. Se repară
promisiunea, nu domeniul.

**Designul, în patru mișcări:**

1. **Eticheta spune adevărul.** Placeholder: „Caută loc, titlu sau sursă…"; textul ascuns pentru
   cititoare de ecran, la fel.
2. **Potrivirile de loc urcă primele în listă.** „Cluj" arată întâi cele 12 articole etichetate
   Cluj, apoi cele care doar îl pomenesc în titlu. Nimeni nu pierde rezultate; ordinea le explică.
3. **Antetul rezultatelor spune de ce e acolo fiecare.** Când există o căutare activă:
   `24 din 33 știri · 12 potriviri de loc`.
4. **Harta reflectă DOAR potrivirile de loc.** O hartă care aprinde Maramureșul fiindcă un titlu
   pomenește Clujul minte prin definiție. Fiecare suprafață spune ce poate spune onest.

Punctul 4 e și reparația corectă pentru bug-ul `matchesSearch` din felia 2 — **coordonează-te cu
felia 2**: dacă felia 2 e deja aplicată, punctul 4 doar înlocuiește condiția; dacă nu, se face aici.

### Cod

**1. `index.html`** — două șiruri, atât:

```html
<span class="sr-only">Caută loc, titlu sau sursă</span>
<input id="map-search" type="search" placeholder="Caută loc, titlu sau sursă…" autocomplete="off">
```

**2. `harta-stiri.js`** — separă cele două feluri de potrivire:

```js
// Cele doua predicate sunt separate deliberat: LISTA arata ambele feluri de potrivire (NN/g:
// nu restrange tacit domeniul cautarii), dar HARTA aprinde doar potrivirile de loc -- o harta
// care aprinde Maramuresul fiindca un titlu pomeneste Clujul minte prin definitie.
function matchesPlace(item, query) {
  return norm(`${item.county} ${item.locality}`).includes(query);
}

function matchesText(item, query) {
  return norm(`${item.title} ${item.source}`).includes(query);
}
```

În `filtered()`, înlocuiește blocul de căutare și sortează potrivirile de loc în față:

```js
function filtered() {
  const query = norm(state.search);
  const base = state.articles.filter((item) => {
    if (state.level !== "all" && item.category !== state.level) return false;
    if (state.selectedCounty && item.county !== state.selectedCounty) return false;
    if (state.selectedLocality && norm(item.locality) !== norm(state.selectedLocality)) return false;
    if (!query) return true;
    return matchesPlace(item, query) || matchesText(item, query);
  });
  if (!query) return base;
  // Sortare stabila: potrivirile de loc primele, ordinea originala pastrata in fiecare grup.
  return [...base].sort((a, b) => Number(matchesPlace(b, query)) - Number(matchesPlace(a, query)));
}
```

> `state.selectedLocality` vine din **felia 2**. Dacă felia 2 nu e încă aplicată, lasă linia
> aceea afară și adaug-o odată cu ea — nu inventa un câmp care nu există.

În `renderList()`, extinde linia de număr scrisă la felia 1:

```js
const count = $("#panel-count");
if (count) {
  const query = norm(state.search);
  const places = query ? all.filter((item) => matchesPlace(item, query)).length : 0;
  const shown = all.length > items.length
    ? `${items.length} din ${all.length} știri`
    : `${items.length} știri`;
  count.textContent = query ? `${shown} · ${places} potriviri de loc` : shown;
}
```

În `buildMap()`, condiția de estompare devine per-județ **și strict geografică**:

```js
const matchesSearch = !query || state.visible.some((item) =>
  item.county === county && matchesPlace(item, query));
```

Scoate `const query = norm(state.search);` din bucla pe județe și pune-l deasupra ei.

### Criterii de acceptare

- Cauți „Cluj": lista începe cu articole al căror `county`/`locality` e Cluj; cele din Maramureș
  și Sibiu apar **după**, nu dispar. `#panel-count` conține „potriviri de loc".
- Cauți „accident" (sau alt cuvânt care nu e loc): **primești rezultate**, nu zero — asta e exact
  regresia pe care varianta A o producea.
- Pe hartă, la căutarea „Cluj", se aprind doar județele cu potrivire de **loc**; județele care
  potrivesc doar prin titlu rămân estompate.
- Placeholder-ul și textul `sr-only` spun același lucru cu ce face codul.
- `node --check` + `pytest` verzi.

---

## Ordinea de aplicare

Feliile astea două ating **același fișier** ca feliile 1 și 2. Ordine obligatorie, fără suprapunere:

```
felia 1 (lista)  →  felia 2 (bug-uri logica)  →  felia 7 (cautare)  →  felia 4 (hit-test)
```

Felia 3 (captura mobilă) e independentă, poate rula oricând.
Felia 5 (control de tastatură) vine după felia 4 — nu invers: felia 5 refolosește funcția
`selectCounty()` pe care felia 4 o consolidează.

## Rânduri de registru la final

```bash
python tools/registru.py add --zona harta --data 2026-08-14 --stare implementat \
  --titlu "Hit-test in cascada pe harta: bulina -> poligon -> contur cu toleranta" \
  --dovada "<hash>" --leaga IZZ-0176
```

```bash
python tools/registru.py add --zona harta --data 2026-08-14 --stare respins \
  --titlu "Varianta A -- cautare strict geografica pe harta (scoate title/source din haystack)" \
  --motiv "NN/g Scoped Search: restrangerea tacita a domeniului e modul de esec principal; 'accident' ar da zero rezultate fara explicatie. Reparat in schimb decalajul eticheta-comportament plus rangul potrivirilor de loc." \
  --dovada "https://www.nngroup.com/articles/scoped-search/"
```

```bash
python tools/registru.py add --zona harta --data 2026-08-14 --stare respins \
  --titlu "Marirea uniforma a bulinelor ca solutie pentru tinta de atins pe mobil" \
  --motiv "WCAG 2.2 SC 2.5.8 excepteaza explicit hartile digitale (Essential): raza bulinei codeaza volumul de stiri, marirea uniforma sterge informatia. Calea conforma e excepta Equivalent -- control HTML echivalent (felia 5)." \
  --dovada "https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html" --leaga IZZ-0176
```
