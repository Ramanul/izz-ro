(() => {
  "use strict";

  const DATA_URL = "./data/map.json";
  const state = {
    map: null,
    counties: {},
    articles: [],
    visible: [],
    selectedCounty: null,
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

  function filtered() {
    const query = norm(state.search);
    return state.articles.filter((item) => {
      if (state.level !== "all" && item.category !== state.level) return false;
      if (state.selectedCounty && item.county !== state.selectedCounty) return false;
      if (!query) return true;
      const haystack = norm([item.title, item.locality, item.county, item.source].join(" "));
      return haystack.includes(query);
    });
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

  function hitDistance(point, marker, extra = 5) {
    return Math.hypot(point.x - marker.x, point.y - marker.y) <= marker.radius + extra;
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
    canvas.addEventListener("click", onCanvasClick);
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
    ctx.setTransform(canvas.width / view.width, 0, 0, canvas.height / view.height,
      -view.x * canvas.width / view.width, -view.y * canvas.height / view.height);
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
      const query = norm(state.search);
      const matchesSearch = !query || state.visible.some((item) =>
        norm(`${item.county} ${item.locality}`).includes(query));
      const dimmed = Boolean(
        (state.selectedCounty && county !== state.selectedCounty) || !hasNews || !matchesSearch,
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

  function onCanvasClick(event) {
    const canvas = state.canvas;
    const view = state.view;
    if (!canvas || !view) return;
    const p = pointForEvent(canvas, view, event);
    if (!p) return;
    if (state.zoomCounty) {
      const marker = closestHit(p, state.localityMarkers, (m) => m);
      if (marker) {
        const locality = marker.localities[0] || marker.locality;
        state.search = locality;
        const search = $("#map-search");
        if (search) search.value = locality;
        state.visible = filtered();
        renderList();
        updateStats();
      }
    } else {
      const entry = closestHit(p, state.paths, (e) => e.marker);
      if (entry) {
        // "Județean": lista se filtreaza la judet, harta ramane pe toata tara -- se poate
        // trece direct la alt judet fara pas de "inapoi". "Local"/"Toate": zoom pe judet,
        // ca sa se vada UAT-urile lui (cerut de owner, 2026-08-13, dupa ce zoom-ul mereu-pornit
        // s-a dovedit neintuitiv la nivel Judetean).
        state.selectedCounty = entry.county;
        if (state.level !== "judetean") state.zoomCounty = entry.county;
        state.visible = filtered();
        buildMap();
        renderList();
        updateStats();
      }
    }
  }

  function renderList() {
    const list = $("#news-list");
    if (!list) return;
    const items = filtered().slice(0, 120);
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
    if (count) count.textContent = `${items.length} știri`;
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
    state.search = "";
    state.selectedCounty = null;
    state.zoomCounty = null;
    state.visible = filtered();
    const search = $("#map-search");
    if (search) search.value = "";
    syncLevelButtons();
    buildMap();
    renderList();
    updateStats();
  }

  function bindControls() {
    const search = $("#map-search");
    const clear = $("#clear-selection");
    if (search) search.addEventListener("input", () => {
      state.search = search.value;
      state.visible = filtered();
      buildMap();
      renderList();
      updateStats();
    });
    $$(".segmented [data-level]").forEach((button) => button.addEventListener("click", () => {
      state.level = button.dataset.level || "all";
      // Schimbarea de nivel schimba INSASI regula de interactiune (zoom sau nu la click pe
      // judet) -- o selectie ramasa de la nivelul anterior ar produce o stare incoerenta
      // (ex. harta ramasa marita cand ai trecut pe Judetean, unde click-ul nu mai face zoom).
      state.selectedCounty = null;
      state.zoomCounty = null;
      state.search = "";
      const search = $("#map-search");
      if (search) search.value = "";
      state.visible = filtered();
      syncLevelButtons();
      buildMap();
      renderList();
      updateStats();
    }));
    if (clear) clear.addEventListener("click", resetSelection);
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
    state.visible = filtered();
    syncLevelButtons();
    buildMap();
    bindResize();
    renderList();
    updateStats();
  }

  init().catch((error) => {
    console.error(error);
    const host = $("#map");
    if (host) host.textContent = "Harta nu a putut fi încărcată.";
  });
})();