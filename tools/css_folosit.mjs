#!/usr/bin/env node
/**
 * tools/css_folosit.mjs — cat din `static/styles.css` e exercitat efectiv de o pagina.
 *
 * Dimensiunea 5 (specs/dimensiunea-5-greutate.md) a masurat CAT cantareste o pagina.
 * Asta masoara ALTCEVA: din cei ~51 KB de CSS, ce parte atinge o pagina de articol.
 *
 * De ce nu e un singur procent: o regula neatinsa la prima randare nu e o regula moarta.
 * Poate fi pentru tema intunecata, pentru panoul de personalizare injectat din JS, pentru
 * un breakpoint mobil, sau pentru hover. Unealta conduce STARILE alea explicit si le
 * raporteaza separat. Doar ultima galeata — "neatins de nicio stare" — e actionabila,
 * si nici aia nu inseamna "mort": inseamna "neexercitat de starile conduse aici".
 *
 * Metoda: Chrome DevTools Protocol, `CSS.startRuleUsageTracking` + `takeCoverageDelta`,
 * care raporteaza regulile devenite folosite de la ultimul apel — deci atribuirea pe stari
 * e a protocolului, nu a mea. Contabilitatea e pe OCTETI de regula, ca sa fie comparabila
 * cu restul dimensiunii 5.
 *
 *   node tools/css_folosit.mjs                     # esantion implicit din output/
 *   node tools/css_folosit.mjs --json raport.json  # + raport masinabil
 *   node tools/css_folosit.mjs /cat/slug/ /alta/   # pagini anume
 */

import { createServer } from 'node:http';
import { readFile, readdir, stat } from 'node:fs/promises';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { extname, join, resolve } from 'node:path';
import { gzipSync } from 'node:zlib';

const RADACINA = resolve(new URL('..', import.meta.url).pathname);
const OUTPUT = join(RADACINA, 'output');
const CSS_SURSA = join(RADACINA, 'static', 'styles.css');
const PORT = Number(process.env.PORT_CSS || 8399);

/* ------------------------------------------------------------------ unelte --- */

/** Aceeasi cautare ca in tools/audit.sh: containerul de cloud tine Chromium sub /opt. */
function gasesteChromium() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const candidati = [
    '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
    '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome',
  ];
  for (const c of candidati) if (existsSync(c)) return c;
  // ultima incercare: orice chromium-* din bundle-ul Playwright
  try {
    const dirs = readdirSync('/opt/pw-browsers');
    for (const d of dirs) {
      const p = `/opt/pw-browsers/${d}/chrome-linux/chrome`;
      if (existsSync(p)) return p;
    }
  } catch { /* nu exista dosarul: cadem pe eroarea de mai jos */ }
  throw new Error(
    'Nu gasesc un binar Chromium. Da-i calea prin CHROME_PATH=... (vezi tools/audit.sh).'
  );
}

/** Playwright e instalat global (node22), nu ca dependenta de proiect. */
async function importaPlaywright() {
  for (const cale of [
    'playwright',
    '/opt/node22/lib/node_modules/playwright/index.mjs',
  ]) {
    try { return await import(cale); } catch { /* incearca urmatoarea cale */ }
  }
  throw new Error('Playwright lipseste. Instaleaza: npm i -g playwright');
}

const TIPURI = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
  '.png': 'image/png', '.webp': 'image/webp', '.woff2': 'font/woff2',
  '.xml': 'application/xml', '.txt': 'text/plain; charset=utf-8',
};

/** Server static minimal peste output/. Fara dependente: e nevoie doar de GET. */
function servesteOutput(dir, port) {
  const srv = createServer(async (req, res) => {
    try {
      let cale = decodeURIComponent(req.url.split('?')[0]);
      let fisier = join(dir, cale);
      if (!fisier.startsWith(dir)) { res.writeHead(403).end(); return; }   // path traversal
      try {
        if ((await stat(fisier)).isDirectory()) fisier = join(fisier, 'index.html');
      } catch { /* nu exista ca dosar: incercam ca fisier mai jos */ }
      const buf = await readFile(fisier);
      res.writeHead(200, { 'content-type': TIPURI[extname(fisier)] || 'application/octet-stream' });
      res.end(buf);
    } catch {
      res.writeHead(404, { 'content-type': 'text/plain' }).end('404');
    }
  });
  return new Promise((ok, nu) => {
    srv.on('error', nu);
    srv.listen(port, '127.0.0.1', () => ok(srv));
  });
}

/* ------------------------------------------------------- parser de reguli --- */

/**
 * Imparte CSS-ul in reguli, cu offset-urile lor in octeti, si atribuie fiecare regula
 * sectiunii din care face parte (comentariile de sectiune din styles.css).
 *
 * Nu e un parser CSS general: sare peste comentarii si stringuri si numara acolade.
 * Verificat pe styles.css: 0 acolade in comentarii, 0 acolade in stringuri, iar singurele
 * at-rule-uri cu corp imbricat sunt @media (6) si @keyframes (1). Daca fisierul creste
 * altfel, `--verifica` de mai jos pica: suma octetilor nu mai da fisierul intreg.
 */
function parseazaReguli(text) {
  const reguli = [];
  const sectiuni = [];
  let sectiuneCurenta = '(fara sectiune)';
  let i = 0, inceputSelector = 0, adancime = 0, inceputBlocMedia = null, prefixMedia = null;

  const esteSpatiu = (c) => c === ' ' || c === '\t' || c === '\n' || c === '\r';

  while (i < text.length) {
    const c = text[i];

    if (c === '/' && text[i + 1] === '*') {
      const fin = text.indexOf('*/', i + 2);
      const corp = text.slice(i + 2, fin === -1 ? text.length : fin);
      // comentariu de sectiune: "---- Nume ---" sau bannerul "===" de la inceput
      const m = corp.match(/-{3,}\s*([^-]{2,60}?)\s*-{3,}/);
      if (m && adancime === 0) {
        sectiuneCurenta = m[1].trim();
        sectiuni.push({ nume: sectiuneCurenta, offset: i });
      }
      i = fin === -1 ? text.length : fin + 2;
      if (adancime === 0) inceputSelector = i;
      continue;
    }
    if (c === '"' || c === "'") {
      const ghilimea = c;
      i++;
      while (i < text.length && text[i] !== ghilimea) i += (text[i] === '\\' ? 2 : 1);
      i++;
      continue;
    }
    if (c === '{') {
      if (adancime === 0) {
        const selector = text.slice(inceputSelector, i).trim();
        if (/^@(media|supports|keyframes|layer)/.test(selector)) {
          // Container. CDP raporteaza SEPARAT preambulul lui („@media (...) {") si fiecare
          // regula dinauntru, deci il inregistram si pe el — altfel offset-ul preambulului
          // ajunge „necunoscut" si octetii lui nu se contabilizeaza nicaieri.
          const brutC = text.slice(inceputSelector, i + 1);
          reguli.push({
            start: inceputSelector + (brutC.length - brutC.trimStart().length),
            end: i + 1, selector, sectiune: sectiuneCurenta, media: null, container: true,
          });
          inceputBlocMedia = i;
          prefixMedia = selector;
          adancime = 1;
          inceputSelector = i + 1;
          i++;
          continue;
        }
        adancime = 1;
        i++;
        continue;
      }
      adancime++;
      i++;
      continue;
    }
    if (c === '}') {
      adancime--;
      if (adancime === 0) {
        const selector = text.slice(inceputSelector, i).trim();
        // regula normala de nivel 0, sau ultima regula dintr-un @media
        if (prefixMedia === null) {
          const brut = text.slice(inceputSelector, i + 1);
          const sel = brut.slice(0, brut.indexOf('{')).trim();
          if (sel) reguli.push({
            start: inceputSelector + (brut.length - brut.trimStart().length),
            end: i + 1, selector: sel, sectiune: sectiuneCurenta, media: null,
          });
        } else {
          // s-a inchis @media: inchidem containerul
          prefixMedia = null;
          inceputBlocMedia = null;
        }
        inceputSelector = i + 1;
        while (inceputSelector < text.length && esteSpatiu(text[inceputSelector])) inceputSelector++;
        i++;
        continue;
      }
      if (adancime === 1 && prefixMedia !== null) {
        // s-a inchis o regula din interiorul unui @media
        const brut = text.slice(inceputSelector, i + 1);
        const taiere = brut.indexOf('{');
        const sel = taiere === -1 ? '' : brut.slice(0, taiere).trim();
        if (sel) reguli.push({
          start: inceputSelector + (brut.length - brut.trimStart().length),
          end: i + 1, selector: sel, sectiune: sectiuneCurenta, media: prefixMedia,
        });
        inceputSelector = i + 1;
        while (inceputSelector < text.length && esteSpatiu(text[inceputSelector])) inceputSelector++;
      }
      i++;
      continue;
    }
    i++;
  }
  return { reguli, sectiuni };
}

export { parseazaReguli };

/* --------------------------------------------------------- driverul de stari --- */

/** Plimba mouse-ul real peste tinte (`:hover` NU raspunde la evenimente sintetice). */
async function treciCuMouse(page, limita = 40) {
  const cutii = await page.evaluate((lim) => {
    const sel = 'a,button,summary,input,select,textarea,[tabindex],label,li,article,.card,.badge';
    const out = [];
    for (const el of document.querySelectorAll(sel)) {
      const r = el.getBoundingClientRect();
      if (r.width > 2 && r.height > 2 && r.top >= 0 && r.top < window.innerHeight) {
        out.push([r.left + r.width / 2, r.top + r.height / 2]);
        if (out.length >= lim) break;
      }
    }
    return out;
  }, limita);
  for (const [x, y] of cutii) await page.mouse.move(x, y);
}

/** Tab-uri reale: `:focus-visible` se aplica la navigare cu tastatura, nu la .focus(). */
async function plimbaFocusul(page, pasi = 25) {
  for (let i = 0; i < pasi; i++) await page.keyboard.press('Tab');
}

const STARI = [
  {
    id: 'S0', nume: 'prima randare',
    async condu(page) { await page.waitForTimeout(400); },
  },
  {
    id: 'S1', nume: 'personalizare (consimtamant + panou)',
    async condu(page) {
      // bara de consimtamant e injectata din personalize.js; butonul profil apare dupa
      for (const sel of ['.consent-yes', '.izz-profile-btn']) {
        const el = await page.$(sel);
        if (el) { await el.click({ timeout: 2000 }).catch(() => {}); await page.waitForTimeout(300); }
      }
      await page.evaluate(() => document.querySelectorAll('details').forEach((d) => (d.open = true)));
      await page.waitForTimeout(200);
    },
  },
  {
    id: 'S2', nume: 'derulare pana jos',
    async condu(page) {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(600);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(200);
    },
  },
  {
    id: 'S3', nume: 'hover / focus',
    async condu(page) { await treciCuMouse(page); await plimbaFocusul(page); },
  },
  {
    // ULTIMA deliberat: pana aici DOM-ul e complet (panou, details deschise), deci
    // regulile `[data-theme="dark"] .izz-profile-btn` au pe ce sa se aplice.
    id: 'S4', nume: 'tema intunecata',
    async condu(page) {
      // Clicul pe buton e calea reala (trece prin theme.js), dar pana aici S1 a deschis
      // toate <details>-urile si butonul poate fi acoperit — masurat: clicul esua tacut si
      // toata tema intunecata se raporta drept „neatinsa". Deci: incearca butonul, VERIFICA,
      // si cazi pe atribut daca n-a tinut.
      const btn = await page.$('.theme-toggle');
      if (btn) await btn.click({ timeout: 2000 }).catch(() => {});
      await page.waitForTimeout(300);
      if (!(await page.evaluate(() => document.documentElement.getAttribute('data-theme') === 'dark'))) {
        await page.evaluate(() => document.documentElement.setAttribute('data-theme', 'dark'));
        await page.waitForTimeout(300);
      }
      await treciCuMouse(page, 25);   // hover-urile din tema intunecata sunt alte reguli
    },
    // O stare care nu se aplica trebuie sa PICE zgomotos, nu sa raporteze „neatins".
    async verifica(page) {
      return page.evaluate(() => document.documentElement.getAttribute('data-theme') === 'dark');
    },
  },
];

/** Masoara o pagina: intoarce, pe stare, indicii regulilor devenite folosite atunci. */
async function masoaraPagina(browser, url, viewport, reguli) {
  /** CDP raporteaza offset-ul de start al regulii; il cautam binar in lista parsata. */
  const gasesteRegula = (offset) => {
    let jos = 0, sus = reguli.length - 1;
    while (jos <= sus) {
      const m = (jos + sus) >> 1;
      if (offset < reguli[m].start) sus = m - 1;
      else if (offset >= reguli[m].end) jos = m + 1;
      else return m;
    }
    return undefined;
  };
  const page = await browser.newPage({ viewport });
  const cdp = await page.context().newCDPSession(page);
  const foiCss = new Map();                       // styleSheetId -> sourceURL
  cdp.on('CSS.styleSheetAdded', (e) => foiCss.set(e.header.styleSheetId, e.header.sourceURL || ''));

  const pePasi = new Map();
  const erori = [];
  page.on('pageerror', (e) => erori.push(String(e).slice(0, 200)));
  try {
    await cdp.send('DOM.enable');
    await cdp.send('CSS.enable');
    await cdp.send('CSS.startRuleUsageTracking');
    await page.goto(url, { waitUntil: 'load', timeout: 30000 });

    for (const stare of STARI) {
      await stare.condu(page);
      if (stare.verifica && !(await stare.verifica(page).catch(() => false)))
        erori.push(`starea ${stare.id} (${stare.nume}) NU s-a aplicat — cifra ei nu inseamna nimic`);
      const { coverage } = await cdp.send('CSS.takeCoverageDelta');
      const indici = new Set();
      for (const c of coverage) {
        if (!c.used) continue;
        const sursa = foiCss.get(c.styleSheetId) || '';
        if (!sursa.includes('styles.css')) continue;      // doar foaia noastra
        const idx = gasesteRegula(c.startOffset);
        if (idx !== undefined) indici.add(idx);
        else erori.push(`offset necunoscut ${c.startOffset}-${c.endOffset}`);
      }
      pePasi.set(stare.id, indici);
    }
  } finally {
    await page.close().catch(() => {});
  }
  return { pePasi, erori };
}

/* ------------------------------------------------------------- esantionul --- */

/** Pagini de articol variate + cele trei tipuri de index. Determinist: sortare, nu random. */
async function alegeEsantion(dir, ceruteDeUtilizator) {
  if (ceruteDeUtilizator.length) return ceruteDeUtilizator;
  const indexuri = ['/', '/local/', '/judetean/'].filter((p) =>
    existsSync(join(dir, p, 'index.html')));

  const candidati = [];
  async function plimba(d, adancime) {
    if (adancime > 4 || candidati.length > 4000) return;
    let intrari;
    try { intrari = await readdir(d, { withFileTypes: true }); } catch { return; }
    for (const it of intrari.sort((a, b) => a.name.localeCompare(b.name))) {
      if (it.isDirectory()) await plimba(join(d, it.name), adancime + 1);
      else if (it.name === 'index.html') candidati.push(join(d, it.name));
    }
  }
  await plimba(dir, 0);

  // Un articol se recunoaste dupa caseta de surse (§7: fiecare articol are exact una).
  // Articolele se recunosc dupa caseta de surse (§7: fiecare articol are exact una). Luam
  // PRIMUL de fiecare varianta structurala, si completam pana la 6 cu articole distantate
  // uniform prin lista — o singura varianta dominanta nu mai reduce esantionul la un articol.
  const articole = [];
  const variante = new Map();
  for (const f of candidati) {
    let html;
    try { html = readFileSync(f, 'utf8'); } catch { continue; }
    if (!html.includes('sources-box')) continue;
    const cale = '/' + f.slice(dir.length + 1).replace(/index\.html$/, '');
    articole.push(cale);
    const cheie = [
      html.includes('<picture') ? 'copertaP' : (html.includes('<img') ? 'copertaI' : 'faraCoperta'),
      (html.match(/rel="noopener/g) || []).length > 1 ? 'multiSursa' : 'monoSursa',
      html.includes('official-note') ? 'anuntOficial' : 'articol',
    ].join('+');
    if (!variante.has(cheie)) variante.set(cheie, cale);
  }
  const alese = new Set(variante.values());
  const pas = Math.max(1, Math.floor(articole.length / 6));
  for (let i = 0; alese.size < 6 && i < articole.length; i += pas) alese.add(articole[i]);
  process.stderr.write(`  esantion: ${articole.length} articole gasite, ${variante.size} variante structurale, ${alese.size} alese\n`);
  return [...indexuri, ...alese];
}

/* ---------------------------------------------------------------- raport --- */

const kb = (o) => (o / 1024).toFixed(1).padStart(6) + ' KB';
const pc = (parte, tot) => ((100 * parte) / tot).toFixed(1).padStart(5) + '%';

function octeti(reguli, indici) {
  let s = 0;
  for (const i of indici) s += reguli[i].end - reguli[i].start;
  return s;
}

async function main() {
  const argv = process.argv.slice(2);
  const iJson = argv.indexOf('--json');
  const caleJson = iJson === -1 ? null : argv[iJson + 1];
  // paginile sunt cai din site (`/cat/slug/`); valoarea lui --json e o cale de FISIER si
  // incepe si ea cu `/`, deci se exclude explicit — altfel ajunge masurata ca pagina.
  const pagini = argv.filter((a, i) => a.startsWith('/') && i !== iJson + 1);

  if (!existsSync(OUTPUT)) {
    console.error(`output/ lipseste. Ruleaza intai: python -m generator.main --render-only`);
    process.exit(2);
  }
  const textCss = readFileSync(CSS_SURSA, 'utf8');
  const totalOcteti = Buffer.byteLength(textCss);
  const totalGzip = gzipSync(Buffer.from(textCss), { level: 9 }).length;
  const { reguli } = parseazaReguli(textCss);
  const octetiInReguli = reguli.reduce((s, r) => s + (r.end - r.start), 0);

  const esantion = await alegeEsantion(OUTPUT, pagini);
  if (!esantion.length) {
    console.error('Nu am gasit pagini in output/. A terminat randarea?');
    process.exit(2);
  }

  const { chromium } = await importaPlaywright();
  const server = await servesteOutput(OUTPUT, PORT);
  const browser = await chromium.launch({ executablePath: gasesteChromium() });
  const VIEWPORTURI = [
    { nume: 'desktop', viewport: { width: 1280, height: 900 } },
    { nume: 'mobil', viewport: { width: 390, height: 844 } },
  ];

  const rezultate = [];      // { cale, tip, pePasi: Map(cheie -> Set), erori }
  try {
    for (const cale of esantion) {
      const url = `http://127.0.0.1:${PORT}${cale}`;
      const pePasi = new Map();
      const erori = [];
      const vazutePanaAcum = new Set();
      for (const v of VIEWPORTURI) {
        let r;
        try {
          r = await masoaraPagina(browser, url, v.viewport, reguli);
        } catch (e) {
          erori.push(`${v.nume}: ${String(e).slice(0, 160)}`);
          continue;
        }
        erori.push(...r.erori);
        for (const [stare, indici] of r.pePasi) {
          // atribuim fiecare regula PRIMEI stari (si primului viewport) care a folosit-o
          const noi = new Set([...indici].filter((i) => !vazutePanaAcum.has(i)));
          for (const i of noi) vazutePanaAcum.add(i);
          const cheie = v.nume === 'desktop' ? stare : `M:${stare}`;
          pePasi.set(cheie, noi);
        }
      }
      const tip = cale === '/' ? 'home'
        : ['/local/', '/judetean/'].includes(cale) ? cale.replaceAll('/', '')
        : 'articol';
      rezultate.push({ cale, tip, pePasi, erori });
      process.stderr.write(`  masurat ${cale} (${tip})\n`);
    }
  } finally {
    await browser.close().catch(() => {});
    server.close();
  }

  /* ---- agregare ---- */
  const cheiStari = [...STARI.map((s) => s.id), ...STARI.map((s) => `M:${s.id}`)];
  const numeStare = Object.fromEntries(STARI.map((s) => [s.id, s.nume]));
  const uniune = (filtru) => {
    const set = new Set();
    for (const r of rezultate) if (filtru(r)) for (const ind of r.pePasi.values()) for (const i of ind) set.add(i);
    return set;
  };
  const articole = rezultate.filter((r) => r.tip === 'articol');
  const totiIndicii = uniune(() => true);
  const indiciArticol = uniune((r) => r.tip === 'articol');

  console.log(`\nCSS FOLOSIT — static/styles.css`);
  console.log(`${'='.repeat(74)}`);
  console.log(`fisier            ${kb(totalOcteti)}  (${totalOcteti.toLocaleString('ro')} octeti)`);
  console.log(`  gzip -9         ${kb(totalGzip)}  ← ce plateste cititorul; Cloudflare serveste brotli, deci si mai putin`);
  console.log(`  in reguli       ${kb(octetiInReguli)}  ${reguli.length} reguli`);
  console.log(`  in afara        ${kb(totalOcteti - octetiInReguli)}  comentarii, spatii, preambul @media — nu apartin niciunei reguli\n`);

  console.log(`PE O PAGINA DE ARTICOL (uniune peste ${articole.length} articole, ambele viewporturi)`);
  console.log(`${'-'.repeat(74)}`);
  let cumulat = 0;
  for (const cheie of cheiStari) {
    const set = new Set();
    for (const r of articole) for (const i of (r.pePasi.get(cheie) || [])) set.add(i);
    if (!set.size) continue;
    const o = octeti(reguli, set);
    cumulat += o;
    const baza = cheie.startsWith('M:') ? cheie.slice(2) : cheie;
    const eticheta = (cheie.startsWith('M:') ? 'mobil · ' : '') + numeStare[baza];
    console.log(`  ${eticheta.padEnd(38)} ${kb(o)}  ${String(set.size).padStart(3)} reguli`);
  }
  const neatinsArticol = reguli.map((_, i) => i).filter((i) => !indiciArticol.has(i));
  console.log(`  ${'─'.repeat(38)} ${'-'.repeat(9)}`);
  console.log(`  ${'FOLOSIT, toate starile'.padEnd(38)} ${kb(cumulat)}  ${pc(cumulat, octetiInReguli)} din reguli`);
  console.log(`  ${'NEATINS de nicio stare'.padEnd(38)} ${kb(octeti(reguli, neatinsArticol))}  ${neatinsArticol.length} reguli  ← singura cifra actionabila`);

  console.log(`\nCINE PLATESTE PENTRU CSS-UL COMUN (folosit, toate starile, pe tip de pagina)`);
  console.log(`${'-'.repeat(74)}`);
  for (const tip of ['home', 'local', 'judetean', 'articol']) {
    const set = uniune((r) => r.tip === tip);
    if (!set.size) continue;
    console.log(`  ${tip.padEnd(12)} ${kb(octeti(reguli, set))}  ${pc(octeti(reguli, set), octetiInReguli)}  ${String(set.size).padStart(3)} reguli`);
  }

  const neatinsDeloc = reguli.map((_, i) => i).filter((i) => !totiIndicii.has(i));
  console.log(`\nNEATINS DE NICIO PAGINA, NICIO STARE — ${kb(octeti(reguli, neatinsDeloc))}, ${neatinsDeloc.length} reguli`);
  console.log(`${'-'.repeat(74)}`);
  const peSectiune = new Map();
  for (const i of neatinsDeloc) {
    const s = reguli[i].sectiune;
    const v = peSectiune.get(s) || { o: 0, n: 0, exemple: [] };
    v.o += reguli[i].end - reguli[i].start; v.n++;
    if (v.exemple.length < 2) v.exemple.push(reguli[i].selector.slice(0, 46));
    peSectiune.set(s, v);
  }
  for (const [s, v] of [...peSectiune].sort((a, b) => b[1].o - a[1].o).slice(0, 14))
    console.log(`  ${s.slice(0, 34).padEnd(34)} ${kb(v.o)}  ${String(v.n).padStart(3)} reg  ${v.exemple.join(' ; ').slice(0, 60)}`);

  const totalErori = rezultate.flatMap((r) => r.erori);
  if (totalErori.length) {
    console.log(`\nAVERTISMENTE (${totalErori.length}) — primele 5:`);
    for (const e of totalErori.slice(0, 5)) console.log(`  ! ${e}`);
  }
  console.log(`\nCE NU SPUNE CIFRA: "neatins" = neexercitat de starile conduse aici (prima randare,`);
  console.log(`personalizare, derulare, hover/focus, tema intunecata, x2 viewporturi). O stare la care`);
  console.log(`unealta nu ajunge — harta, un formular trimis, o eroare — apare tot acolo, pe nedrept.`);

  if (caleJson) {
    const { writeFileSync } = await import('node:fs');
    writeFileSync(caleJson, JSON.stringify({
      fisier: { octeti: totalOcteti, gzip: totalGzip, octetiInReguli, reguli: reguli.length },
      esantion, pePagina: rezultate.map((r) => ({
        cale: r.cale, tip: r.tip,
        stari: Object.fromEntries([...r.pePasi].map(([k, v]) => [k, octeti(reguli, v)])),
      })),
      neatinsDeloc: neatinsDeloc.map((i) => ({
        selector: reguli[i].selector, sectiune: reguli[i].sectiune,
        media: reguli[i].media, octeti: reguli[i].end - reguli[i].start,
      })),
    }, null, 2));
    console.log(`\n>> raport JSON: ${caleJson}`);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((e) => { console.error('EROARE:', e); process.exit(1); });
}
