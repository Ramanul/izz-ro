"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");
const { JSDOM, VirtualConsole } = require("jsdom");

const root = path.resolve(__dirname, "..");
const read = (relative) => fs.readFileSync(path.join(root, relative), "utf8");
const tick = () => new Promise((resolve) => setTimeout(resolve, 60));

async function bootstrap(query = "") {
  const errors = [];
  const console = new VirtualConsole();
  console.on("jsdomError", (error) => errors.push(error.message));
  const dom = new JSDOM(read("static/harta-stiri/index.html"), {
    url: `https://izz.ro/static/harta-stiri/${query}`,
    runScripts: "outside-only", pretendToBeVisual: true, virtualConsole: console,
  });
  const { window } = dom;
  window.ResizeObserver = class { observe() {} disconnect() {} };
  window.scrollTo = () => {};
  window.matchMedia = () => ({ matches: false, addEventListener() {} });
  const base = {
    title: "Lucrări la drum", source: "test", source_name: "Test", published: "2026-10-25T10:00:00Z",
    category: "local", county: "TIMIS", locality: "TIMISOARA", x: 250, y: 400,
  };
  const articles = [
    { ...base, slug: "a", event_id: "same", event_article_count: 2, cross_confirmations: 2 },
    { ...base, slug: "b", event_id: "same", event_article_count: 2, cross_confirmations: 3 },
    { ...base, slug: "c", event_id: "other" },
    { ...base, slug: "d", county: "ALBA", event_id: "single", cross_confirmations: 1 },
    { ...base, slug: "e", county: "BRASOV", event_id: "unknown" },
  ];
  const data = JSON.parse(read("static/harta-stiri/data/map.json"));
  data.articles = articles;
  window.fetch = async (url) => {
    if (String(url).includes("/data/map.json")) return { ok: true, json: async () => data };
    const file = path.join(root, String(url).replace(/^\//, ""));
    if (!fs.existsSync(file)) return { ok: false, status: 404 };
    return { ok: true, json: async () => JSON.parse(fs.readFileSync(file, "utf8")) };
  };
  window.eval(read("static/harta-stiri/harta-stiri.js"));
  await tick();
  assert.deepEqual(errors, []);
  return { window, close: () => dom.window.close() };
}

test("lens preserves complete lists, unknowns and conservative event measurements", async () => {
  const { window, close } = await bootstrap();
  try {
    const document = window.document;
    const count = document.querySelectorAll("#news-list > li").length;
    document.querySelector('[data-scale="confirmari"]').click();
    await tick();
    assert.equal(document.querySelectorAll("#news-list > li").length, count);
    assert.equal(document.querySelector('[data-scale="confirmari"]').getAttribute("aria-checked"), "true");
    assert.equal(document.querySelectorAll('[data-scale][aria-checked="true"]').length, 1);
    assert.match(window.location.search, /scara=confirmari/);
    const timis = document.querySelector('.map-county[data-judet="TIMIS"]');
    assert.match(timis.getAttribute("aria-label"), /3 confirmări măsurate · date pentru 1 din 2/);
    const unknown = document.querySelector('.map-county[data-judet="BRASOV"]');
    assert.match(unknown.getAttribute("aria-label"), /nemăsurat/);
    assert(unknown.classList.contains("is-unmeasured"));
    assert.match(document.querySelector('#county-picker [data-county="BRASOV"]').textContent, / · —$/);
    const timisPicker = document.querySelector('#county-picker [data-county="TIMIS"]');
    assert.match(timisPicker.textContent, / · 3\+$/);
    assert.match(timisPicker.getAttribute("aria-label"), /date pentru 1 din 2 evenimente/);
    assert.match(unknown.getAttribute("aria-label"), /nemăsurat pentru 1 eveniment\b/);
    assert.match(document.querySelector("#news-list").textContent, /prima relatare/);
    const alba = document.querySelector('.map-county[data-judet="ALBA"]');
    assert.match(alba.getAttribute("aria-label"), /0 confirmări măsurate · date pentru 1 din 1/);
    assert(!alba.classList.contains("is-unmeasured"));
    assert.match(document.querySelector("#news-list").textContent, /nemăsurat/);
    assert.equal(document.querySelector('[data-title="confirmari"]').hidden, false);
    assert.match(document.querySelector("#map-status").textContent, /date pentru 2 din 4 evenimente/);

    document.querySelector('[data-view="articles"]').click();
    await tick();
    assert.equal(document.querySelectorAll("#news-list > li").length, 5);
    assert.match(timis.getAttribute("aria-label"), /3 confirmări măsurate/);
    assert(!timis.getAttribute("aria-label").includes("5 confirmări"));
    document.querySelector("#reset-all").click();
    await tick();
    assert.equal(window.location.search, "");
    assert.equal(document.querySelector('[data-scale="volum"]').getAttribute("aria-checked"), "true");
    assert.equal(document.querySelector(".is-unmeasured"), null);
  } finally { close(); }
});

test("regional geography stays categorical and restores the remembered lens", async () => {
  const { window, close } = await bootstrap("?scara=confirmari");
  try {
    const document = window.document;
    document.querySelector('[data-level="regional"]').click();
    await tick();
    const button = document.querySelector('[data-scale="confirmari"]');
    assert.equal(button.disabled, true);
    assert.equal(document.querySelector("#confirmation-scope").hidden, false);
    assert.equal(document.querySelector("#confirmation-hint").hidden, true);
    assert.equal(document.querySelector("#map-legend").hidden, true);
    assert.equal(document.querySelector(".is-unmeasured"), null);
    assert.match(window.location.search, /scara=confirmari/);
    for (const county of document.querySelectorAll(".map-county")) {
      assert(!county.getAttribute("aria-label").includes("confirmări măsurate"));
    }
    document.querySelector('[data-level="all"]').click();
    await tick();
    assert.equal(button.disabled, false);
    assert.equal(document.querySelector("#confirmation-scope").hidden, true);
    assert.equal(document.querySelector("#confirmation-hint").hidden, false);
    assert.equal(document.querySelector('[data-title="confirmari"]').hidden, false);
  } finally { close(); }
});

test("direct links, history and keyboard restore the explicit lens", async () => {
  const { window, close } = await bootstrap("?scara=confirmari");
  try {
    const document = window.document;
    assert.equal(document.querySelector('[data-scale="confirmari"]').getAttribute("aria-checked"), "true");
    document.querySelector('[data-scale="confirmari"]').dispatchEvent(
      new window.KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    await tick();
    assert.equal(document.querySelector('[data-scale="volum"]').getAttribute("aria-checked"), "true");
    window.history.pushState({}, "", "?scara=confirmari");
    window.dispatchEvent(new window.PopStateEvent("popstate"));
    await tick();
    assert.equal(document.querySelector('[data-scale="confirmari"]').getAttribute("aria-checked"), "true");
    document.querySelector('[data-scale="locuitori"]').click();
    await tick();
    assert.equal(document.querySelector('[data-scale="locuitori"]').getAttribute("aria-checked"), "true");
    assert.equal(document.querySelectorAll('[data-scale][aria-checked="true"]').length, 1);
  } finally { close(); }
});

test("filters keep measurement coverage coherent and regional keyboard skips the unavailable lens", async () => {
  const { window, close } = await bootstrap("?scara=confirmari&q=Bra%C8%99ov");
  try {
    const document = window.document;
    assert.equal(document.querySelectorAll("#news-list > li").length, 1);
    assert.match(document.querySelector("#map-status").textContent, /nemăsurat pentru 1 eveniment\b/);
    assert.match(document.querySelector('#county-picker [data-county="BRASOV"]').textContent, / · —$/);
    document.querySelector("#reset-all").click();
    document.querySelector('[data-level="regional"]').click();
    document.querySelector('[data-scale="locuitori"]').click();
    await tick();
    document.querySelector('[data-scale="locuitori"]').dispatchEvent(
      new window.KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    await tick();
    assert.equal(document.querySelector('[data-scale="confirmari"]').disabled, true);
    assert.equal(document.querySelector('[data-scale="volum"]').getAttribute("aria-checked"), "true");
  } finally { close(); }
});
