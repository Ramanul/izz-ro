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

import worker, { e_cale_de_oglinda } from "./worker-404-mirror.js";
import { webcrypto } from "node:crypto";

if (!globalThis.crypto) globalThis.crypto = webcrypto;
const HTML = "<!doctype html><html><body>Archived article</body></html>";

async function serve({ method = "GET", path = "/local/old/", origin } = {}) {
  let assetsCalls = 0;
  let mirrorCalls = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => { mirrorCalls++; return origin(url, options); };
  try {
    const response = await worker.fetch(new Request("https://izz.ro" + path, { method }), {
      ASSETS: { fetch: async (req) => {
        assetsCalls++;
        if (new URL(req.url).pathname === "/404") return new Response(req.method === "HEAD" ? null : "PAGE404", { headers: { "content-type": "text/html", "content-security-policy": "site-csp", etag: '"x"' } });
        return new Response(null, { status: 404 });
      } },
    });
    return { response, assetsCalls, mirrorCalls };
  } finally { globalThis.fetch = originalFetch; }
}

test("fallback fetches ASSETS once and applies local security headers", async () => {
  const result = await serve({ origin: (url, options) => {
    assert.equal(url, "https://ramanul.github.io/local/old/");
    assert.equal(options.method, "GET");
    assert.equal(options.redirect, "manual");
    return new Response(HTML, { headers: { "content-type": "text/html", "set-cookie": "foreign=1", "access-control-allow-origin": "*" } });
  } });
  assert.equal(result.assetsCalls, 1);
  assert.equal(result.mirrorCalls, 1);
  assert.equal(result.response.status, 200);
  assert.equal(await result.response.text(), HTML);
  // Mirror HTML has its own inline scripts: no script-src 'self' CSP may be imposed on it.
  assert.equal(result.response.headers.get("content-security-policy"), null);
  assert.equal(result.response.headers.get("x-frame-options"), "DENY");
  assert.equal(result.response.headers.get("content-type"), "text/html; charset=utf-8");
  assert.equal(result.response.headers.get("x-content-type-options"), "nosniff");
  assert.equal(result.response.headers.get("set-cookie"), null);
  assert.equal(result.response.headers.get("access-control-allow-origin"), null);
});

test("HEAD uses upstream HEAD and returns an empty body", async () => {
  let cancelled = false;
  const { response, assetsCalls } = await serve({ method: "HEAD", origin: (_, options) => {
    assert.equal(options.method, "HEAD");
    return new Response(new ReadableStream({ cancel() { cancelled = true; } }), { headers: { "content-type": "text/html" } });
  } });
  assert.equal(response.status, 200);
  assert.equal(await response.text(), "");
  assert.equal(assetsCalls, 1);
  assert.equal(cancelled, true);
});

test("methods and fresh-only routes never query the mirror", async () => {
  for (const args of [{ method: "POST" }, { path: "/" }, { path: "/feed.xml" }, { path: "/local/3/" }]) {
    const result = await serve({ ...args, origin: () => { throw new Error("must not query mirror"); } });
    assert.equal(result.response.status, 404);
    assert.equal(result.mirrorCalls, 0);
    if (args.method === "POST") {
      assert.equal(result.assetsCalls, 1);
    } else {
      // GET miss outside the mirror list: the site's own 404 page, with ITS headers.
      assert.equal(result.assetsCalls, 2);
      assert.equal(await result.response.text(), "PAGE404");
      assert.equal(result.response.headers.get("content-security-policy"), "site-csp");
      assert.equal(result.response.headers.get("etag"), null);
      assert.equal(result.response.headers.get("cache-control"), "public, max-age=0, s-maxage=60, must-revalidate");
    }
  }
});

test("mirror miss serves the local 404 page; HEAD keeps it bodiless", async () => {
  const get = await serve({ origin: () => new Response("missing", { status: 404 }) });
  assert.equal(get.response.status, 404);
  assert.equal(await get.response.text(), "PAGE404");
  const head = await serve({ method: "HEAD", origin: () => new Response(null, { status: 404 }) });
  assert.equal(head.response.status, 404);
  assert.equal(await head.response.text(), "");
});

test("only the mirror's trailing-slash redirect is honored, as a local 301", async () => {
  const ok = await serve({ path: "/local/old", origin: () => new Response(null, { status: 301, headers: { location: "https://ramanul.github.io/local/old/" } }) });
  assert.equal(ok.response.status, 301);
  assert.equal(ok.response.headers.get("location"), "/local/old/");
  for (const location of ["https://evil.example/local/old/", "https://ramanul.github.io/other/"]) {
    const bad = await serve({ path: "/local/old", origin: () => new Response(null, { status: 301, headers: { location } }) });
    assert.equal(bad.response.status, 404);
    assert.equal(bad.response.headers.get("cache-control"), "no-store");
  }
});

test("only confirmed absence has a short negative cache", async () => {
  for (const status of [404, 403, 429, 500, 503]) {
    const { response } = await serve({ origin: () => new Response("missing", { status }) });
    assert.equal(response.status, 404);
    assert.equal(response.headers.get("cache-control"), status === 404 ? "public, max-age=0, s-maxage=60, must-revalidate" : "no-store");
  }
});

test("bad MIME, malformed, empty and truncated HTML fail closed", async () => {
  for (const [body, headers] of [
    [HTML, { "content-type": "application/json" }],
    ["upstream error", { "content-type": "text/html" }],
    ["", { "content-type": "text/html" }],
    [HTML, { "content-type": "text/html", "content-length": "999" }],
    [HTML, { "content-type": "text/html", "content-length": "1048577" }],
  ]) {
    const { response } = await serve({ origin: () => new Response(body, { headers }) });
    assert.equal(response.status, 404);
    assert.equal(response.headers.get("cache-control"), "no-store");
  }
});

test("header and body stalls have finite deadlines and cancel bodies", async () => {
  for (const stall of ["headers", "body"]) {
    let cancelled = false;
    const start = performance.now();
    const { response } = await serve({ origin: () => stall === "headers" ? new Promise(() => {}) : new Response(new ReadableStream({ cancel() { cancelled = true; } }), { headers: { "content-type": "text/html" } }) });
    assert.equal(response.status, 404);
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.ok(performance.now() - start < 3500);
    if (stall === "body") assert.equal(cancelled, true);
  }
});

test("pagina de articol iese din fereastra TTL -> oglinda", () => {
  assert.equal(e_cale_de_oglinda("/local/un-articol-vechi/"), true);
  assert.equal(e_cale_de_oglinda("/politic/alt-articol"), true);
});

test("imaginile articolului servit de pe oglinda vin tot de acolo", () => {
  for (const f of ["cover.jpg", "art.jpg", "art.webp", "photo.jpg", "photo.webp"]) {
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
