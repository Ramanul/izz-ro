// Fallback 404 -> oglinda gh-pages, pentru paginile iesite din fereastra TTL (IZZ-0425, #198).
//
// DE CE EXISTA: primarul (Workers Static Assets, `not_found_handling: 404-page`) serveste
// doar fereastra TTL — un permalink mai veche de `ARTICLE_TTL_DAYS` zile moare definitiv
// desi continutul continua sa existe pe oglinda (izolata de plafonul de 20.000 fisiere al
// planului Free). Cu acest Worker, un 404 pe un URL de articol NU se mai duce in intuneric:
// cerem aceeasi cale la oglinda gh-pages (care din 2026-10-03 acumuleaza paginile pensionate
// — `keep_files: true` in jobul `mirror`) si o livram sub canonica izz.ro.
//
// DOUA ORIGINI, O SINGURA ADRESA (2026-10-03). Oglinda nu mai e doar plasa de siguranta a
// articolului expirat: ea randeaza setul COMPLET (jobul `mirror` ruleaza cu
// OUTPUT_FILE_BUDGET=100000, deci nu taie nimic din fereastra TTL), in timp ce primarul e
// limitat la 20.000 de fisiere si taie. Diferenta dintre ele — pagini de subiect, ghiduri,
// paginare adinca, portrete ale articolelor care n-au incaput pe primar — se serveste de
// aici. Cititorul vede in continuare izz.ro; originea a doua e invizibila.
//
// LISTA POZITIVA, NU NEGATIVA. `e_cale_de_oglinda()` enumera ce POATE veni de pe oglinda si
// respinge tot restul. Invers (o lista de exceptii) ar fi lasat prima pagina, paginile de
// categorie, sitemap-urile si feedul sa cada pe o oglinda mai veche decat primarul — exact
// continutul care trebuie sa fie cel mai proaspat. Un 404 pe ceva ce nu e in lista ramane
// 404 local, ca inainte.
//
// NO-WORSE. Orice raspuns de oglinda care nu e 2xx — inclusiv 5xx si erori de retea —
// intoarce 404-ul local: a publica pagina de eroare a oglinzii drept articol (200 cu gunoi)
// ar fi mai rau decat status quo, iar promisiunea fallback-ului e no-worse.
//
// CANARY LIPSESTE pe Free: nu se porneste — cine „merge” aplică transita dintre
// `keep_files`-mirror si fallback deja verificate prin `verify_release.py` (care confirma
// sha-ul pe ambele origini). Amestecul de risc: daca oglinda e jos, paginile vechi treceau
// oricum — fallback-ul atunci e NO-WORSE decat status quo, doar o dare in plus.
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
  if (pathname.includes("%") || pathname.includes("..")) return false;

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

export default {
  async fetch(request, env) {
    const raspuns = await env.ASSETS.fetch(request);
    if (raspuns.status !== 404) return raspuns;
    const pathname = new URL(request.url).pathname;
    if (!e_cale_de_oglinda(pathname)) return raspuns;
    let din_oglinda;
    try {
      din_oglinda = await fetch(MIRROR + pathname, {
        cf: { cacheEverything: true, cacheTtl: 3600 },
      });
    } catch {
      return raspuns; // oglinda jos/timeout: 404 local, nu 500
    }
    if (!din_oglinda.ok) return raspuns;
    const headers = new Headers(din_oglinda.headers);
    headers.set("cache-control", "public, max-age=300");
    return new Response(din_oglinda.body, { status: 200, headers });
  },
};
