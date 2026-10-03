// Fallback 404 -> oglinda gh-pages, pentru paginile iesite din fereastra TTL (IZZ-0425, #198).
//
// DE CE EXISTA: primarul (Workers Static Assets, `not_found_handling: 404-page`) serveste
// doar fereastra TTL — un permalink mai veche de `ARTICLE_TTL_DAYS` zile moare definitiv
// desi continutul continua sa existe pe oglinda (izolata de plafonul de 20.000 fisiere al
// planului Free). Cu acest Worker, un 404 pe un URL de articol NU se mai duce in intuneric:
// cerem aceeasi cale la oglinda gh-pages (care din 2026-10-03 acumuleaza paginile pensionate
// — `keep_files: true` in jobul `mirror`) si o livram sub canonica izz.ro.
//
// TINUT IN AFARA ARTICELOR NECUNOSCUTE: fallback-ul se declanseaza doar pe tiparul
// `/<categorie>/<slug>/` (o trasa articol). Restul 404-urilor (static?/fisieri/404.html) raman
// text-area. Un raspuns de oglinda cu 404 intoarce 404-ul local, ca sa nu oferi de doua ori.
//
// CANARY LIPSESTE pe Free: nu se porneste — cine „merge" aplică transita dintre
// `keep_files`-mirror si fallback deja verificate prin `verify_release.py` (care confirma
// sha-ul pe ambele origini). Amestecul de risc: daca oglinda e jos, paginile vechi treceau
// oricum — fallback-ul atunci e NO-WORSE decat status quo, doar o dare in plus.
const MIRROR = "https://ramanul.github.io";
const CALEA_ARTICOL = /^\/[a-z0-9-]+\/[a-z0-9-]+\/?$/;

export default {
  async fetch(request, env) {
    const raspuns = await env.ASSETS.fetch(request);
    if (raspuns.status !== 404) return raspuns;
    const pathname = new URL(request.url).pathname;
    if (!CALEA_ARTICOL.test(pathname)) return raspuns;
    const din_oglinda = await fetch(MIRROR + pathname, {
      cf: { cacheEverything: true, cacheTtl: 3600 },
    });
    if (din_oglinda.status === 404) return raspuns;
    const headers = new Headers(din_oglinda.headers);
    headers.set("cache-control", "public, max-age=300");
    return new Response(din_oglinda.body, { status: 200, headers });
  },
};
