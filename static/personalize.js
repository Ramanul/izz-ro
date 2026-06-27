/* IZZ.ro Personalization Engine — client-side only, localStorage, zero PII */
(function () {
  'use strict';

  const KEY = 'izz_profile_v1';
  const HALF_LIFE_MS = 7 * 24 * 3600 * 1000;
  const MIN_INTERACTIONS = 5;
  const STOP_WORDS = new Set(['si','sau','in','la','de','cu','pe','un','o','nu','se','ca','din','ale','ale','cel','cea','cei','cele','este','sunt','fost','care','prin','dupa','este','mai','dar','daca','tot','astfel','insa','chiar','doar','iar','despre','acest','acestei','aceasta','acesta','sa','au','al','ai','am','ar','fi','vor','va','poate','orice']);

  /* ---- storage ---- */
  function load() {
    try { return JSON.parse(localStorage.getItem(KEY)) || empty(); }
    catch { return empty(); }
  }
  function save(p) {
    try { localStorage.setItem(KEY, JSON.stringify(p)); } catch {}
  }
  function empty() {
    return { cats: {}, sources: {}, keywords: {}, reads: 0, totalTime: 0, interactions: 0 };
  }

  /* ---- decay: score × 0.5^(age/half_life) ---- */
  function decayed(signals, now) {
    const out = {};
    for (const [k, v] of Object.entries(signals || {})) {
      const score = (v.score || 0) * Math.pow(0.5, (now - (v.ts || now)) / HALF_LIFE_MS);
      if (score > 0.01) out[k] = { score, ts: v.ts || now };
    }
    return out;
  }

  function bump(map, key, delta, now) {
    const cur = map[key] || { score: 0, ts: now };
    map[key] = { score: (cur.score || 0) + delta, ts: now };
  }

  /* ---- keywords from title ---- */
  function keywords(title) {
    return (title || '').toLowerCase()
      .replace(/[^a-zăâîșțáéíóú\s-]/gi, ' ')
      .split(/\s+/)
      .filter(w => w.length > 3 && !STOP_WORDS.has(w));
  }

  /* ---- track a card click ---- */
  function trackClick(category, source, title) {
    const p = load();
    const now = Date.now();
    p.cats    = decayed(p.cats,    now);
    p.sources = decayed(p.sources, now);
    p.keywords= decayed(p.keywords,now);
    bump(p.cats,    category, 3, now);
    bump(p.sources, source,   2, now);
    keywords(title).forEach(w => bump(p.keywords, w, 1, now));
    p.interactions = (p.interactions || 0) + 1;
    save(p);
  }

  /* ---- track read time (called from article page) ---- */
  function trackTime(seconds) {
    const p = load();
    p.reads    = (p.reads    || 0) + 1;
    p.totalTime= (p.totalTime|| 0) + seconds;
    if (seconds > 30) {
      const now = Date.now();
      const cat = document.body.dataset.category;
      const src = document.body.dataset.source;
      const ttl = document.body.dataset.title;
      if (cat) bump(p.cats    = decayed(p.cats,    now), cat, 2, now);
      if (src) bump(p.sources = decayed(p.sources, now), src, 1, now);
      if (ttl) keywords(ttl).forEach(w => bump(p.keywords = decayed(p.keywords, now), w, 0.5, now));
    }
    save(p);
  }

  /* ---- score an article element ---- */
  function scoreArticle(el, p, now) {
    const cat  = el.dataset.cat   || '';
    const src  = el.dataset.src   || '';
    const kws  = keywords(el.dataset.title || '');
    const dCats = decayed(p.cats,     now);
    const dSrcs = decayed(p.sources,  now);
    const dKws  = decayed(p.keywords, now);
    const catS  = (dCats[cat]?.score || 0);
    const srcS  = (dSrcs[src]?.score || 0);
    const kwS   = kws.reduce((s, w) => s + (dKws[w]?.score || 0), 0) / Math.max(kws.length, 1);
    return 0.4 * catS + 0.3 * srcS + 0.3 * kwS;
  }

  /* ---- render "Pentru tine" section ---- */
  function renderForYou() {
    const p = load();
    if ((p.interactions || 0) < MIN_INTERACTIONS) return;
    const now = Date.now();

    const cards = Array.from(document.querySelectorAll('.grid .card[data-cat]'));
    if (cards.length < 3) return;

    const scored = cards
      .map(el => ({ el, score: scoreArticle(el, p, now) }))
      .filter(x => x.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 6);

    if (scored.length < 2) return;

    const section = document.createElement('section');
    section.id = 'pentru-tine';
    section.innerHTML = '<h2 class="section-title pt-title">Pentru tine <span class="pt-badge">personalizat</span></h2>';
    const grid = document.createElement('div');
    grid.className = 'grid';
    scored.forEach(({ el }) => grid.appendChild(el.cloneNode(true)));
    section.appendChild(grid);

    const main = document.querySelector('main');
    const firstGrid = main && main.querySelector('.grid');
    if (!firstGrid) return;
    main.insertBefore(section, firstGrid);
    rewireClicks(section);
  }

  /* ---- reorder nav by preference ---- */
  function reorderNav() {
    const p = load();
    if ((p.interactions || 0) < MIN_INTERACTIONS) return;
    const now = Date.now();
    const nav = document.querySelector('.nav');
    if (!nav) return;
    const links = Array.from(nav.querySelectorAll('a[href]'));
    links.sort((a, b) => {
      const catA = a.textContent.trim().toLowerCase();
      const catB = b.textContent.trim().toLowerCase();
      const sA = (decayed(p.cats, now)[catA]?.score || 0);
      const sB = (decayed(p.cats, now)[catB]?.score || 0);
      return sB - sA;
    });
    links.forEach(l => nav.appendChild(l));
  }

  /* ---- wire click tracking on cards ---- */
  function rewireClicks(root) {
    (root || document).querySelectorAll('.card[data-cat] .read-more, .card[data-cat] .card-title a').forEach(a => {
      a.addEventListener('click', () => {
        const card = a.closest('[data-cat]');
        if (card) trackClick(card.dataset.cat, card.dataset.src, card.dataset.title || '');
      });
    });
  }

  /* ---- stats panel ---- */
  function buildStatsPanel() {
    const p = load();
    const now = Date.now();
    const cats = decayed(p.cats, now);
    const sources = decayed(p.sources, now);
    const keywords = decayed(p.keywords, now);

    const topCats = Object.entries(cats).sort((a,b) => b[1].score - a[1].score).slice(0, 5);
    const topSrc  = Object.entries(sources).sort((a,b) => b[1].score - a[1].score).slice(0, 5);
    const topKws  = Object.entries(keywords).sort((a,b) => b[1].score - a[1].score).slice(0, 10);
    const avgTime = p.reads ? Math.round(p.totalTime / p.reads) : 0;
    const catTotal = topCats.reduce((s, [,v]) => s + v.score, 0) || 1;

    const panel = document.createElement('div');
    panel.id = 'izz-stats';
    panel.innerHTML = `
      <div class="stats-backdrop"></div>
      <div class="stats-box" role="dialog" aria-label="Profilul tău de cititor">
        <div class="stats-header">
          <span class="stats-title">Profilul tău</span>
          <button class="stats-close" aria-label="Închide">✕</button>
        </div>
        <div class="stats-body">
          <div class="stats-row">
            <span class="stats-num">${p.interactions || 0}</span><span class="stats-lbl">interacțiuni</span>
            <span class="stats-num">${p.reads || 0}</span><span class="stats-lbl">articole citite</span>
            <span class="stats-num">${avgTime}s</span><span class="stats-lbl">timp mediu</span>
          </div>
          ${topCats.length ? `
          <h3 class="stats-section">Categorii preferate</h3>
          <div class="stats-bars">
            ${topCats.map(([cat, v]) => `
              <div class="bar-row">
                <span class="bar-label">${cat}</span>
                <div class="bar-track"><div class="bar-fill" style="width:${Math.round(v.score/catTotal*100)}%"></div></div>
                <span class="bar-pct">${Math.round(v.score/catTotal*100)}%</span>
              </div>`).join('')}
          </div>` : ''}
          ${topSrc.length ? `
          <h3 class="stats-section">Surse favorite</h3>
          <ul class="stats-list">${topSrc.map(([src]) => `<li>${src}</li>`).join('')}</ul>` : ''}
          ${topKws.length ? `
          <h3 class="stats-section">Topicuri frecvente</h3>
          <div class="stats-tags">${topKws.map(([w]) => `<span class="tag">${w}</span>`).join('')}</div>` : ''}
          <button class="stats-reset">Resetează preferințele</button>
          ${!p.interactions || p.interactions < MIN_INTERACTIONS
            ? `<p class="stats-hint">Mai citește ${MIN_INTERACTIONS - (p.interactions||0)} articol${(MIN_INTERACTIONS - (p.interactions||0)) === 1 ? '' : 'e'} pentru a activa secțiunea „Pentru tine".</p>`
            : ''}
        </div>
      </div>`;

    panel.querySelector('.stats-close').onclick = () => panel.remove();
    panel.querySelector('.stats-backdrop').onclick = () => panel.remove();
    panel.querySelector('.stats-reset').onclick = () => {
      localStorage.removeItem(KEY);
      panel.remove();
      document.getElementById('pentru-tine')?.remove();
    };
    document.body.appendChild(panel);
  }

  /* ---- stats trigger button ---- */
  function addStatsButton() {
    const btn = document.createElement('button');
    btn.className = 'izz-profile-btn';
    btn.title = 'Profilul tău de cititor';
    btn.textContent = '◎';
    btn.onclick = buildStatsPanel;
    document.body.appendChild(btn);
  }

  /* ---- article page: track time ---- */
  function initArticlePage() {
    if (!document.querySelector('.article')) return;
    const start = Date.now();
    window.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'hidden') {
        trackTime(Math.round((Date.now() - start) / 1000));
      }
    });
    window.addEventListener('pagehide', () => {
      trackTime(Math.round((Date.now() - start) / 1000));
    });
  }

  /* ---- init ---- */
  function init() {
    rewireClicks();
    renderForYou();
    reorderNav();
    addStatsButton();
    initArticlePage();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();
