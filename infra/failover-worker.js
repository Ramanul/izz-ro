// Failover router la edge pentru izz.ro.
//
// Serveste din Cloudflare Pages (primar). La 5xx, eroare de retea sau timeout,
// serveste TRANSPARENT din mirror-ul GitHub Pages (ramanul.github.io). Comutarea e
// per-request, instant, fara propagare DNS. Clientul vede mereu certificatul de edge
// al Cloudflare pentru izz.ro; originile sunt fetch-uite server-side de Worker, deci
// NU exista gol de certificat la failover (spre deosebire de un flip DNS catre GitHub).
//
// Deploy: vezi infra/README-failover.md. Necesita un token Cloudflare cu
// Workers Scripts:Edit + Workers Routes:Edit pe zona izz.ro.

const PRIMARY = "https://izz-ro.pages.dev";
const MIRROR = "https://ramanul.github.io";
const PRIMARY_TIMEOUT_MS = 4000;

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

function tag(resp, origin) {
  const h = new Headers(resp.headers);
  h.set("x-izz-origin", origin);
  return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers: h });
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    try {
      const r = await tryOrigin(PRIMARY, request, url, PRIMARY_TIMEOUT_MS);
      if (r.status < 500) return tag(r, "primary");
    } catch (e) {
      // timeout sau eroare de retea la primar -> cade pe mirror
    }
    const m = await tryOrigin(MIRROR, request, url, 0);
    return tag(m, "mirror");
  },
};
