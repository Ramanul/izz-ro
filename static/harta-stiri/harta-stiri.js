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

  function buildMap() {
    const host = $("#map");
    host.replaceChildren();
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", state.map.viewbox);
    svg.setAttribute("role", "presentation");

    const counts = new Map();
    for (const item of state.visible) {
      counts.set(item.county, (counts.get(item.county) || 0) + 1);
    }

    const paths = new Map();
    for (const [county, pathData] of Object.entries(state.counties)) {
      const count = counts.get(county) || 0;
      const path = document.createElementNS(svgNS, "path");
      path.setAttribute("d", pathData);
      path.setAttribute("class", `county ${count ? `has-news ${bucket(count)}` : ""}${state.selectedCounty === county ? " selected" : ""}`);
      path.dataset.county = county;
      path.setAttribute("tabindex", "0");
      path.setAttribute("aria-label", `${county}: ${count} știri`);
      path.addEventListener("click", () => selectCounty(count ? county : null));
      path.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectCounty(count ? county : null);
        }
      });
      svg.appendChild(path);
      paths.set(county, path);
    }

    // Attach the SVG before measuring paths. getBBox() is only reliable once
    // the SVG is connected to the document; otherwise headless Chromium can
    // report zero-size boxes and all news markers disappear.
    host.appendChild(svg);

    // Use the browser's parsed SVG geometry rather than parsing path strings.
    // Romanian county boundaries contain H/V/arc/relative commands for which
    // pairing every numeric token as X/Y produces incorrect marker positions.
    for (const [county] of Object.entries(state.counties)) {
      const count = counts.get(county) || 0;
      if (!count) continue;
      const path = paths.get(county);
      const box = path.getBBox();
      if (!Number.isFinite(box.x) || !Number.isFinite(box.y) || box.width <= 0 || box.height <= 0) continue;
      const x = box.x + box.width / 2;
      const y = box.y + box.height / 2;

      const bubble = document.createElementNS(svgNS, "circle");
      bubble.setAttribute("cx", x);
      bubble.setAttribute("cy", y);
      bubble.setAttribute("r", Math.max(7, Math.min(18, 6 + Math.sqrt(count) * 1.8)));
      bubble.setAttribute("class", "count-bubble");
      bubble.setAttribute("aria-hidden", "true");

      const label = document.createElementNS(svgNS, "text");
      label.setAttribute("x", x);
      label.setAttribute("y", y);
      label.setAttribute("class", "count-label");
      label.textContent = String(count);
      label.setAttribute("aria-hidden", "true");
      svg.append(bubble, label);
    }
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

    document.querySelectorAll(".county").forEach((element) => {
      const county = element.dataset.county;
      const hasNews = state.visible.some((item) => item.county === county);
      const query = norm(state.search);
      const matchesSearch = !query || state.visible.some((item) =>
        norm(`${item.county} ${item.locality}`).includes(query));
      element.classList.toggle("dimmed", Boolean(
        (state.selectedCounty && county !== state.selectedCounty) || !hasNews || !matchesSearch,
      ));
      element.classList.toggle("selected", county === state.selectedCounty);
    });
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
