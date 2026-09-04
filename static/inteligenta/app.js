const state = { data: null };

const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
}[char]));

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

function setupLeads() {
  document.getElementById('lead-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const need = String(form.get('need')).trim().toLowerCase();
    const city = String(form.get('city')).trim().toLowerCase();
    const budget = String(form.get('budget'));
    const ranked = state.data.providers.map((provider) => {
      const categoryHit = provider.categories.some((category) => need.includes(category) || category.includes(need)) ? 45 : 0;
      const cityHit = provider.cities.some((item) => item.toLowerCase() === city) ? 30 : 0;
      const budgetHit = provider.budgets.includes(budget) ? 15 : 0;
      return { provider, score: Math.min(100, 10 + categoryHit + cityHit + budgetHit) };
    }).sort((a, b) => b.score - a.score).slice(0, 3);
    document.getElementById('lead-result').innerHTML = ranked.length ? ranked.map(({ provider, score }) => `<div class="iz-result"><strong>${escapeHtml(provider.name)}</strong><div class="iz-score">${score}/100</div><p>${escapeHtml(provider.reason)}</p><span class="iz-muted">${escapeHtml(provider.city)} · ${escapeHtml(provider.contact)}</span></div>`).join('') : '<div class="iz-result">Nu există furnizori în dataset.</div>';
  });
}

function setupBusiness() {
  document.getElementById('business-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const cui = String(new FormData(event.currentTarget).get('cui')).replace(/\s+/g, '').toUpperCase();
    const company = state.data.companies[cui];
    const target = document.getElementById('business-result');
    if (!company) {
      target.innerHTML = '<div class="iz-result">CUI-ul nu există în datasetul demonstrativ. În producție, aici intră adaptorii către sursele publice.</div>';
      return;
    }
    target.innerHTML = `<div class="iz-result"><h3>${escapeHtml(company.name)}</h3><p><strong>${escapeHtml(company.status)}</strong> · ${escapeHtml(company.city)} · ${escapeHtml(company.domain)}</p><div class="iz-grid">${company.changes.map((change) => `<article class="iz-card"><h3>${escapeHtml(change.type)}</h3><p>${escapeHtml(change.text)}</p><span class="iz-muted">${escapeHtml(change.date)} · încredere ${escapeHtml(change.confidence)}%</span></article>`).join('')}</div></div>`;
  });
}

function setupActions() {
  document.getElementById('action-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const text = String(new FormData(event.currentTarget).get('text')).toLowerCase();
    const actions = [];
    if (/salari|tax|impozit|venit/.test(text)) actions.push('Calculează impactul pentru profilul tău');
    if (/lege|ordonan|reglement|guvern|minister/.test(text)) actions.push('Verifică textul oficial și termenul de aplicare');
    if (/achizi|contract|licit|proiect/.test(text)) actions.push('Caută oportunități și contracte similare');
    if (/preț|energie|credit|asigur|rca|locuin/.test(text)) actions.push('Compară ofertele și costul total');
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
