// Punctul de intrare al Workerului izz.ro (`main` in wrangler.jsonc).
//
// DE CE UN FISIER NOU IN LOC SA SCRIEM IN worker-404-mirror.js. Acela e un worker cu o
// singura treaba (404 -> oglinda gh-pages), deja descris in infra/README-failover.md si in
// registru; amestecarea rutelor de push in el ar face ca orice modificare la alerte sa atinga
// si fallback-ul articolelor expirate. Aici se face doar COMPOZITIA: pushul raspunde pe
// `/push/*`, `/sw.js` primeste antetul de care are nevoie ca sa poata fi actualizat, iar tot
// restul trece prin workerul de oglinda, neschimbat.
//
// RUTAREA. Workers serveste intai activele statice si cheama Workerul doar cand nu exista
// niciun activ care sa corespunda (assets.run_worker_first = false e implicitul). Pentru
// rutele de push asta functioneaza „din intamplare" — nu exista fisier `push/...` in output —
// iar `_headers` nu poate pune antete pe ce serveste Workerul. De aceea wrangler.jsonc
// declara explicit `run_worker_first: ["/push/*", "/sw.js"]`: contractul e scris, nu dedus
// din absenta unui fisier. Restul traficului ramane pe calea rapida, a activelor.

import oglinda from './worker-404-mirror.js';
import { esteCalePush, raspunsPush } from './push.js';

// Fisiere pe care Workerul le serveste cu antet de revalidare, nu cu cache lung.
// `/sw.js` e singurul caz si e critic: browserul compara octet cu octet fisierul SW la
// fiecare navigare, dar NU o face daca raspunsul e servit din cache-ul HTTP. Cu
// `max-age=0, must-revalidate`, un SW schimbat ajunge la vizitator la urmatoarea vizita;
// fara el, ar putea sta 30 de zile, adica exact cat tin activele din /static/.
const REVALIDARE = new Map([
  ['/sw.js', 'public, max-age=0, must-revalidate'],
]);

async function cuAntete(request, env, cacheControl) {
  const sursa = await env.ASSETS.fetch(request);
  // Raspunsul unui asset e imuabil: se reconstruieste cu antetele noi, nu se modifica.
  const antete = new Headers(sursa.headers);
  antete.set('cache-control', cacheControl);
  return new Response(sursa.body, { status: sursa.status, statusText: sursa.statusText, headers: antete });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    if (esteCalePush(url.pathname)) {
      return raspunsPush(request, env, url, ctx);
    }
    const regula = REVALIDARE.get(url.pathname);
    if (regula) {
      return cuAntete(request, env, regula);
    }
    return oglinda.fetch(request, env, ctx);
  },
};
