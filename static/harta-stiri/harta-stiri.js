(() => {
  "use strict";

  const DATA_URL = "./data/map.json";
  const state = {
    map: null,
    counties: {},
    articles: [],
    visible: [],
    selectedCounty: null,
    level: "all",
    search: "",
  };

  const $ = (selector) => document.querySelector(selector);
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

  function bucket(count) {
    if (count >= 20) return "high";
    if (count >= 10) return "medium";
    return "low";
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

  function colors() {
    const styles = getComputedStyle(document.documentElement);
    return {
      fill: styles.getPropertyValue("--map-fill").trim() || "#dfe6ee",
      stroke: styles.getPropertyValue("--map-stroke").trim() || "#9aa8b8",
      accentSoft: styles.getPropertyValue("--accent-soft").trim() || "#cfe4ff",
      hot: styles.getPropertyValue("--map-hot").trim() || "#d94b4b",
      surface: styles.getPropertyValue("--surface").trim() || "#fff",
      text: styles.getPropertyValue("--text").trim() || "#fff",
    };
  }

  function buildMap() {
    const host = $("#map");
    host.replaceChildren();

    // Canvas is intentional here. The real-device Android failure is a visual
    // repaint/compositing smear during touch scrolling, not DOM accumulation:
    // the previous implementation used a large dynamically-created SVG. Canvas
    // keeps the map as one raster drawing surface and removes SVG layer repaint
    // state from the browser compositor.
    const canvas = document.createElement("canvas");
    canvas.className = "map-canvas";
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", "Harta României cu știri pe județe");
    canvas.style.touchAction = "pan-y";
    host.appendChild(canvas);

    const rect = host.getBoundingClientRect();
    const viewBox = String(state.map.viewbox).trim().split(/\s+/).map(Number);
    const [vx, vy, vw, vh] = viewBox.length === 4 ? viewBox : [0, 0, 1000, 700];
    const cssWidth = Math.max(1, rect.width - 8);
    const cssHeight = Math.max(1, Math.min(720, cssWidth * vh / vw));
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.style.width = `${cssWidth}px`;
    canvas.style.height = `${cssHeight}px`;
    canvas.width = Math.max(1, Math.round(cssWidth * dpr));
    canvas.height = Math.max(1, Math.round(cssHeight * dpr));

    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) throw new Error("Canvas 2D nu este disponibil.");
    ctx.setTransform(canvas.width / vw, 0, 0, canvas.height / vh, -vx * canvas.width / vw, -vy * canvas.height / vh);
    ctx.clearRect(vx, vy, vw, vh);

    const palette = colors();
    const counts = new Map();
    for (const item of state.visible) counts.set(item.county, (counts.get(item.county) || 0) + 1);

    const paths = [];
    for (const [county, pathData] of Object.entries(state.counties)) {
      const count = counts.get(county) || 0;
      let path;
      try {
        path = new Path2D(pathData);
      } catch {
        continue;
      }
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
      paths.push({ county, path, count });
    }

    // Draw count markers in the same canvas, using the same deterministic
    // centroid calculation previously used by the SVG implementation.
    // Bounds are approximated from the path via a temporary hit region only
    // where possible; the map JSON also carries the county geometry, so the
    // visual marker remains one per county with news.
    for (const entry of paths) {
      if (!entry.count) continue;
      // Use the path's visual center through an offscreen geometry-independent
      // grid search. This is intentionally cheap because there are only 42
      // counties; it avoids parsing SVG commands, which was a previous source
      // of incorrect marker positions.
      const p = centroidForPath(ctx, entry.path, vx, vy, vw, vh);
      if (!p) continue;
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

    const pointForEvent = (event) => {
      const r = canvas.getBoundingClientRect();
      return {
        x: vx + ((event.clientX - r.left) / r.width) * vw,
        y: vy + ((event.clientY - r.top) / r.height) * vh,
      };
    };

    canvas.addEventListener("click", (event) => {
      const p = pointForEvent(event);
      for (const entry of paths) {
        if (ctx.isPointInPath(entry.path, p.x, p.y)) {
          selectCounty(entry.count ? entry.county : null);
          return;
        }
      }
    });

    canvas.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
    });
  }

  // Return the visual center of a Path2D without parsing SVG path syntax.
  // We use a deterministic sampling grid and choose the mean of hit points.
  // 42 counties make this inexpensive and it works with every SVG command that
  // Path2D accepts in Chromium/Android Chrome.
  function centroidForPath(ctx, path, x, y, width, height) {
    const samples = [];
    const stepX = width / 80;
    const stepY = height / 56;
    for (let py = y; py <= y + height; py += stepY) {
      for (let px = x; px <= x + width; px += stepX) {
        if (ctx.isPointInPath(path, px, py)) samples.push({ x: px, y: py });
      }
    }
    if (!samples.length) return null;
    const middle = samples.slice().sort((a, b) => (a.y - b.y) || (a.x - b.x));
    const center = middle[Math.floor(middle.length / 2)];
    return center || null;
  }

  function renderList() {
    const list = $("#news-list");
    const items = filtered();
    $("#panel-count").textContent = `${items.length} știri`;
    $("#panel-title").textContent = state.selectedCounty ? `Știri — ${state.selectedCounty}` : "Știri pe hartă";
    list.replaceChildren();

    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "Nu există știri pentru filtrul ales.";
      list.appendChild(empty);
      return;
    }

    for (const item of items.slice(0, 200)) {
      const link = document.createElement("a");
      link.className = "news-item";
      link.href = articleUrl(item);
      const meta = document.createElement("div");
      meta.className = "news-meta";
      const badge = document.createElement("span");
      badge.className = `badge ${item.category}`;
      badge.textContent = item.category === "local" ? "LOCAL" : "ZONAL";
      const date = document.createElement("span");
      date.textContent = dateLabel(item.published);
      meta.append(badge, date);
      const title = document.createElement("h3");
      title.className = "news-title";
      title.textContent = item.title || "Fără titlu";
      const place = document.createElement("div");
      place.className = "news-place";
      const bits = [item.locality || item.county, item.siruta ? `SIRUTA ${item.siruta}` : ""].filter(Boolean);
      place.textContent = bits.join(" · ");
      link.append(meta, title, place);
      list.appendChild(link);
    }
  }

  function refresh() {
    state.visible = filtered();
    buildMap();
    renderList();
  }

  function selectCounty(county) {
    state.selectedCounty = county;
    refresh();
  }

  async function load() {
    try {
      const response = await fetch(DATA_URL, { cache: "no-store" });
      if (!response.ok) throw new Error(`Datasetul hărții nu este disponibil (${response.status}).`);
      const payload = await response.json();
      if (!payload.map?.viewbox || !payload.map?.judete || !Array.isArray(payload.articles)) {
        throw new Error("Datasetul hărții are o structură invalidă.");
      }
      state.map = payload.map;
      state.counties = payload.map.judete;
      state.articles = payload.articles;
      refresh();
      const stats = payload.stats || {};
      $("#map-stats").innerHTML = `<strong>${Number(stats.total || state.articles.length).toLocaleString("ro-RO")}</strong><span>știri localizate în ${Number(stats.counties || new Set(state.articles.map((item) => item.county)).size).toLocaleString("ro-RO")} județe</span>`;
    } catch (error) {
      $("#map").innerHTML = `<p class="error">Harta nu a putut încărca datele: ${String(error.message || error)}</p>`;
      $("#news-list").innerHTML = `<p class="error">Datasetul hărții nu a fost publicat sau este invalid.</p>`;
      $("#map-stats").innerHTML = "<span>Date indisponibile</span>";
    }
  }

  document.querySelectorAll("[data-level]").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll("[data-level]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.level = button.dataset.level;
    refresh();
  }));

  $("#map-search").addEventListener("input", (event) => {
    state.search = event.target.value;
    refresh();
  });

  $("#clear-selection").addEventListener("click", () => {
    state.selectedCounty = null;
    state.search = "";
    $("#map-search").value = "";
    document.querySelector('[data-level="all"]').classList.add("active");
    document.querySelectorAll("[data-level]:not([data-level=all])").forEach((item) => item.classList.remove("active"));
    state.level = "all";
    refresh();
  });

  load();
})();