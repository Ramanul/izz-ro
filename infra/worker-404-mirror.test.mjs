// Testele regulilor de rutare din worker-404-mirror.js.
//
// DE CE UN TEST PE REGULI, NU PE WORKER: esecul de evitat aici nu e „fallback-ul nu merge",
// ci „fallback-ul serveste continut VECHI drept proaspat" — prima pagina, o categorie sau un
// sitemap luate de pe oglinda in loc de primar. Asta e o functie pura, deci se verifica fara
// Workers, fara retea si fara cont Cloudflare.
//
// Rulare: `node --test infra/` (sau prin pytest: tests/test_worker_mirror_rutare.py).
import test from "node:test";
import assert from "node:assert/strict";

import { e_cale_de_oglinda } from "./worker-404-mirror.js";

test("pagina de articol iese din fereastra TTL -> oglinda", () => {
  assert.equal(e_cale_de_oglinda("/local/un-articol-vechi/"), true);
  assert.equal(e_cale_de_oglinda("/politic/alt-articol"), true);
});

test("imaginile articolului servit de pe oglinda vin tot de acolo", () => {
  for (const f of [
    "cover.jpg", "art.jpg", "art.webp", "art.avif", "photo.jpg", "photo.webp", "photo.avif",
  ]) {
    assert.equal(e_cale_de_oglinda(`/local/un-articol/${f}`), true, f);
  }
});

test("sectiunile de coada lunga merg pe oglinda", () => {
  for (const p of [
    "/subiect/valcea/",
    "/subiect/donald-trump/feed.xml",
    "/ghiduri/salariul-minim/",
    "/instrumente/calculator-salariu/",
    "/calendar/",
    "/legal/corrections/",
    "/despre/",
    "/sectiuni/",
    "/surse/",
    "/portraits/donald-trump.jpg",
    "/og/local.jpg",
    "/leads/2026/09/o-foto.jpg",
  ]) {
    assert.equal(e_cale_de_oglinda(p), true, p);
  }
});

test("continutul care TREBUIE sa fie proaspat nu cade niciodata pe oglinda", () => {
  for (const p of [
    "/",                    // prima pagina
    "/politic/",            // pagina de categorie
    "/politic/2/",          // paginare de categorie
    "/cauta/",              // indexul de cautare
    "/feed.xml",            // fluxul RSS
    "/sitemap.xml",
    "/sitemap-news.xml",
    "/robots.txt",
    "/search-index.json",
    "/build.json",          // manifestul de release — verificat de verify_release.py
    "/_headers",
    "/_redirects",
    "/404.html",
    "/.well-known/security.txt",
    "/static/styles.css",
    "/static/harta-stiri/",
  ]) {
    assert.equal(e_cale_de_oglinda(p), false, p);
  }
});

test("traversarea si caiile percent-codate sunt refuzate", () => {
  for (const p of [
    "/subiect/../../etc/passwd",
    "/legal/%2e%2e/%2e%2e/secret",
    "/subiect/x%2fy/",
  ]) {
    assert.equal(e_cale_de_oglinda(p), false, p);
  }
});

test("intrarile invalide nu arunca", () => {
  assert.equal(e_cale_de_oglinda(""), false);
  assert.equal(e_cale_de_oglinda("fara-slash"), false);
  assert.equal(e_cale_de_oglinda(undefined), false);
  assert.equal(e_cale_de_oglinda(null), false);
  assert.equal(e_cale_de_oglinda(42), false);
});

test("un fisier necunoscut din directorul unui articol nu merge pe oglinda", () => {
  // Lista de imagini e inchisa: altfel orice 404 dintr-un director de articol ar deveni o
  // cerere catre un host extern.
  assert.equal(e_cale_de_oglinda("/local/un-articol/index.html"), false);
  assert.equal(e_cale_de_oglinda("/local/un-articol/../../secret.jpg"), false);
});
