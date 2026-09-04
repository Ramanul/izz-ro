const state = { data: null };
const API_BASE = String(window.IZZ_INTELLIGENCE_API || '/api/intelligence').replace(/\/$/, '');
const SESSION_KEY = 'izz_intelligence_session';

const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
}[char]));

function sessionKey() {
  let value = sessionStorage.getItem(SESSION_KEY);
  if (!value) {
    value = `${crypto.randomUUID()}-${crypto.randomUUID()}`;
    sessionStorage.setItem(SESSION_KEY, value);
  }
  return value;
}

async function apiRequest(path, options = {}) {
  const headers = { accept: 'application/json', ...(options.headers || {}) };
  if (options.body) headers['content-type'] = 'application/json';
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) throw new Error(`API HTTP ${response.status}`);
  return response.json();
}

async function loadData() {
  try {
    const response = await fetch('./data.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    state.data = await response.json();
  } catch (error) {
    state.data = { catalog: [], providers: [], companies: {}, market: [], commerce: [], events: [] };
    console.error('IZZ Intelligence data load failed', error);
  }
  renderAll();
}

function renderAll() {
  document.getElementById('catalog').innerHTML = state.data.catalog.map((item) => `<li><strong>${escapeHtml(item.name)}</strong> — ${escapeHtml(item.value)}</li>`).join('');
  document.getElementById('market-grid').innerHTML = state.data.market.map((item) => `<article class="iz-card"><div class="iz-score">${escapeHtml(item.value)}</div><h3>${escapeHtml(item.label)}</h3><p>${escapeHtml(item.note)}</p></article>`).join('');
  document.getElementById('commerce-grid').innerHTML = state.data.commerce.map((item) => `<article class="iz-card"><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.description)}</p><p class="iz-muted">Model: ${escapeHtml(item.model)}</p></article>`).join('');
  document.getElementById('events-grid').innerHTML = state.data.events.map((item) => `<article class="iz-card"><h3>${escapeHtml(item.name)}</h3><p>${escapeHtml(item.date)} · ${escapeHtml(item.location)}</p><p>${escapeHtml(item.description)}</p></article>`).join('');
}

function setupTabs() {
  document.querySelectorAll('[role="tab"]').forEach((button) => {
    button.addEventListener('click', () => {
      const tab = button.dataset.tab;
      document.querySelectorAll('[role="tab"]').forEach((item) => item.setAttribute('aria-selected', String(item === button)));
      document.querySelectorAll('.iz-panel').forEach((panel) => panel.classList.toggle('active', panel.id === tab));
      history.replaceState(null, '', `#${tab}`);
    });
  });
  const initial = location.hash.slice(1);
  if (initial && document.getElementById(initial)) document.querySelector(`[data-tab="${CSS.escape(initial)}"]`)?.click();
}

function rankLocalLeads(need, city, budget) {
  const normalizedNeed = need.trim().toLowerCase();
  const normalizedCity = city.trim().toLowerCase();
  return state.data.providers.map((provider) => {
    const providerCities = provider.cities ?? (provider.city ? [provider.city] : []);
    const categoryHit = provider.categories.some((category) => normalizedNeed.includes(category.toLowerCase()) || category.toLowerCase().includes(normalizedNeed)) ? 45 : 0;
    const cityHit = providerCities.some((item) => item.toLowerCase() === normalizedCity) ? 30 : 0;
    const budgetHit = provider.budgets.includes(budget) ? 15 : 0;
    return { provider, score: Math.min(100, 10 + categoryHit + cityHit + budgetHit) };
  }).sort((a, b) => b.score - a.score).slice(0, 3);
}

function renderLeadMatches(matches) {
  document.getElementById('lead-result').innerHTML = matches.length
    ? matches.map((match) => `<div class="iz-result"><strong>${escapeHtml(match.name || match.provider?.name)}</strong><div class="iz-score">${escapeHtml(match.score)}/100</div><p>${escapeHtml(match.reason || match.provider?.reason || 'Potrivire pe baza intenției declarate.')}</p><span class="iz-muted">${escapeHtml(match.city || match.provider?.city || '')} · ${escapeHtml(match.contact || match.provider?.contact || '')}${match.verified ? ' · verificat' : ''}</span></div>`).join('')
    : '<div class="iz-result">Nu există furnizori potriviți în dataset.</div>';
}

function setupLeads() {
  document.getElementById('lead-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const need = String(form.get('need')).trim();
    const city = String(form.get('city')).trim();
    const budget = String(form.get('budget'));
    try {
      const result = await apiRequest('/leads', {
        method: 'POST',
        headers: { 'x-izz-session': sessionKey() },
        body: JSON.stringify({ need, city, budget, session_key: sessionKey() }),
      });
      renderLeadMatches(result.matches || []);
    } catch (_) {
      renderLeadMatches(rankLocalLeads(need.toLowerCase(), city.toLowerCase(), budget).map(({ provider, score }) => ({ provider, score })));
    }
  });
}

async function renderBusiness(cui) {
  const localCompany = state.data.companies[cui];
  try {
    const result = await apiRequest(`/company?cui=${encodeURIComponent(cui)}`);
    if (result.data) {
      const company = result.data;
      document.getElementById('business-result').innerHTML = `<div class="iz-result"><h3>${escapeHtml(company.canonical_name)}</h3><p>${escapeHtml(company.city || '')} · CUI ${escapeHtml(company.external_key || cui)}</p><div class="iz-grid">${(company.changes || []).map((change) => `<article class="iz-card"><h3>${escapeHtml(change.type)}</h3><p>${escapeHtml(change.title)}</p><span class="iz-muted">${escapeHtml(change.published_at || change.observed_at || '')} · încredere ${escapeHtml(change.confidence)}%</span></article>`).join('')}</div></div>`;
      return;
    }
  } catch (_) {}
  if (localCompany) {
    document.getElementById('business-result').innerHTML = `<div class="iz-result"><h3>${escapeHtml(localCompany.name)}</h3><p><strong>${escapeHtml(localCompany.status)}</strong> · ${escapeHtml(localCompany.city)} · ${escapeHtml(localCompany.domain)}</p><div class="iz-grid">${localCompany.changes.map((change) => `<article class="iz-card"><h3>${escapeHtml(change.type)}</h3><p>${escapeHtml(change.text)}</p><span class="iz-muted">${escapeHtml(change.date)} · încredere ${escapeHtml(change.confidence)}%</span></article>`).join('')}</div></div>`;
  } else {
    document.getElementById('business-result').innerHTML = '<div class="iz-result">Compania nu există în datele locale. Pentru producție, conectează un dataset public în D1.</div>';
  }
}

function setupBusiness() {
  document.getElementById('business-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const cui = String(new FormData(event.currentTarget).get('cui')).replace(/\s+/g, '').toUpperCase();
    renderBusiness(cui);
  });
}

async function setupActions() {
  document.getElementById('action-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const text = String(new FormData(event.currentTarget).get('text'));
    try {
      const result = await apiRequest('/actions', { method: 'POST', body: JSON.stringify({ text }) });
      document.getElementById('action-result').innerHTML = `<div class="iz-result"><strong>Următorii pași</strong><ul class="iz-list">${(result.actions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div>`;
      return;
    } catch (_) {}
    const value = text.toLowerCase();
    const actions = [];
    if (/salari|tax|impozit|venit/.test(value)) actions.push('Calculează impactul pentru profilul tău');
    if (/lege|ordonan|reglement|guvern|minister/.test(value)) actions.push('Verifică textul oficial și termenul de aplicare');
    if (/achizi|contract|licit|proiect/.test(value)) actions.push('Caută oportunități și contracte similare');
    if (/preț|energie|credit|asigur|rca|locuin/.test(value)) actions.push('Compară ofertele și costul total');
    if (!actions.length) actions.push('Salvează subiectul și activează o alertă de schimbare');
    document.getElementById('action-result').innerHTML = `<div class="iz-result"><strong>Următorii pași</strong><ul class="iz-list">${actions.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul></div>`;
  });
}

function setupTool() {
  const calculate = () => {
    const gross = Math.max(0, Number(document.getElementById('gross').value) || 0);
    const type = document.getElementById('calc-type').value;
    const value = type === 'annual' ? gross * 12 : gross * 0.585;
    const label = type === 'annual' ? 'brut anual estimat' : 'net estimat (model orientativ)';
    document.getElementById('tool-result').innerHTML = `<div class="iz-score">${Math.round(value).toLocaleString('ro-RO')} lei</div><strong>${label}</strong><p class="iz-muted">Calculatorul este orientativ; regulile fiscale complete trebuie furnizate de un motor fiscal verificat înainte de producție.</p>`;
  };
  document.getElementById('calc-btn').addEventListener('click', calculate);
  calculate();
}

document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupLeads();
  setupBusiness();
  setupActions();
  setupTool();
  loadData();
});
