// Verificare de DOM pentru harta stirilor, fara browser: jsdom + fetch simulat din fisiere.
//
// De ce exista, daca repo-ul are deja tools/harta_dom_check.py (Playwright): acela e garda
// COMPLETA, dar cere Chromium si o masina cu browser. Verificarile de acolo au nevoie de
// layout, pixeli si gesturi; cele de aici verifica LOGICA pe noduri reale -- ce elemente
// exista, ce clase primesc, ce scrie in aria-label, cate cereri de retea pleaca -- si ruleaza
// in orice sandbox, inclusiv in cele unde Playwright nu se poate instala (masurat: de trei ori
// in sesiunile din 2026-10-04). A prins doua defecte reale inainte de livrare: o silueta de
// `clip-path` lasata in afara arborelui (ar fi taiat TOATE UAT-urile din vedere) si un mod
// „pe locuitor" care afisa tacit numaratoarea, fiindca in stare intra fisierul de populație
// intreg in loc de dictionarul de județe.
//
// Usage:
//   npm install jsdom           (o singura data, in orice director)
//   node tools/harta_dom_jsdom.mjs [radacina-repo]     # implicit: directorul curent
//
// Ce NU verifica: asezarea etichetelor, latimile de text, suprapunerile, scrollul si
// gesturile -- jsdom nu are layout. Pentru acelea rămâne tools/harta_dom_check.py.

import fs from "node:fs";
import path from "node:path";
import { JSDOM, VirtualConsole } from "jsdom";

const ROOT = process.argv[2] ? path.resolve(process.argv[2]) : process.cwd();
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), "utf8");
const HTML_REL = "static/harta-stiri/index.html";
const JS_REL = "static/harta-stiri/harta-stiri.js";

const rezultate = [];
const erori = [];
const check = (ok, label) => rezultate.push([Boolean(ok), label]);

async function bootstrap(query = "") {
  const vc = new VirtualConsole();
  vc.on("jsdomError", (e) => erori.push(String((e && e.message) || e)));
  vc.on("error", (...a) => erori.push(a.map(String).join(" ")));
  vc.on("warn", () => {});
  const dom = new JSDOM(read(HTML_REL), {
    url: "http://localhost/static/harta-stiri/" + query,
    runScripts: "outside-only",
    pretendToBeVisual: true,
    virtualConsole: vc,
  });
  const { window } = dom;
  // Orice încercare de a desena pe canvas e un defect: substratul e SVG din 2026-10-04.
  window.HTMLCanvasElement.prototype.getContext = () => {
    throw new Error("canvas interzis: substratul hartii este SVG");
  };
  window.ResizeObserver = class { observe() {} disconnect() {} };
  window.matchMedia = window.matchMedia || (() => ({ matches: false, addEventListener() {} }));
  const cereri = [];
  window.fetch = async (url) => {
    cereri.push(String(url));
    const fisier = path.join(ROOT, "static", "harta-stiri", String(url).replace(/^\.\//, ""));
    if (!fs.existsSync(fisier)) return { ok: false, status: 404, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => JSON.parse(fs.readFileSync(fisier, "utf8")) };
  };
  window.eval(read(JS_REL));
  await asteapta(500);
  return { window, cereri };
}

const asteapta = (ms) => new Promise((r) => setTimeout(r, ms));

function pointerEv(window, type, target, extra = {}) {
  const ev = new window.MouseEvent(type, {
    bubbles: true, cancelable: true, clientX: 30, clientY: 30, ...extra,
  });
  Object.defineProperty(ev, "pointerType", { value: "mouse" });
  Object.defineProperty(ev, "buttons", { value: type === "pointerdown" ? 1 : 0 });
  target.dispatchEvent(ev);
  return ev;
}

const click = (window, el) => {
  if (!el) throw new Error("element lipsa la click");
  el.dispatchEvent(new window.MouseEvent("click", { bubbles: true, clientX: 30, clientY: 30 }));
};

function praguri(window, mod) {
  const at = mod === "locuitori" ? "praguriLocuitor" : "praguri";
  return window.document.querySelector("#map-legend").dataset[at].split(",").map(Number);
}

function clasaAsteptata(valoare, lista) {
  if (!valoare) return "h0";
  return "h" + Math.min(4, lista.filter((p) => valoare >= p).length);
}

// ---------------------------------------------------------------------------------------------
// 1. STRUCTURA: substratul si straturile
// ---------------------------------------------------------------------------------------------
async function verificariStructura() {
  const { window, cereri } = await bootstrap();
  const $ = (sel) => window.document.querySelector(sel);
  const $$ = (sel) => [...window.document.querySelectorAll(sel)];
  const judete = $$("#map svg.map-svg .layer-counties path");

  check($("#map svg.map-svg") !== null, "scena e un <svg> (nu <canvas>)");
  const stageChildren = [...$(".map-stage").children];
  check(stageChildren[0]?.classList.contains("map-basemap-viewport")
      && stageChildren[1]?.classList.contains("map-svg"),
    "viewportul MapLibre stă sub SVG, fără să schimbe straturile tematice");
  check($(".map-basemap-viewport")?.getAttribute("aria-hidden") === "true",
    "basemapul decorativ este ascuns tehnologiilor asistive");
  check(cereri.filter((url) => url.includes("/data/projection.json")).length === 1,
    "metadatele proiecției sunt cerute o singură dată");
  check($("#map-basemap-status")?.hidden === false,
    "fără WebGL în jsdom, mesajul de fallback apare iar harta rămâne randată");
  check(!$(".map-stage").classList.contains("has-basemap"),
    "fallbackul păstrează umplerea SVG opacă");
  check(judete.length === 42, `42 de județe ca <path> (${judete.length})`);
  check(judete.every((n) => n.getAttribute("tabindex") === "0"
      && n.getAttribute("role") === "button" && n.getAttribute("aria-pressed") !== null),
    "fiecare județ e focusabil, role=button, cu aria-pressed");
  check($$("#map .layer-labels text").length > 10,
    `etichete <text> la nivel național (${$$("#map .layer-labels text").length})`);
  check($("#map .layer-labels .label-value") !== null, "cifra apare în eticheta de județ");
  check($(".map-stage").style.getPropertyValue("--map-aspect") !== "",
    `raportul scenei: ${$(".map-stage").style.getPropertyValue("--map-aspect")}`);
  check($("#map-legend").hidden === false, "legenda vizibilă la nivel național");
  check($("#map .layer-outline").hidden === true && $("#map .layer-uats").hidden === true,
    "fără UAT-uri, conturul și stratul lor se ascund (nu rămân orfane)");

  // intrare pe un județ: O singura cerere de geometrie, contur pe silueta lui
  const timis = judete.find((n) => n.dataset.judet === "TIMIS");
  click(window, timis);
  await asteapta(500);
  check(window.location.search.includes("judet=TIMIS"), `click pe județ -> adresa: ${window.location.search}`);
  check($$("#map .layer-uats path").length > 0, `UAT-uri randează ca <path> (${$$("#map .layer-uats path").length})`);
  check($("#clip-judet-silueta").getAttribute("d") === timis.getAttribute("d"),
    "UAT-urile sunt tăiate pe silueta județului (clip-path)");
  check($("#map .layer-uats").getAttribute("clip-path") === "url(#clip-judet)",
    "stratul UAT e legat de clip");
  check($("#map use.map-outline") !== null, "conturul județului deschis e desenat ca <use>");
  const cereriUat = cereri.filter((u) => u.includes("/data/uat/"));
  check(cereriUat.length === 1 && cereriUat[0].includes("TIMIS.json"),
    `o singură cerere de geometrie la click: ${cereriUat.join(", ")}`);
  check($$("#map .layer-counties path.h4").length >= 1 && $$("#map .layer-counties path.h0").length >= 1,
    `trepte h0..h4 aplicate prin clase (h4: ${$$("#map .layer-counties path.h4").length}, h0: ${$$("#map .layer-counties path.h0").length})`);
  check((($("#map svg.map-svg").getAttribute("viewBox") || "").split(" ").length) === 4,
    `viewBox scris de JS: ${$("#map svg.map-svg").getAttribute("viewBox")}`);
}

// ---------------------------------------------------------------------------------------------
// 2. SCARA SI NUMITORUL: aceeasi culoare = acelasi numar, in ambele moduri
// ---------------------------------------------------------------------------------------------
async function verificariScara() {
  const { window } = await bootstrap();
  const $ = (sel) => window.document.querySelector(sel);
  const $$ = (sel) => [...window.document.querySelectorAll(sel)];

  check(window.document.querySelector('[data-title="volum"]').hidden === false,
    "titlul de volum e vizibil în modul implicit");
  check(window.document.querySelector('[data-bands="locuitori"]').hidden === true,
    "benzile de rate sunt ascunse în modul implicit");

  const buton = $('[data-scale="locuitori"]');
  click(window, buton);
  await asteapta(400);
  const lista = praguri(window, "locuitori");

  const noduri = $$("#map svg.map-svg .layer-counties path");
  const rele = [];
  let cuUnitate = 0;
  for (const nod of noduri) {
    const aria = nod.getAttribute("aria-label") || "";
    if (/la 100\.000 de locuitori/.test(aria)) cuUnitate += 1;
    const m = aria.match(/:\s*(\d+(?:,\d)?)/);
    if (!m) continue;
    const valoare = Number(m[1].replace(",", "."));
    const clase = [...nod.classList].filter((c) => /^h\d$/.test(c));
    if (clase.length !== 1 || clase[0] !== clasaAsteptata(valoare, lista)) {
      rele.push(`${nod.dataset.judet}=${valoare}->${clase.join("/")}`);
    }
  }
  check(cuUnitate >= 40, `aria-label spune unitatea pe județele cu știri (${cuUnitate}/42)`);
  check(rele.length === 0, `aceeași culoare = același număr pe ${cuUnitate} județe`
    + (rele.length ? ` — rele: ${rele.slice(0, 4).join("; ")}` : ""));

  const etichete = $$("#map .layer-labels .label-value").map((n) => n.textContent);
  check(etichete.length > 10 && etichete.every((v) => /^\d+,\d$/.test(v)),
    `etichetele arată rate cu o zecimală (ex.: ${etichete.slice(0, 3).join(", ")})`);
  check(!etichete.some((v) => v === "undefined" || v === "NaN"),
    "nicio etichetă cu undefined/NaN");
  const fereastra = $("#map-window").textContent;
  check(!/undefined|NaN/.test(fereastra) && fereastra.trim().length > 0,
    `fereastra calculată din date: „${fereastra}”`);
  check(window.location.search.includes("scara=locuitori"), `adresa: ${window.location.search}`);

  // numitorul se cere o singura data, iar revenirea nu-l mai cere
  const alt = await bootstrap();
  const cereriInainte = alt.cereri.filter((u) => u.includes("populatie.json")).length;
  check(cereriInainte === 0, "prima încărcare nu cere populatie.json (mod implicit = volum)");
  click(alt.window, alt.window.document.querySelector('[data-scale="locuitori"]'));
  await asteapta(300);
  click(alt.window, alt.window.document.querySelector('[data-scale="volum"]'));
  await asteapta(200);
  click(alt.window, alt.window.document.querySelector('[data-scale="locuitori"]'));
  await asteapta(300);
  check(alt.cereri.filter((u) => u.includes("populatie.json")).length === 1,
    `numitorul se cere o singură dată (${alt.cereri.filter((u) => u.includes("populatie.json")).length} cereri la două comutări)`);

  // link direct: modul se aplica inainte de prima desenare
  const direct = await bootstrap("?scara=locuitori&judet=TIMIS");
  const uats = [...direct.window.document.querySelectorAll("#map svg.map-svg .layer-uats path")];
  const clase = uats.map((n) => [...n.classList].filter((c) => /^h\d$/.test(c))[0]);
  check(new Set(clase).size > 1,
    `linkul direct deschide modul de rate (${uats.length} UAT-uri, clase: ${[...new Set(clase)].join("/")})`);
  check(uats.every((n) => /eveniment|relatare/.test(n.getAttribute("aria-label") || "")),
    `pe UAT-uri cifra rămâne numărătoarea: „${uats[0] ? uats[0].getAttribute("aria-label") : ""}”`);
}

// ---------------------------------------------------------------------------------------------
// 3. PLIMBAREA: toate caile de interactiune, ca sa prindem functiile sterse dar inca apelate
// ---------------------------------------------------------------------------------------------
async function verificariInteractiune() {
  const { window } = await bootstrap();
  const $ = (sel) => window.document.querySelector(sel);
  const $$ = (sel) => [...window.document.querySelectorAll(sel)];
  const drumuri = [];
  const pas = async (nume, fn) => {
    const inainte = erori.length;
    try { await fn(); } catch (e) { erori.push(`${nume}: ${e.message}`); }
    drumuri.push(`${erori.length > inainte ? "ERR " : "ok  "} ${nume}`);
  };

  const pointer = (type, target, extra = {}) => pointerEv(window, type, target, extra);

  await pas("hover pe un județ (pointermove)", async () => {
    pointer("pointermove", $$("#map .layer-counties path")[3]);
    await asteapta(60);
    if ($(".map-tip").hidden) throw new Error("tooltipul nu s-a deschis la hover");
    if (!/evenimente|relatări/.test($(".map-tip").textContent)) {
      throw new Error("tooltip fără cifra: " + $(".map-tip").textContent);
    }
  });
  await pas("ieșire de pe scenă", async () => {
    pointer("pointerleave", $("#map svg"));
    await asteapta(40);
    if (!$(".map-tip").hidden) throw new Error("tooltipul a rămas deschis");
  });
  await pas("tap pe un județ (pointerdown/up)", async () => {
    const n = $$("#map .layer-counties path")[3];
    pointer("pointerdown", n);
    pointer("pointerup", n);
    await asteapta(60);
  });
  await pas("intrare pe județ (click)", async () => {
    click(window, $$("#map .layer-counties path")[3]);
    await asteapta(400);
    if (!/judet=/.test(window.location.search)) throw new Error("adresa nu s-a schimbat");
  });
  for (const nivel of ["regional", "judetean", "local", "all"]) {
    await pas(`nivel ${nivel}`, async () => { click(window, $(`[data-level="${nivel}"]`)); await asteapta(150); });
  }
  for (const mod of ["articles", "events"]) {
    await pas(`vedere ${mod}`, async () => { click(window, $(`[data-view="${mod}"]`)); await asteapta(150); });
  }
  await pas("căutare 'cluj'", async () => {
    const inp = $("#map-search");
    inp.value = "cluj";
    inp.dispatchEvent(new window.Event("input", { bubbles: true }));
    await asteapta(300);
  });
  await pas("golire căutare", async () => {
    const inp = $("#map-search");
    inp.value = "";
    inp.dispatchEvent(new window.Event("input", { bubbles: true }));
    await asteapta(200);
  });
  for (const [nume, sel] of [
    ["zoom +", '.map-zoom button[aria-label="Apropie harta"]'],
    ["zoom -", '.map-zoom button[aria-label="Îndepărtează harta"]'],
    ["reset zoom", '.map-zoom button[aria-label="Resetează zoom-ul hărții"]'],
  ]) {
    await pas(nume, async () => { click(window, $(sel)); await asteapta(120); });
  }
  await pas("tastatură pe zoom", async () => {
    const box = $(".map-zoom");
    for (const k of ["ArrowRight", "ArrowDown", "+", "-", "Home"]) {
      box.dispatchEvent(new window.KeyboardEvent("keydown", { key: k, bubbles: true }));
      await asteapta(40);
    }
  });
  await pas("roată pe scenă", async () => {
    $("#map svg").dispatchEvent(new window.WheelEvent("wheel", {
      deltaY: -300, bubbles: true, cancelable: true, clientX: 30, clientY: 30,
    }));
    await asteapta(150);
  });
  await pas("dublu-click", async () => {
    $("#map svg").dispatchEvent(new window.MouseEvent("dblclick", { bubbles: true, clientX: 30, clientY: 30 }));
    await asteapta(150);
  });
  await pas("buton înapoi", async () => { click(window, $(".map-back")); await asteapta(300); });
  await pas("selector județ", async () => { click(window, $$("#county-picker button")[1]); await asteapta(400); });
  await pas("UAT din listă", async () => {
    const uat = $$("#county-picker button[data-uat]")[0];
    if (!uat) throw new Error("niciun buton de UAT");
    click(window, uat);
    await asteapta(200);
  });
  await pas("arată mai multe", async () => {
    const b = $("#show-more");
    if (b && !b.hidden) { click(window, b); await asteapta(200); }
  });
  await pas("fir de navigare", async () => {
    const crumbs = $$("#map-breadcrumb button");
    if (crumbs.length) { click(window, crumbs[crumbs.length - 1]); await asteapta(250); }
  });
  await pas("filtru fără rezultate", async () => {
    const inp = $("#map-search");
    inp.value = "zzzzqqq";
    inp.dispatchEvent(new window.Event("input", { bubbles: true }));
    await asteapta(300);
  });
  await pas("resetare totală", async () => { click(window, $("#reset-all")); await asteapta(250); });
  await pas("comutare scară și revenire", async () => {
    click(window, $('[data-scale="locuitori"]'));
    await asteapta(300);
    click(window, $('[data-scale="volum"]'));
    await asteapta(200);
  });

  for (const linie of drumuri) console.log("  " + linie);
  const picate = drumuri.filter((l) => l.startsWith("ERR")).length;
  check(picate === 0, `toate cele ${drumuri.length} căi de interacțiune trec fără erori`);
}

// ---------------------------------------------------------------------------------------------
await verificariStructura();
await verificariScara();
await verificariInteractiune();

console.log("");
for (const [ok, label] of rezultate) console.log(`  ${ok ? "ok  " : "FAIL"} ${label}`);
if (erori.length) {
  console.log("\nerori capturate în pagină:");
  for (const e of erori.slice(0, 10)) console.log("   - " + e);
}
const picate = rezultate.filter(([ok]) => !ok).length + erori.length;
console.log(picate ? `\n${picate} verificări picate` : "\ntoate verificările au trecut");
process.exit(picate ? 1 : 0);
