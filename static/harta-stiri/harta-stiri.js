(() => {
  "use strict";

  const DATA = {
    map: "../../data/harta_judete.json",
    articles: "../../data/articles.json",
    siruta: "../../data/siruta_raw.csv",
  };
  const MAX_ARTICLES = 1500;

  const $ = (s) => document.querySelector(s);
  const norm = (s) => (s || "")
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .toUpperCase().replace(/[^A-Z0-9]+/g, " ").trim();

  const state = {
    map: null,
    counties: {},
    articles: [],
    visible: [],
    selectedCounty: null,
    level: "all",
    search: "",
    sirutaByName: new Map(),
  };

  function csvRows(text) {
    const delimiter = (text.split(/\r?\n/, 1)[0].match(/;/g) || []).length >=
      (text.split(/\r?\n/, 1)[0].match(/,/g) || []).length ? ";" : ",";
    const rows = [];
    let row = [], cell = "", quoted = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (c === '"') {
        if (quoted && text[i + 1] === '"') { cell += '"'; i++; }
        else quoted = !quoted;
      } else if (c === delimiter && !quoted) {
        row.push(cell); cell = "";
      } else if ((c === "\n" || c === "\r") && !quoted) {
        if (c === "\r" && text[i + 1] === "\n") i++;
        row.push(cell); rows.push(row); row = []; cell = "";
      } else cell += c;
    }
    if (cell || row.length) { row.push(cell); rows.push(row); }
    return { rows, delimiter };
  }

  function sirutaIndex(text) {
    const { rows } = csvRows(text);
    if (!rows.length) return new Map();
    const h = rows[0].map(norm);
    const idx = (names) => names.map(norm).map(x => h.indexOf(x)).find(i => i >= 0);
    const iCode = idx(["SIRUTA", "COD SIRUTA", "COD_SIRUTA", "CODSIRUTA"]);
    const iName = idx(["LOCALITATE", "DENUMIRE", "DENUMIRE LOCALITATE", "LOCALITATEA"]);
    const iCounty = idx(["JUDET", "JUDETUL", "JUDEȚ", "JUDEȚUL"]);
    if (iName == null || iCounty == null) return new Map();

    const out = new Map();
    for (const r of rows.slice(1)) {
      const name = norm(r[iName]);
      if (!name || name.length < 4) continue;
      const county = norm(r[iCounty]);
      const rec = { siruta: iCode == null ? "" : String(r[iCode] || "").trim(), county, name };
      const list = out.get(name) || [];
      list.push(rec);
      out.set(name, list);
    }
    return out;
  }

  function countyFromSource(source) {
    const s = norm(source);
    if (!s) return null;
    // Local government / county feeds encode the county in their stable source key.
    const keys = Object.keys(state.counties).sort((a, b) => b.length - a.length);
    return keys.find(c => s.includes(c)) || null;
  }

  function explicitCounty(text) {
    const t = norm(text);
    const keys = Object.keys(state.counties).sort((a, b) => b.length - a.length);
    for (const c of keys) {
      const re = new RegExp(`(?:JUDETUL|JUDETULUI|JUDETELE|JUDET|JUD\\.)\\s+${c}\\b`);
      if (re.test(t)) return c;
    }
    return keys.find(c => new RegExp(`\\b${c}\\b`).test(t)) || null;
  }

  function localityFromText(text, sourceCounty) {
    const t = ` ${norm(text)} `;
    const candidates = [];
    for (const [name, recs] of state.sirutaByName.entries()) {
      if (name.length < 5) continue;
      if (!t.includes(` ${name} `)) continue;
      const same = sourceCounty ? recs.filter(r => r.county.includes(sourceCounty) || sourceCounty.includes(r.county)) : recs;
      const unique = same.length === 1 ? same[0] : null;
      if (unique) candidates.push(unique);
    }
    candidates.sort((a, b) => b.name.length - a.name.length);
    return candidates[0] || null;
  }

  function locateArticle(a) {
    if (!a || !["local", "zonal"].includes(a.category)) return null;
    const text = [a.title, a.teaser, a.synthesis].filter(Boolean).join(" ");
    const sourceCounty = countyFromSource(a.source);
    const textCounty = explicitCounty(text);
    const county = textCounty || sourceCounty;
    const locality = localityFromText(text, county);
    const finalCounty = county || (locality && locality.county);
    if (!finalCounty || !state.counties[finalCounty]) return null;
    return {
      article: a,
      county: finalCounty,
      locality: locality ? locality.name : "",
      siruta: locality ? locality.siruta : "",
      confidence: textCounty ? "text" : sourceCounty ? "source" : locality ? "siruta" : "none",
    };
  }

  function articleUrl(a) {
    return `../../${encodeURIComponent(a.category)}/${encodeURIComponent(a.slug)}/`;
  }

  function dateLabel(value) {
    if (!value) return "";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "";
    return new Intl.DateTimeFormat("ro-RO", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(d);
  }

  function pathCenter(d) {
    const nums = (d.match(/-?\d+(?:\.\d+)?/g) || []).map(Number);
    if (nums.length < 4) return [0, 0];
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (let i = 0; i + 1 < nums.length; i += 2) {
      minX = Math.min(minX, nums[i]); maxX = Math.max(maxX, nums[i]);
      minY = Math.min(minY, nums[i + 1]); maxY = Math.max(maxY, nums[i + 1]);
    }
    return [(minX + maxX) / 2, (minY + maxY) / 2];
  }

  function bucket(count) {
    if (!count) return "none";
    if (count >= 20) return "high";
    if (count >= 10) return "medium";
    return "low";
  }

  function buildMap() {
    const host = $("#map");
    host.replaceChildren();
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", state.map.viewbox);
    svg.setAttribute("role", "presentation");

    const counts = new Map();
    for (const item of state.visible) counts.set(item.county, (counts.get(item.county) || 0) + 1);

    for (const [county, d] of Object.entries(state.counties)) {
      const path = document.createElementNS(svgNS, "path");
      const count = counts.get(county) || 0;
      path.setAttribute("d", d);
      path.setAttribute("class", `county ${count ? `has-news ${bucket(count)}` : ""}${state.selectedCounty === county ? " selected" : ""}`);
      path.dataset.county = county;
      path.setAttribute("tabindex", "0");
      path.setAttribute("aria-label", `${county}: ${count} știri`);
      path.addEventListener("click", () => selectCounty(count ? county : null));
      path.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectCounty(count ? county : null); } });
      svg.appendChild(path);
    }

    for (const [county, d] of Object.entries(state.counties)) {
      const count = counts.get(county) || 0;
      if (!count) continue;
      const [x, y] = pathCenter(d);
      const circle = document.createElementNS(svgNS, "circle");
      circle.setAttribute("cx", x); circle.setAttribute("cy", y); circle.setAttribute("r", Math.max(7, Math.min(18, 6 + Math.sqrt(count) * 1.8)));
      circle.setAttribute("class", "count-bubble");
      const label = document.createElementNS(svgNS, "text");
      label.setAttribute("x", x); label.setAttribute("y", y); label.setAttribute("class", "count-label");
      label.textContent = String(count);
      svg.append(circle, label);
    }
    host.appendChild(svg);
  }

  function filtered() {
    const q = norm(state.search);
    return state.articles.filter(item => {
      if (state.level !== "all" && item.article.category !== state.level) return false;
      if (state.selectedCounty && item.county !== state.selectedCounty) return false;
      if (!q) return true;
      const hay = norm([item.article.title, item.locality, item.county, item.article.source].join(" "));
      return hay.includes(q);
    });
  }

  function renderList() {
    const list = $("#news-list");
    const items = filtered();
    $("#panel-count").textContent = `${items.length} știri`;
    $("#panel-title").textContent = state.selectedCounty ? `Știri — ${state.selectedCounty}` : "Știri pe hartă";
    list.replaceChildren();
    if (!items.length) {
      const p = document.createElement("p"); p.className = "empty"; p.textContent = "Nu există știri pentru filtrul ales."; list.appendChild(p); return;
    }
    for (const item of items.slice(0, 200)) {
      const a = document.createElement("a"); a.className = "news-item"; a.href = articleUrl(item.article);
      const meta = document.createElement("div"); meta.className = "news-meta";
      const badge = document.createElement("span"); badge.className = `badge ${item.article.category}`; badge.textContent = item.article.category === "local" ? "LOCAL" : "ZONAL";
      const date = document.createElement("span"); date.textContent = dateLabel(item.article.published);
      meta.append(badge, date);
      const title = document.createElement("h3"); title.className = "news-title"; title.textContent = item.article.title || "Fără titlu";
      const place = document.createElement("div"); place.className = "news-place";
      const bits = [item.locality || item.county, item.siruta ? `SIRUTA ${item.siruta}` : ""].filter(Boolean);
      place.textContent = bits.join(" · ");
      a.append(meta, title, place); list.appendChild(a);
    }
  }

  function applyDim() {
    document.querySelectorAll(".county").forEach(el => {
      const county = el.dataset.county;
      const has = state.visible.some(x => x.county === county);
      const q = norm(state.search);
      const matchesSearch = !q || state.visible.some(x => x.county === county || x.locality === q);
      el.classList.toggle("dimmed", !!(state.selectedCounty && county !== state.selectedCounty) || !has || !matchesSearch);
      el.classList.toggle("selected", county === state.selectedCounty);
    });
  }

  function selectCounty(county) {
    state.selectedCounty = county;
    renderList();
    buildMap();
    applyDim();
  }

  function refresh() {
    state.visible = filtered();
    buildMap();
    renderList();
    applyDim();
    const all = state.articles.length;
    const counties = new Set(state.articles.map(x => x.county)).size;
    $("#map-stats").innerHTML = `<strong>${all.toLocaleString("ro-RO")}</strong><span>știri localizate în ${counties} județe</span>`;
  }

  async function load() {
    try {
      const [mapRes, artRes, sirutaRes] = await Promise.all([
        fetch(DATA.map, { cache: "no-store" }),
        fetch(DATA.articles, { cache: "no-store" }),
        fetch(DATA.siruta, { cache: "no-store" }),
      ]);
      if (!mapRes.ok || !artRes.ok || !sirutaRes.ok) throw new Error("Nu toate sursele de date sunt disponibile.");
      state.map = await mapRes.json();
      state.counties = state.map.judete || {};
      const articles = await artRes.json();
      const sirutaText = await sirutaRes.text();
      state.sirutaByName = sirutaIndex(sirutaText);

      const raw = Array.isArray(articles) ? articles : (articles.articles || articles.items || []);
      raw.sort((a, b) => String(b.published || "").localeCompare(String(a.published || "")));
      for (const a of raw.slice(0, MAX_ARTICLES)) {
        const located = locateArticle(a);
        if (located) state.articles.push(located);
      }
      refresh();
    } catch (err) {
      $("#map").innerHTML = `<p class="error">Harta nu a putut încărca datele: ${String(err.message || err)}</p>`;
      $("#news-list").innerHTML = `<p class="error">Verifică disponibilitatea fișierelor de date și încearcă din nou.</p>`;
      $("#map-stats").innerHTML = "<span>Date indisponibile</span>";
    }
  }

  document.querySelectorAll("[data-level]").forEach(btn => btn.addEventListener("click", () => {
    document.querySelectorAll("[data-level]").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    state.level = btn.dataset.level;
    refresh();
  }));
  $("#map-search").addEventListener("input", (e) => { state.search = e.target.value; refresh(); });
  $("#clear-selection").addEventListener("click", () => { state.selectedCounty = null; $("#map-search").value = ""; state.search = ""; refresh(); });

  load();
})();
