(() => {
  "use strict";

  const DATA_URL = "./data/map.json";
  const state = {
    map: null,
    counties: {},
    articles: [],
    visible: [],
    selectedCounty: null,
    selectedLocality: null,
    zoomCounty: null,
    level: "all",
    search: "",
    canvas: null,
    view: null,
    paths: [],
    localityMarkers: [],
  };

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));
  const norm = (value) => (value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, " ")
    .trim();

  function articleUrl(article) {
    return `../../${encodeURIComponent(article.category)}/${encodeURIComponent(article.slug)}/`;
  }

  function dateLabel(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat("ro-RO", {
      day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
    }).format(date);
  }

  function colors() {
    const styles = getComputedStyle(document.documentElement);
    return {
      fill: styles.getPropertyValue("--map-fill").trim() || "#dfe6ee",
      stroke: styles.getPropertyValue("--map-stroke").trim() || "#9aa8b8",
      accentSoft: styles.getPropertyValue("--accent-soft").trim() || "#cfe4ff",
      hot: styles.getPropertyValue("--map-hot").trim() || "#d94b4b",
      surface: styles.getPropertyValue("--surface").trim() || "#fff",
      text: styles.getPropertyValue("--text").trim() || "#fff",
      locality: styles.getPropertyValue("--accent").trim() || "#1769aa",
    };
  }

  // Cele doua predicate sunt separate deliberat. LISTA arata ambele feluri de potrivire --
  // NN/g ("Scoped Search") arata ca restrangerea tacita a domeniului de cautare e modul de
  // esec principal: cine scrie "accident" ar primi zero rezultate fara explicatie. HARTA, in
  // schimb, aprinde doar potrivirile de LOC -- o harta care aprinde Maramuresul fiindca un
  // titlu pomeneste Clujul minte prin constructie.
  function matchesPlace(item, query) {
    return norm(`${item.county} ${item.locality}`).includes(query);
  }

  function matchesText(item, query) {
    return norm(`${item.title} ${item.source}`).includes(query);
  }

  // `ignorePlace` sare peste filtrele de judet/localitate, pastrand nivelul si cautarea. E
  // folosit de selectorul de judete: construit din `state.visible`, dupa o selectie ar ramane
  // cu un singur buton -- cel al judetului curent -- si cine navigheaza din tastatura n-ar mai
  // avea cum sa treaca la alt judet. Acelasi mod de esec ca harta "blocata" pe judet raportata
  // pe 12 aug, pe alta cale (masurat: 38 de butoane -> 1).
  function filtered(options = {}) {
    const query = norm(state.search);
    const base = state.articles.filter((item) => {
      if (state.level !== "all" && item.category !== state.level) return false;
      if (!options.ignorePlace && state.selectedCounty && item.county !== state.selectedCounty) return false;
      if (!options.ignorePlace && state.selectedLocality) {
        const localities = Array.isArray(state.selectedLocality) ? state.selectedLocality : [state.selectedLocality];
        const itemNorm = norm(item.locality);
        if (!localities.some((loc) => norm(loc) === itemNorm)) return false;
      }
      if (!query) return true;
      return matchesPlace(item, query) || matchesText(item, query);
    });
    if (!query) return base;
    // Sortare stabila: potrivirile de loc urca primele, ordinea originala se pastreaza in
    // fiecare grup. Nimeni nu pierde rezultate; ordinea le explica.
    return [...base].sort((a, b) => Number(matchesPlace(b, query)) - Number(matchesPlace(a, query)));
  }

  function pathBounds(pathData) {
    const numbers = String(pathData).match(/-?\d+(?:\.\d+)?/g)?.map(Number) || [];
    if (numbers.length < 4) return null;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (let i = 0; i + 1 < numbers.length; i += 2) {
      const x = numbers[i];
      const y = numbers[i + 1];
      minX = Math.min(minX, x); minY = Math.min(minY, y);
      maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
    }
    if (![minX, minY, maxX, maxY].every(Number.isFinite)) return null;
    return { minX, minY, maxX, maxY };
  }

  function selectedView(vx, vy, vw, vh) {
    if (!state.zoomCounty || !state.counties[state.zoomCounty]) {
      return { x: vx, y: vy, width: vw, height: vh };
    }
    const bounds = pathBounds(state.counties[state.zoomCounty]);
    if (!bounds) return { x: vx, y: vy, width: vw, height: vh };
    const padX = Math.max(12, (bounds.maxX - bounds.minX) * 0.12);
    const padY = Math.max(12, (bounds.maxY - bounds.minY) * 0.12);
    const x = Math.max(vx, bounds.minX - padX);
    const y = Math.max(vy, bounds.minY - padY);
    const right = Math.min(vx + vw, bounds.maxX + padX);
    const bottom = Math.min(vy + vh, bounds.maxY + padY);
    return { x, y, width: Math.max(1, right - x), height: Math.max(1, bottom - y) };
  }

  // Minimul zonei de atins, in pixeli CSS (Apple HIG 44pt, Material 48dp). WCAG 2.2 SC 2.5.8
  // excepteaza explicit hartile digitale de la minimul de 24x24 ("Essential") -- dar exceptarea
  // le face conforme, nu utilizabile. Masurat 2026-08-12 pe 390px latime: 24 din 42 de judete
  // sub 44px (cel mai mic 9x15px), bulinele la ~11,7px. Raza bulinei CODEAZA numarul de stiri,
  // deci nu poate creste uniform fara sa stearga informatia: creste ZONA DE ATINS, desenul nu.
  const TINTA_MIN_CSS = 44;

  function unitatiPerPixelCss() {
    // Unitati viewBox per pixel CSS. `null` cand canvasul nu e inca masurabil.
    if (!state.view || !state.canvas) return null;
    const rect = state.canvas.getBoundingClientRect();
    return rect.width > 0 ? state.view.width / rect.width : null;
  }

  function hitDistance(point, marker, extra = 10) {
    // `point` si `marker` sunt in unitati viewBox (vezi `pointForEvent`); `extra` e in pixeli
    // CSS si se converteste, ca sa insemne aceeasi distanta reala pe orice rezolutie.
    const scale = unitatiPerPixelCss();
    if (scale === null) return Math.hypot(point.x - marker.x, point.y - marker.y) <= marker.radius + extra;
    const razaCss = marker.radius / scale;
    // Podeaua de 44px: o bulina desenata cu raza de ~5,8px CSS primea 15,8px de raza utila,
    // adica 31,7px diametru -- sub minim. Acum primeste 22px, cu desenul neschimbat.
    const razaUtilaCss = Math.max(razaCss + extra, TINTA_MIN_CSS / 2);
    return Math.hypot(point.x - marker.x, point.y - marker.y) <= razaUtilaCss * scale;
  }

  function ensureCanvas() {
    const host = $("#map");
    if (!host) return null;
    if (state.canvas && host.contains(state.canvas)) return state.canvas;
    // Un singur element canvas traieste pe toata durata paginii. Recrearea lui la
    // fiecare redesenare (host.replaceChildren() + createElement) lasa o fereastra in
    // care browserul poate compune vizual elementul vechi si cel nou suprapuse, in
    // timp ce pagina e in mijlocul unui scroll tactil real -- asta produce dedublarea
    // verticala observata pe dispozitiv (confirmata pe video 2026-08-12).
    host.replaceChildren();
    const canvas = document.createElement("canvas");
    canvas.className = "map-canvas";
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", "Harta României cu știri pe județe și localități");
    canvas.style.touchAction = "pan-y";
    canvas.style.cursor = "pointer";
    host.appendChild(canvas);
    // Garda tap-vs-drag. Cu hit-test pe tot poligonul judetului, o atingere din timpul unei
    // derulari tactile ajunge la `click` si ar selecta un judet la intamplare -- adica am
    // repara desktopul stricand telefonul. Pragul de 10px e ordinea de marime a `touch slop`-ului.
    let downAt = null;
    canvas.addEventListener("pointerdown", (e) => { downAt = { x: e.clientX, y: e.clientY }; });
    canvas.addEventListener("pointercancel", () => { downAt = null; });
    canvas.addEventListener("click", (event) => {
      const moved = downAt && Math.hypot(event.clientX - downAt.x, event.clientY - downAt.y) > 10;
      downAt = null;
      if (!moved) onCanvasClick(event);
    });
    state.canvas = canvas;

    // Butonul "Arata toate judetele" din bara de deasupra hartii iese din ecran pe mobil
    // dupa ce utilizatorul deruleaza ca sa vada harta marita -- fara alta cale de intoarcere
    // vizibila, harta pare "blocata" pe judetul selectat (raportat 2026-08-12). Ancora asta
    // traieste LANGA harta, deci ramane la indemana indiferent cat s-a derulat.
    const back = document.createElement("button");
    back.type = "button";
    back.className = "map-back";
    back.textContent = "← Toate județele";
    back.hidden = true;
    back.addEventListener("click", resetSelection);
    host.appendChild(back);
    state.backButton = back;

    return canvas;
  }

  // isPointInPath/isPointInStroke citesc transformarea CURENTA a contextului, nu una salvata.
  // buildMap() o lasa setata la final, dar asta e o coincidenta de ordine, nu o garantie: orice
  // desen intercalat ar rupe hit-testul silentios -- nu crapa, doar nu mai nimereste. De-aia
  // desenul si hit-testul trec amandoua prin functia asta.
  function applyViewTransform(ctx, canvas, view) {
    ctx.setTransform(
      canvas.width / view.width, 0, 0, canvas.height / view.height,
      -view.x * canvas.width / view.width, -view.y * canvas.height / view.height,
    );
  }

  function buildMap() {
    const host = $("#map");
    if (!host || !state.map) return;
    const canvas = ensureCanvas();
    if (!canvas) return;

    const rect = host.getBoundingClientRect();
    const viewBox = String(state.map.viewbox).trim().split(/\s+/).map(Number);
    const [vx, vy, vw, vh] = viewBox.length === 4 ? viewBox : [0, 0, 1000, 700];
    const view = selectedView(vx, vy, vw, vh);
    const cssWidth = Math.max(1, rect.width - 8);
    const cssHeight = Math.max(1, Math.min(720, cssWidth * view.height / view.width));
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.style.width = `${cssWidth}px`;
    canvas.style.height = `${cssHeight}px`;
    canvas.width = Math.max(1, Math.round(cssWidth * dpr));
    canvas.height = Math.max(1, Math.round(cssHeight * dpr));

    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) throw new Error("Canvas 2D nu este disponibil.");
    const palette = colors();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    applyViewTransform(ctx, canvas, view);
    ctx.fillStyle = palette.surface;
    ctx.fillRect(view.x, view.y, view.width, view.height);

    const counts = new Map();
    for (const item of state.visible) counts.set(item.county, (counts.get(item.county) || 0) + 1);

    const paths = [];
    for (const [county, pathData] of Object.entries(state.counties)) {
      const count = counts.get(county) || 0;
      let path;
      try { path = new Path2D(pathData); } catch { continue; }
      const hasNews = count > 0;
      // `matchesSearch` a fost STERS, nu reparat. Era o constanta recalculata de 42 de ori
      // (nu continea `county`), deci o cautare potrivita doar pe titlu stingea toata harta.
      // Dar nici versiunea per-judet nu era corecta: la o cautare care nu e un loc ("accident")
      // ar fi stins tot, desi lista arata 15 rezultate -- harta si lista ar fi spus lucruri
      // diferite. Regula corecta e mai simpla: harta arata geografia listei vizibile, atat.
      // De ce e un articol in lista se explica in ORDINE (potrivirile de loc primele) si in
      // eticheta din antet ("N potriviri de loc"), nu stingand harta.
      const dimmed = Boolean(
        (state.selectedCounty && county !== state.selectedCounty) || !hasNews,
      );

      ctx.globalAlpha = dimmed ? 0.32 : 1;
      ctx.fillStyle = state.selectedCounty === county ? palette.accentSoft : palette.fill;
      ctx.fill(path);
      ctx.globalAlpha = 1;
      ctx.strokeStyle = palette.stroke;
      ctx.lineWidth = 1.2;
      ctx.stroke(path);
      paths.push({ county, path, count, bounds: pathBounds(pathData) });
    }

    if (!state.zoomCounty) {
      for (const entry of paths) {
        if (!entry.count || !entry.bounds) continue;
        const p = {
          x: (entry.bounds.minX + entry.bounds.maxX) / 2,
          y: (entry.bounds.minY + entry.bounds.maxY) / 2,
        };
        const radius = Math.max(7, Math.min(18, 6 + Math.sqrt(entry.count) * 1.8));
        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = palette.hot;
        ctx.fill();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = palette.surface;
        ctx.stroke();
        ctx.fillStyle = palette.text;
        ctx.font = "800 11px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(entry.count), p.x, p.y);
        entry.marker = { x: p.x, y: p.y, radius };
      }
    }

    const localityMarkers = [];
    if (state.zoomCounty) {
      const groups = new Map();
      for (const item of state.visible) {
        if (item.county !== state.zoomCounty || item.x == null || item.y == null) continue;
        const x = Number(item.x);
        const y = Number(item.y);
        if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
        const coordinateKey = `${x.toFixed(4)}|${y.toFixed(4)}`;
        const siruta = item.siruta ? String(item.siruta) : "";
        const locality = item.locality || item.county;
        const key = siruta || `${norm(locality)}|${norm(item.county)}`;
        const group = groups.get(key) || {
          x, y, locality, county: item.county, siruta, count: 0, coordinateKey,
        };
        group.count += 1;
        groups.set(key, group);
      }

      // Different SIRUTA records can legitimately share a point. Keep one visual
      // marker, but preserve every locality identity so a click cannot select the wrong one.
      const byCoordinate = new Map();
      for (const group of groups.values()) {
        const existing = byCoordinate.get(group.coordinateKey);
        if (existing) {
          existing.count += group.count;
          existing.localities.push(group.locality);
          existing.sirutas.push(group.siruta);
        } else {
          byCoordinate.set(group.coordinateKey, {
            ...group,
            localities: [group.locality],
            sirutas: [group.siruta],
          });
        }
      }

      for (const group of byCoordinate.values()) {
        const radius = Math.max(5, Math.min(14, 4 + Math.sqrt(group.count) * 1.7));
        ctx.beginPath();
        ctx.arc(group.x, group.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = palette.locality;
        ctx.fill();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = palette.surface;
        ctx.stroke();
        ctx.fillStyle = palette.surface;
        ctx.font = "800 9px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(String(group.count), group.x, group.y);
        localityMarkers.push({ ...group, radius });
      }
    }

    // Salvate pe state, nu pe closure: handler-ul de click e legat o singura data pe
    // canvas (in ensureCanvas), asa ca citeste mereu ultimul rezultat aici.
    state.view = view;
    state.paths = paths;
    state.localityMarkers = localityMarkers;
    if (state.backButton) state.backButton.hidden = !state.selectedCounty;
  }

  function pointForEvent(canvas, view, event) {
    const r = canvas.getBoundingClientRect();
    if (!r.width || !r.height) return null;
    return {
      x: view.x + ((event.clientX - r.left) / r.width) * view.width,
      y: view.y + ((event.clientY - r.top) / r.height) * view.height,
    };
  }

  // isPointInPath/isPointInStroke aplica transformarea CAII, nu PUNCTULUI: x,y se citesc in
  // pixeli de canvas (verificat 2026-08-14 pe Chromium -- vezi IZZ-0193). Bulinele se compara in
  // spatiul viewBox (`pointForEvent`), poligoanele in pixeli de canvas -- doua spatii, doua
  // functii, ca sa nu se mai amestece. Greseala trecea neobservata pe desktop, unde canvasul are
  // ~820px iar viewBox-ul ~1000 de unitati: punctul cadea alaturi, dar tot pe uscat. Pe telefon
  // canvasul are 364px, deci un punct de 900 cadea in afara panzei si nu nimerea niciodata.
  function devicePointForEvent(canvas, event) {
    const r = canvas.getBoundingClientRect();
    if (!r.width || !r.height) return null;
    return {
      x: ((event.clientX - r.left) / r.width) * canvas.width,
      y: ((event.clientY - r.top) / r.height) * canvas.height,
    };
  }

  function closestHit(point, candidates, markerOf) {
    // Bulinele apropiate se pot suprapune (ex. judete mici, grupate). Alegerea primei
    // care intra in raza de atingere, indiferent de distanta reala, face ca un tap langa
    // o grupare sa "sara" mereu pe ACEEASI buline -- de-aia harta parea blocata pe un
    // singur judet, oricat de aproape ai fi apasat de altul. Se alege cea mai apropiata.
    let best = null;
    let bestDist = Infinity;
    for (const candidate of candidates) {
      const marker = markerOf(candidate);
      if (!marker || !hitDistance(point, marker)) continue;
      const dist = Math.hypot(point.x - marker.x, point.y - marker.y);
      if (dist < bestDist) { bestDist = dist; best = candidate; }
    }
    return best;
  }

  // Cascada de hit-test, de la intentia cea mai precisa la cea mai iertatoare. WCAG 2.2 SC 2.5.8
  // excepteaza explicit hartile digitale de la minimul de 24x24px ("Essential"): raza bulinei
  // CODEAZA volumul de stiri, deci marirea ei uniforma ar sterge informatia. Calea corecta e
  // zona de atins mai mare decat desenul -- exact ce recomanda si Apple HIG (44pt) si Material
  // (48dp): pictograma ramane mica, zona din jurul ei creste.

  // Toleranta de baza pe contur, in pixeli CSS, pentru ORICE judet. Exista ca sa prinda
  // atingerile care cad in afara oricarui poligon (in mare, peste Dunare, in golurile dintre
  // contururi). E ordinul de marime folosit de bibliotecile de harti pentru `hitTolerance`.
  const TOLERANTA_BAZA_CSS = 10;

  // Cat are voie sa "fure" un judet mic din vecinul lui, in pixeli CSS. Plafonul exista pentru
  // ca tinta de 44px e GEOMETRIC IMPOSIBILA pentru o enclava de 8,6px fara sa-i distrugi vecinii:
  // Bucurestiul ar avea nevoie de 17,7px de fiecare parte, iar judetele din jur au ele insele
  // doar 8-11px adancime pana la propriul contur, deci le-ar inghiti punctul cel mai adanc.
  //
  // 6px e ales prin masurare, nu din intuitie. Baleiat 22/14/10/8/6/4/3 px pe punctul cel mai
  // adanc al fiecarui judet: 22px strica 5 judete, 10px strica 2, iar de la 6px in jos ramane
  // doar Ilfovul, si acolo doar acel unic punct. Masurat pe SUPRAFATA utila (cati px² dintr-un
  // judet il mai selecteaza pe el insusi), 6px iese in castig peste tot unde conteaza:
  //   Bucuresti  59px² -> 448px² (x7,6)      Ilfov     323px² -> 549px² (x1,7)
  //   Calarasi 1511 -> 2010 · Dambovita 1057 -> 1676 · Ialomita 985 -> 1083
  //   Cluj 1502 -> 1073 · Giurgiu 1361 -> 1086 (-20..29%, dar raman peste 1000px²)
  // Adica pana si Ilfovul, vecinul de care Bucurestiul fura, iese in castig -- fiindca el
  // castiga la randul lui de la judetele mai mari din jur.
  //
  // Bucurestiul NU ajunge la 44px asa (448px² ~ un patrat de 21px). Cine vrea cu adevarat 44px
  // pentru enclave trebuie sa mute la solutia cartografica standard: caseta/bulina separata
  // langa harta, cum fac Datawrapper & co. pentru DC, Bremen sau Hamburg.
  const FURT_MAXIM_CSS = 6;

  function dimensiuneDesenataCss(entry, scale) {
    // Latura mica a formei desenate, in pixeli CSS. `bounds` e in unitati viewBox, iar `scale`
    // spune cate unitati viewBox intra intr-un pixel CSS -- deci se imparte, nu se inmulteste.
    if (!entry.bounds) return Infinity;
    return Math.min(
      (entry.bounds.maxX - entry.bounds.minX) / scale,
      (entry.bounds.maxY - entry.bounds.minY) / scale,
    );
  }

  function judeteDeLaMicLaMare(scale) {
    return state.paths
      .filter((e) => e.count > 0)
      .map((e) => ({ entry: e, dim: dimensiuneDesenataCss(e, scale) }))
      .sort((a, b) => a.dim - b.dim);
  }

  function seteazaToleranta(ctx, ceruta, scale) {
    // `isPointInStroke` intinde conturul cu lineWidth/2 in FIECARE parte, deci raza utila
    // ceruta se dubleaza inainte de conversia in unitati viewBox.
    ctx.lineWidth = ceruta * 2 * scale;
  }

  // Ordinea de interogare e ASCENDENTA dupa marimea formei, si castiga PRIMA potrivire.
  //
  // E conventia standard din bibliotecile de harti: se testeaza de sus in jos prin stiva de
  // randare, iar formele mici stau deasupra celor mari (OpenLayers `forEachFeatureAtPixel`,
  // Leaflet cu SVG unde ordinea din DOM decide). Fara ea, un judet mic care e o GAURA in altul
  // -- Bucuresti in Ilfov -- nu poate fi atins prin toleranta niciodata, fiindca vecinul mare
  // raspunde primul la orice punct din jurul lui.
  //
  // Prima incercare (2026-08-15, retrasa) a colectat toate potrivirile la un "inel" care creste
  // si a departajat dupa marime. Nu merge: la acelasi pas poate potrivi si un judet departat,
  // iar departajarea il alegea pe el in locul celui care chiar continea punctul -- centrul
  // Clujului ajungea la Salaj. Prima-potrivire-in-ordine face modul asta de esec imposibil,
  // fiindca un judet departat pur si simplu nu potriveste.
  function countyAtPoint(ctx, point) {
    const scale = unitatiPerPixelCss();
    if (scale === null) {
      return state.paths.find((e) => e.count > 0 && ctx.isPointInPath(e.path, point.x, point.y)) || null;
    }
    const candidati = judeteDeLaMicLaMare(scale);
    const previous = ctx.lineWidth;
    try {
      // 1. Judetele prea mici pentru un deget, cu zona de atins invizibila. Doar ele au voie sa
      //    ia puncte din interiorul unui vecin, si doar cat le trebuie ca sa ajunga la 44px --
      //    nu o valoare fixa, altfel unul aproape suficient de mare ar fura cat unul minuscul.
      //    Decizie de proprietar 2026-08-15; compromisul, spus pe fata: atingeri de la marginea
      //    vecinului mare ajung la judetul mic.
      for (const c of candidati) {
        if (c.dim >= TINTA_MIN_CSS) continue;
        const ceruta = Math.min(FURT_MAXIM_CSS, (TINTA_MIN_CSS - c.dim) / 2);
        if (ceruta <= 0) continue;
        seteazaToleranta(ctx, ceruta, scale);
        if (ctx.isPointInPath(c.entry.path, point.x, point.y)
            || ctx.isPointInStroke(c.entry.path, point.x, point.y)) return c.entry;
      }
      // 2. Formele propriu-zise, tot de la cel mai mic: cine chiar contine punctul.
      for (const c of candidati) {
        if (ctx.isPointInPath(c.entry.path, point.x, point.y)) return c.entry;
      }
      // 3. Toleranta de baza, pentru atingerile din afara oricarui poligon.
      for (const c of candidati) {
        seteazaToleranta(ctx, TOLERANTA_BAZA_CSS, scale);
        if (ctx.isPointInStroke(c.entry.path, point.x, point.y)) return c.entry;
      }
      return null;
    } finally {
      ctx.lineWidth = previous;
    }
  }

  // --- starea in adresa paginii ----------------------------------------------------------
  // Toate schimbarile de stare trec prin `applyState`. Fara asta ar exista cai care muta harta
  // fara sa mute adresa: un link partajat ar duce pe alta stare decat cea vazuta de cel care
  // l-a trimis, iar Back ar sari de pe pagina in loc sa anuleze ultima selectie.

  function urlForState() {
    const params = new URLSearchParams();
    if (state.level && state.level !== "all") params.set("nivel", state.level);
    if (state.selectedCounty) params.set("judet", state.selectedCounty);
    const loc = Array.isArray(state.selectedLocality)
      ? state.selectedLocality
      : (state.selectedLocality ? [state.selectedLocality] : []);
    // Mai multe localitati pot cadea pe acelasi marker; toate intra in link, altfel cel care
    // deschide adresa vede mai putine stiri decat cel care a trimis-o.
    if (loc.length) params.set("loc", loc.join("|"));
    if (state.search) params.set("q", state.search);
    const query = params.toString();
    return query ? `${location.pathname}?${query}` : location.pathname;
  }

  function stateFromUrl() {
    const params = new URLSearchParams(location.search);
    const loc = params.get("loc");
    return {
      level: params.get("nivel") || "all",
      county: params.get("judet") || null,
      locality: loc ? loc.split("|").filter(Boolean) : null,
      query: params.get("q") || "",
    };
  }

  function applyState(patch, { push = true, replace = false } = {}) {
    if ("level" in patch) state.level = patch.level || "all";
    if ("county" in patch) state.selectedCounty = patch.county || null;
    if ("locality" in patch) state.selectedLocality = patch.locality || null;
    if ("query" in patch) state.search = patch.query || "";
    // `zoomCounty` nu e stare independenta, e derivata: la nivel Judetean click-ul filtreaza
    // fara sa mareasca (decizie proprietar, 13 aug). Tinuta separat, se desincroniza.
    state.zoomCounty = state.selectedCounty && state.level !== "judetean" ? state.selectedCounty : null;
    state.visible = filtered();

    const search = $("#map-search");
    if (search && search.value !== state.search) search.value = state.search;
    syncLevelButtons();
    buildMap();
    renderList();
    updateStats();

    if (!push && !replace) return;
    const url = urlForState();
    if (url === `${location.pathname}${location.search}`) return;
    // `replaceState` la tastare: altfel fiecare litera ar lasa o intrare in istoric si Back ar
    // trebui apasat de zece ori ca sa iasa dintr-o cautare de zece caractere.
    if (replace) history.replaceState(null, "", url);
    else history.pushState(null, "", url);
  }

  function selectCounty(county) {
    applyState({ county, locality: null });
  }

  function updateCountyPicker() {
    const picker = $("#county-picker");
    if (!picker) return;
    // Butoanele se reconstruiesc la fiecare redesenare, deci elementul care avea focusul dispare
    // si focusul cade pe <body>. Pentru cineva care navigheaza din tastatura asta inseamna ca
    // dupa fiecare Enter o ia de la capat cu Tab-ul. Retinem judetul focusat si il refocusam.
    const active = document.activeElement;
    const focusedCounty = active && active.closest && active.closest("#county-picker")
      ? active.dataset.county : null;

    const pool = filtered({ ignorePlace: true });
    const counts = new Map();
    for (const item of pool) {
      if (!item.county) continue;
      counts.set(item.county, (counts.get(item.county) || 0) + 1);
    }
    picker.replaceChildren();
    for (const county of Array.from(counts.keys()).sort()) {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.county = county;
      button.textContent = `${county} · ${counts.get(county)}`;
      button.setAttribute("aria-pressed", county === state.selectedCounty ? "true" : "false");
      button.addEventListener("click", () => selectCounty(county));
      picker.appendChild(button);
      if (county === focusedCounty) button.focus();
    }
  }

  function onCanvasClick(event) {
    const canvas = state.canvas;
    const view = state.view;
    if (!canvas || !view) return;
    const p = pointForEvent(canvas, view, event);
    if (!p) return;
    if (state.zoomCounty) {
      const marker = closestHit(p, state.localityMarkers, (m) => m);
      if (marker) {
        // Filtrarea pe localitate are camp propriu de stare. Inainte se facea scriind
        // localitatea in `#map-search`, ceea ce stergea ce tastase utilizatorul SI aducea,
        // prin cautarea in titluri, articole din alte judete care doar o pomeneau.
        // Daca mai multe localitati cad exact pe acelasi punct (deduplicare vizuala), se
        // filtreaza pe TOATE, nu doar pe prima.
        applyState({ locality: marker.localities || [marker.locality] });
      }
    } else {
      // Transformarea se reafirma explicit inainte de hit-test: buildMap() o lasa setata, dar
      // a te baza pe ordinea apelurilor face hit-testul sa cada silentios la prima schimbare.
      const ctx = canvas.getContext("2d");
      applyViewTransform(ctx, canvas, view);
      const dp = devicePointForEvent(canvas, event);
      // Poligoanele se interogheaza INAINTEA bulinelor, nu dupa. Cat timp `closestHit` era
      // primul, pasul pentru judetele mici din `countyAtPoint` nu se executa niciodata pentru
      // exact perechea pentru care fusese scris: bulina Bucurestiului si cea a Ilfovului sunt
      // la ~4px una de alta pe un ecran de 375px (IZZ-0177), deci "cea mai apropiata bulina"
      // alegea practic arbitrar intre ele si returna inainte sa se ajunga la poligoane.
      // Bulinele raman ca rezerva: pentru forme concave, centroidul (deci bulina) poate cadea
      // in afara propriului judet, si atunci atingerea pe bulina trebuie sa functioneze oricum.
      const entry = (dp && countyAtPoint(ctx, dp))
        || closestHit(p, state.paths, (e) => e.marker);
      if (entry) {
        selectCounty(entry.county);
      }
    }
  }

  function renderList() {
    const list = $("#news-list");
    if (!list) return;
    const all = filtered();
    const items = all.slice(0, 120);
    list.replaceChildren();
    for (const item of items) {
      const li = document.createElement("li");
      const a = document.createElement("a");
      a.href = articleUrl(item);
      a.textContent = item.title || "Fără titlu";
      const meta = document.createElement("span");
      meta.textContent = [item.locality, item.county, item.source, dateLabel(item.published)]
        .filter(Boolean).join(" · ");
      li.append(a, meta);
      list.appendChild(li);
    }
    const count = $("#panel-count");
    if (count) {
      const query = norm(state.search);
      const shown = all.length > items.length
        ? `${items.length} din ${all.length} știri`
        : `${items.length} știri`;
      // Cand exista o cautare, antetul spune DE CE e acolo fiecare rezultat: cate au potrivit
      // pe loc (si stau primele in lista) si cate au intrat doar prin titlu sau sursa.
      const places = query ? all.filter((item) => matchesPlace(item, query)).length : 0;
      count.textContent = query ? `${shown} · ${places} potriviri de loc` : shown;
    }
    updateCountyPicker();
  }

  function updateStats() {
    const stats = $("#map-stats");
    if (!stats) return;
    const counties = new Set(state.visible.map((item) => item.county).filter(Boolean)).size;
    const localities = new Set(state.visible.map((item) => item.siruta || `${norm(item.locality)}|${norm(item.county)}`).filter(Boolean)).size;
    stats.replaceChildren();
    const span = document.createElement("span");
    span.textContent = `${state.visible.length} știri · ${counties} județe · ${localities} localități`;
    stats.appendChild(span);
  }

  function syncLevelButtons() {
    $$(".segmented [data-level]").forEach((button) => {
      button.classList.toggle("active", button.dataset.level === state.level);
      button.setAttribute("aria-pressed", button.dataset.level === state.level ? "true" : "false");
    });
  }

  function resetSelection() {
    applyState({ county: null, locality: null, query: "" });
  }

  function bindControls() {
    const search = $("#map-search");
    const clear = $("#clear-selection");
    if (search) search.addEventListener("input", () => {
      applyState({ query: search.value }, { replace: true });
    });
    $$(".segmented [data-level]").forEach((button) => button.addEventListener("click", () => {
      // Schimbarea de nivel schimba INSASI regula de interactiune (zoom sau nu la click pe
      // judet) -- o selectie ramasa de la nivelul anterior ar produce o stare incoerenta
      // (ex. harta ramasa marita cand ai trecut pe Judetean, unde click-ul nu mai face zoom).
      applyState({ level: button.dataset.level || "all", county: null, locality: null, query: "" });
    }));
    if (clear) clear.addEventListener("click", resetSelection);
    window.addEventListener("popstate", () => applyState(stateFromUrl(), { push: false }));
  }

  function bindResize() {
    const host = $("#map");
    if (!host || typeof ResizeObserver === "undefined") return;
    let scheduled = false;
    let lastWidth = Math.round(host.getBoundingClientRect().width);
    const observer = new ResizeObserver((entries) => {
      const width = Math.round(entries[0]?.contentRect?.width ?? host.getBoundingClientRect().width);
      // Doar latimea afecteaza layout-ul hartii (inaltimea e derivata din ea). Pe mobil,
      // aparitia/disparitia barei de adrese la scroll schimba inaltimea ferestrei, nu
      // latimea -- fara garda asta, fiecare din acele evenimente redeschide un canvas
      // nou in mijlocul unui scroll, ceea ce e cauza dedublarii vizuale (vezi ensureCanvas).
      if (width === lastWidth) return;
      lastWidth = width;
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(() => {
        scheduled = false;
        buildMap();
      });
    });
    observer.observe(host);
  }

  async function init() {
    bindControls();
    const response = await fetch(DATA_URL, { cache: "no-store" });
    if (!response.ok) throw new Error(`map.json HTTP ${response.status}`);
    const data = await response.json();
    state.map = data.map || {};
    state.counties = state.map.judete || {};
    state.articles = Array.isArray(data.articles) ? data.articles : [];
    // Starea din adresa se aplica INAINTE de prima desenare, altfel harta apare o clipa
    // nefiltrata si abia apoi sare pe judetul din link.
    applyState(stateFromUrl(), { push: false });
    bindResize();
  }

  init().catch((error) => {
    console.error(error);
    const host = $("#map");
    if (host) host.textContent = "Harta nu a putut fi încărcată.";
  });
})();