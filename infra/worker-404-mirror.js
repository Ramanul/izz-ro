// Bounded fallback 404 -> gh-pages mirror (IZZ-0425, #198).
// The primary serves the TTL window; articles that left it, and long-tail routes the
// primary cuts, are served from the mirror (`keep_files: true`, full render). A mirror
// response is not generation-bound proof of an archived body.
//
// LISTA POZITIVA, NU NEGATIVA. `e_cale_de_oglinda()` enumera ce POATE veni de pe oglinda si
// respinge tot restul. Invers (o lista de exceptii) ar fi lasat prima pagina, paginile de
// categorie, sitemap-urile si feedul sa cada pe o oglinda mai veche decat primarul — exact
// continutul care trebuie sa fie cel mai proaspat. Un 404 pe ceva ce nu e in lista ramane
// 404 local, ca inainte.
//
// A successful fallback requires a bounded, validated response. A network or archive
// failure returns the local 404 without negative caching. This preserves status
// semantics but does not prove availability of every historical URL.
//
// Cache-Control on a Worker response does not bypass Worker invocations. Existing
// mirror release probes compare freshness; they do not attest exact archived body
// hashes or dependencies. Retention/eviction must have a separate integrity gate.
const MIRROR = "https://ramanul.github.io";

// Categoriile editoriale, din `generator/config.py:CATEGORIES`. Sincronizarea e verificata
// de `tests/test_worker_mirror_rutare.py` — daca se adauga o categorie in pipeline si nu si
// aici, articolele ei expirate incep sa dea 404 in loc sa vina de pe oglinda, iar testul pica.
const CATEGORII = new Set([
  "general", "regional", "judetean", "local", "politic", "economic", "extern", "sport",
  "ai", "tech", "auto", "sanatate", "cultura", "lifestyle", "discounturi",
]);

// Sectiunile de coada lunga: pagini care trebuie sa raspunda si cand primarul nu le (mai) are.
// Toate sunt randate de jobul `mirror` la fiecare rulare.
const SECTIUNI_COADA = new Set([
  "subiect",       // ~1.157 de pagini de agregare; unele cad sub pragul de publicare al primarului
  "ghiduri",       // stratul permanent („Ai nevoie să știi”) — nu are voie sa dea 404 niciodata
  "instrumente",
  "calendar",
  "legal",
  "despre",
  "sectiuni",
  "surse",
  "portraits",     // portretele articolelor publicate DOAR pe oglinda (vezi render._portret)
  "og",            // copertile de categorie
  "leads",         // fotografii de lead fara obligatie de credit
]);

// Imaginile care traiesc in directorul unui articol. Fara ele, o pagina de articol servita
// de pe oglinda si-ar cere coperta de la primar — care nu o are, pentru ca articolul nu e
// al lui — si cititorul ar primi articolul cu imaginea sparta.
const IMAGINI_ARTICOL = new Set([
  "cover.jpg", "art.jpg", "art.webp", "photo.jpg", "photo.webp",
]);

// Al doilea segment al unei paginari de categorie e numar (`/politic/2/`). Un slug de articol
// NU e niciodata pur numeric — masurat pe 11.792 articole din `data/articles.json`: zero.
const DOAR_CIFRE = /^[0-9]+$/;

export function e_cale_de_oglinda(pathname) {
  if (typeof pathname !== "string" || !pathname.startsWith("/")) return false;
  // Traversare si cai percent-codate: nu le trimitem mai departe nicioadata. Oglinda e un
  // host public, iar `fetch(MIRROR + pathname)` concateneaza textual.
  if (/[ %\\\x00-\x20\x7f]/.test(pathname) || pathname.includes("..") || pathname.includes("//")) return false;

  const seg = pathname.split("/").filter(Boolean);
  if (seg.length === 0) return false;   // radacina ramane a primarului, mereu

  // 1. sectiune de coada lunga: /<sectiune> sau /<sectiune>/<oricat>
  if (SECTIUNI_COADA.has(seg[0])) return true;

  // De aici incolo, doar rute de articol — si doar sub o CATEGORIE cunoscuta. Tiparul larg
  // `/<ceva>/<ceva>/` pe care il inlocuim potrivea si `/politic/2/` (paginare) si
  // `/static/harta-stiri/`, deci paginarea adinca a primarului ar fi fost servita de pe
  // oglinda: continut vechi drept proaspat, exact ce lista pozitiva trebuie sa opreasca.
  if (!CATEGORII.has(seg[0])) return false;
  if (DOAR_CIFRE.test(seg[1] || "")) return false;

  // 2. pagina de articol: /<categorie>/<slug>/
  if (seg.length === 2) return true;

  // 3. imagine de articol: /<categorie>/<slug>/<fisier din lista inchisa>
  if (seg.length === 3 && IMAGINI_ARTICOL.has(seg[2])) return true;

  return false;
}

// Response caching saves origin traffic, not Worker invocations. Only a confirmed
// absence may be cached briefly; an unavailable archive must never poison a URL.
const CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
  "img-src 'self' data: https://tiles.openfreemap.org https://upload.wikimedia.org; " +
  "font-src 'self'; connect-src 'self' https://tiles.openfreemap.org; worker-src 'self' blob:; " +
  "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests";
const MIME = new Map([
  ["jpg", "image/jpeg"], ["jpeg", "image/jpeg"], ["webp", "image/webp"],
  ["png", "image/png"], ["xml", "application/xml"], ["ics", "text/calendar"],
]);

function headersFor(type, cache, { csp = true } = {}) {
  const headers = new Headers({
    "content-type": type, "cache-control": cache,
    "content-security-policy": CSP, "x-content-type-options": "nosniff",
    "x-frame-options": "DENY", "referrer-policy": "strict-origin-when-cross-origin",
    "strict-transport-security": "max-age=31536000; includeSubDomains",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
  });
  // Mirror HTML carries the mirror render's own inline scripts; a script-src 'self' header
  // would block them. Before the bounded fallback the mirror's headers (no CSP) passed
  // through, so archived HTML keeps no CSP header rather than a wrong one.
  if (!csp) headers.delete("content-security-policy");
  return headers;
}

function discard(response) {
  if (response?.body) void response.body.cancel().catch(() => {});
}

// Without assets.not_found_handling the ASSETS miss has an empty body, so the Worker
// serves the site's own 404 page (404.html, reachable as /404) with ITS headers
// (_headers CSP with the inline-script hashes), only status and cache changed.
async function local404(response, request, env, confirmed = false) {
  discard(response);
  const cache = confirmed ? "public, max-age=0, s-maxage=60, must-revalidate" : "no-store";
  let page = null;
  try {
    page = await env.ASSETS.fetch(new Request(new URL("/404", request.url), { method: request.method }));
  } catch { page = null; }
  const ok = page && page.status === 200;
  const headers = ok ? new Headers(page.headers) : headersFor("text/html; charset=utf-8", cache);
  headers.set("cache-control", cache);
  headers.set("x-robots-tag", "noindex");
  // The 404.html validators must not be attached to every missing URL.
  headers.delete("etag");
  headers.delete("last-modified");
  if (!ok || request.method === "HEAD") discard(page);
  return new Response(request.method === "HEAD" || !ok ? null : page.body, { status: 404, headers });
}

// A deadline covers both response headers and every byte of the body. Abort alone
// is insufficient for an upstream/mock that ignores its signal.
async function withinDeadline(action, ms) {
  const controller = new AbortController();
  let timer;
  try {
    return await Promise.race([
      action(controller.signal),
      new Promise((_, reject) => {
        timer = setTimeout(() => { controller.abort(); reject(new Error("archive deadline")); }, ms);
      }),
    ]);
  } finally { clearTimeout(timer); }
}

async function readBounded(response, limit, signal) {
  if (Number(response.headers.get("content-length")) > limit) throw new Error("archive too large");
  const reader = response.body?.getReader();
  if (!reader) throw new Error("empty archive");
  const abort = () => { void reader.cancel().catch(() => {}); };
  signal.addEventListener("abort", abort, { once: true });
  const chunks = [];
  let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > limit) throw new Error("archive too large");
      chunks.push(value);
    }
    if (!size || signal.aborted) throw new Error("empty or interrupted archive");
    const declared = response.headers.get("content-length");
    if (declared !== null && Number(declared) !== size) throw new Error("truncated archive");
    const body = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength; }
    return body;
  } finally {
    signal.removeEventListener("abort", abort);
    void reader.cancel().catch(() => {});
  }
}

function validHtml(bytes) {
  const html = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  return /<html[\s>]/i.test(html) && /<\/html\s*>/i.test(html);
}

export default {
  async fetch(request, env) {
    const raspuns = await env.ASSETS.fetch(request);
    if (raspuns.status !== 404) return raspuns;
    const pathname = new URL(request.url).pathname;
    if (!["GET", "HEAD"].includes(request.method)) return raspuns;
    if (!e_cale_de_oglinda(pathname)) return local404(raspuns, request, env, true);
    const ext = pathname.split("/").pop()?.split(".").slice(1).pop();
    const expectedType = MIME.get(ext) || "text/html";
    try {
      const result = await withinDeadline(async (signal) => {
        const upstream = await fetch(MIRROR + pathname, {
          method: request.method, signal, redirect: "manual",
          cf: { cacheEverything: true, cacheTtlByStatus: { "200-299": 300, "404": 60, "500-599": 0 } },
        });
        try {
          // GitHub Pages adds the trailing slash with a 301. Only that exact redirect is
          // honored, as a local relative redirect; any other one fails closed (no loops).
          if ([301, 308].includes(upstream.status)) {
            const target = upstream.headers.get("location");
            if (!pathname.endsWith("/") && target === MIRROR + pathname + "/") return { redirect: pathname + "/" };
            throw new Error("archive redirect rejected");
          }
          if (upstream.status !== 200) return { absent: upstream.status === 404 };
          const type = (upstream.headers.get("content-type") || "").split(";")[0].trim().toLowerCase();
          if (type !== expectedType && !(expectedType === "application/xml" && ["text/xml", "application/rss+xml"].includes(type))) {
            throw new Error("archive MIME mismatch");
          }
          if (request.method === "HEAD") return { body: null, type };
          const body = await readBounded(upstream, type.startsWith("image/") ? 8388608 : 1048576, signal);
          if (type === "text/html" && !validHtml(body)) throw new Error("invalid archive HTML");
          return { body, type };
        } finally { discard(upstream); }
      }, 2000);
      if (result.redirect) {
        discard(raspuns);
        const headers = headersFor("text/plain; charset=utf-8", "public, max-age=0, s-maxage=300, must-revalidate");
        headers.set("location", result.redirect);
        return new Response(null, { status: 301, headers });
      }
      if (!result.type) return local404(raspuns, request, env, result.absent);
      discard(raspuns);
      return new Response(result.body, {
        headers: headersFor(result.type === "text/html" ? "text/html; charset=utf-8" : result.type,
          "public, max-age=0, s-maxage=300, must-revalidate",
          { csp: result.type !== "text/html" }),
      });
    } catch {
      return local404(raspuns, request, env);
    }
  },
};
