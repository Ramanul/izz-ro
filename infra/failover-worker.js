// Failover router + cache la edge pentru izz.ro.
//
// Serveste din Worker-ul de static assets izz-ro (primar). La 5xx, eroare de retea sau timeout,
// serveste TRANSPARENT din mirror-ul GitHub Pages (ramanul.github.io). Comutarea e
// per-request, instant, fara propagare DNS. Clientul vede mereu certificatul de edge
// al Cloudflare pentru izz.ro; originile sunt fetch-uite server-side de Worker, deci
// NU exista gol de certificat la failover (spre deosebire de un flip DNS catre GitHub).
//
// CACHE (adaugat 2026-08-17). Masurat inainte: 6 raspunsuri cache-uite din 34.419 in 7
// zile = 0,02%. Cauza NU erau headerele originii — alea sunt corecte (`_headers` da
// `max-age=2592000, immutable` pe /static/*, `86400` pe imagini; Workers static assets le
// serveste identic) — ci faptul ca raspunsul
// generat de un Worker nu intra in cache-ul de zona: `CF-Cache-Status` lipsea complet din
// raspunsurile de pe izz.ro, desi era prezent pe originea servita direct. Cat timp ruta
// `izz.ro/*` e prinsa de Worker, singura cale de a cache-ui la edge e Cache API, explicit,
// de aici. Fara asta fiecare cerere de font/imagine/CSS lovea originea (26.425 subrequests
// la 26.425 cereri, raport 1,00).
//
// Deploy: vezi infra/README-failover.md. Necesita un token Cloudflare cu
// Workers Scripts:Edit + Workers Routes:Edit pe zona izz.ro.

// Primarul e Worker-ul de static assets, NU Pages. Mutat pe 2026-08-22: output-ul a
// trecut plafonul de 20.000 de fisiere al Pages, deploy-urile au inceput sa fie refuzate
// tacut, iar failover-ul continua sa fetch-uiasca o origine inghetata — site-ul a servit
// continut din 21 august timp de 34 de ore, cu totul verde in aval. Workers Paid da
// 100.000 de fisiere; aceeasi randare deployeaza acolo.
// Host DIFERIT de izz.ro, deci ruta izz.ro/* nu se auto-apeleaza (vezi wrangler.toml).
const PRIMARY = "https://izz-ro.andifreelancer2.workers.dev";
const MIRROR = "https://ramanul.github.io";

// 1500ms, coborat de la 4000. Masurat 2026-08-17, 10 cereri catre primar: median 147ms,
// p90 158ms, max 190ms. 4s insemna ~25x mediana — la o origine care chiar atarna, clientul
// astepta 4s INAINTE sa inceapa fetch-ul catre mirror, deci >4,2s pana la primul octet.
// 1500ms ramane ~9x p90, deci nu declanseaza failover pe varfuri normale de latenta.
const PRIMARY_TIMEOUT_MS = 1500;

// TTL la edge pentru raspunsurile care nu-si aduc singure un s-maxage. Browserul pastreaza
// `max-age=0, must-revalidate` de la origine — asta schimba doar cat tine edge-ul o copie
// inainte sa reintrebe originea. Pipeline-ul publica la ~2h (CLAUDE.md §17), deci 120s
// inseamna intarziere maxima de 2 minute la aparitia unui articol nou.
const EDGE_TTL_HTML = 120;
const EDGE_TTL_XML = 300;

function forwardHeaders(request) {
  // Nu propaga Host-ul clientului: fiecare origine trebuie sa-si primeasca propriul
  // Host din URL (pages.dev / github.io), altfel GitHub Pages nu stie ce site sa serveasca.
  const h = new Headers(request.headers);
  h.delete("host");
  return h;
}

async function tryOrigin(base, request, url, timeoutMs) {
  const target = base + url.pathname + url.search;
  const ctl = new AbortController();
  const t = timeoutMs ? setTimeout(() => ctl.abort(), timeoutMs) : null;
  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  try {
    return await fetch(target, {
      method: request.method,
      headers: forwardHeaders(request),
      body: hasBody ? request.body : undefined,
      redirect: "manual",
      signal: ctl.signal,
    });
  } finally {
    if (t) clearTimeout(t);
  }
}

function tag(resp, origin, cacheState) {
  const h = new Headers(resp.headers);
  h.set("x-izz-origin", origin);
  h.set("x-izz-cache", cacheState);
  return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers: h });
}

// Primar, apoi mirror la 5xx / timeout / eroare de retea. Neschimbat fata de versiunea
// initiala: 4xx (inclusiv 404) vin de la primar si NU declanseaza failover — mirror-ul e
// o copie bit-identica a primarului (verificat 2026-08-17: acelasi sha256 pe `/`, acelasi
// sitemap.xml), deci un 404 acolo ar fi tot 404, cu un fetch in plus pe degeaba.
async function serveFromOrigins(request, url) {
  try {
    const r = await tryOrigin(PRIMARY, request, url, PRIMARY_TIMEOUT_MS);
    if (r.status < 500) return { resp: r, origin: "primary" };
  } catch (e) {
    // timeout sau eroare de retea la primar -> cade pe mirror
  }
  const m = await tryOrigin(MIRROR, request, url, 0);
  return { resp: m, origin: "mirror" };
}

// Doar cererile simple de citire sunt candidate. `Range` si `Authorization` sunt sarite
// deliberat: Cache API respinge raspunsurile partiale (206), iar cererile autentificate
// n-au ce cauta intr-un cache partajat.
function isCacheableRequest(request) {
  if (request.method !== "GET") return false;
  if (request.headers.has("range")) return false;
  if (request.headers.has("authorization")) return false;
  return true;
}

// `cache.put()` arunca la Set-Cookie sau la un Cache-Control care interzice stocarea.
// Verificam inainte, ca sa nu folosim exceptii pe post de control de flux.
function isCacheableResponse(resp) {
  if (resp.status !== 200) return false;
  if (resp.headers.has("set-cookie")) return false;
  const cc = (resp.headers.get("cache-control") || "").toLowerCase();
  if (cc.includes("no-store") || cc.includes("private")) return false;
  return true;
}

// Originea trimite deja headere corecte pentru /static/* (`max-age=2592000, immutable`) si
// pentru imagini (`max-age=86400`) — alea se cache-uiesc ca atare, fara sa le atingem. Ce
// n-are TTL de edge (HTML: `max-age=0, must-revalidate`) primeste un `s-maxage`, care se
// aplica DOAR cache-urilor partajate; browserul continua sa revalideze la fiecare vizita.
function withEdgeTtl(resp) {
  const cc = (resp.headers.get("cache-control") || "").toLowerCase();
  if (cc.includes("s-maxage") || cc.includes("immutable")) return resp;

  const m = /max-age=(\d+)/.exec(cc);
  if (m && Number(m[1]) > 0) return resp; // are deja un TTL propriu, nu-l suprascriem

  const ct = (resp.headers.get("content-type") || "").toLowerCase();
  let ttl = 0;
  if (ct.includes("text/html")) ttl = EDGE_TTL_HTML;
  else if (ct.includes("xml")) ttl = EDGE_TTL_XML;
  if (!ttl) return resp;

  const h = new Headers(resp.headers);
  h.set("cache-control", `${resp.headers.get("cache-control") || "public"}, s-maxage=${ttl}`);
  return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers: h });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (!isCacheableRequest(request)) {
      const { resp, origin } = await serveFromOrigins(request, url);
      return tag(resp, origin, "BYPASS");
    }

    // Cheie normalizata: doar URL-ul. Fara asta, variatia de headere intre clienti ar
    // fragmenta cache-ul si HIT-urile ar ramane rare degeaba.
    const cacheKey = new Request(url.toString(), { method: "GET" });
    const cache = caches.default;

    const hit = await cache.match(cacheKey);
    if (hit) {
      const h = new Headers(hit.headers);
      h.set("x-izz-cache", "HIT");
      return new Response(hit.body, { status: hit.status, statusText: hit.statusText, headers: h });
    }

    const { resp, origin } = await serveFromOrigins(request, url);

    // Se cache-uieste DOAR ce vine de la primar. In timpul unui incident raspunsurile vin
    // de la mirror, iar acelea n-au ce cauta stocate cu TTL lung: incidentul trece, cache-ul
    // ar ramane.
    if (origin === "primary" && isCacheableResponse(resp)) {
      const store = withEdgeTtl(resp);
      const forClient = store.clone();
      ctx.waitUntil(cache.put(cacheKey, store));
      return tag(forClient, origin, "MISS");
    }

    return tag(resp, origin, "BYPASS");
  },
};
