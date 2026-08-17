# Redundanță izz.ro — două sisteme de servire + failover automat

Scop: site-ul public să nu pice la un incident de deploy sau la o cădere a hostului primar.

## Arhitectură

```
                    ┌─────────────── Cloudflare edge (izz.ro) ───────────────┐
   client ── TLS ──▶│  Worker izz-failover                                    │
                    │    0) Cache API la edge — HIT ⇒ raspuns fara fetch       │
                    │    1) fetch primar  https://izz-ro.pages.dev (timeout 1,5s)
                    │    2) la 5xx/eroare/timeout → https://ramanul.github.io  │
                    └────────────────────────────────────────────────────────┘
```

- **Sistem #1 (primar):** Cloudflare Pages — `izz-ro.pages.dev`, deploy la commit-ul de conținut.
- **Sistem #2 (mirror):** GitHub Pages — `ramanul.github.io`, host complet independent, sincronizat
  de jobul `mirror` din `.github/workflows/build.yml` la fiecare rulare a pipeline-ului (2h).
- **Failover:** Worker la edge, per-request, instant, fără propagare DNS. Clientul vede mereu
  certul Cloudflare pentru izz.ro; originile-s fetch-uite server-side → **fără gol de certificat**.
- **Detecție:** `.github/workflows/monitor.yml` verifică extern cele trei suprafețe la 10 min și
  alertează (email owner) doar la cădere publică sau pierdere totală a redundanței.

Punctul unic ireductibil rămas: DNS + edge Cloudflare și registrarul (ICI). Nicio redundanță
tehnică nu acoperă expirarea domeniului — ține calendarul de plată.

## Cache la edge (adăugat 2026-08-17)

Măsurat înainte: **6 răspunsuri cache-uite din 34.419 în 7 zile = 0,02%**, iar `CF-Cache-Status`
lipsea complet din răspunsurile de pe izz.ro. Cauza nu erau headerele originii — `output/_headers`
dă `max-age=2592000, immutable` pe `/static/*` și `86400` pe imagini, corect — ci faptul că
**răspunsul generat de un Worker nu intră în cache-ul de zonă**. Cât timp ruta `izz.ro/*` e prinsă
de Worker, singura cale de a cache-ui la edge e Cache API, explicit, din Worker.

- Se cache-uiește **doar ce vine de la primar**. În incident răspunsurile vin de la mirror și nu se
  stochează: incidentul trece, cache-ul ar rămâne.
- Assets păstrează headerul originii neatins. HTML (`max-age=0, must-revalidate`) primește
  `s-maxage=120`, XML `s-maxage=300` — `s-maxage` se aplică DOAR cache-urilor partajate, browserul
  revalidează în continuare. Publicarea e la ~2h, deci întârzierea maximă a unui articol nou e 2 min.
- Nu se cache-uiesc: non-GET, `Range`, `Authorization`, status ≠ 200, răspunsuri cu `Set-Cookie`.

Diagnostic din curl — headerul `x-izz-cache` ia `HIT` / `MISS` / `BYPASS`:

```bash
curl -sI https://izz.ro/static/styles.css | grep -i x-izz-cache   # a doua oara: HIT
```

## Deploy Worker (o singură dată)

Necesită un token Cloudflare cu **Workers Scripts:Edit** + **Workers Routes:Edit** pe zona izz.ro
(cel existent e scoped doar pe Pages). Creează-l pe dash.cloudflare.com → My Profile → API Tokens.

```bash
cd infra
npm i -g wrangler
export CLOUDFLARE_API_TOKEN="<token-nou>"
wrangler deploy
```

`wrangler deploy` publică Worker-ul și leagă ruta `izz.ro/*`. Verificare:

```bash
curl -sI https://izz.ro/ | grep -i x-izz-origin      # asteptat: primary
```

Test failover fără să strici primarul: schimbă temporar `PRIMARY` într-un host inexistent,
`wrangler deploy`, `curl -sI https://izz.ro/ | grep x-izz-origin` → `mirror`, apoi revert-deploy.

## De reținut

- Ruta Worker are prioritate peste custom domain-ul Pages — nu șterge custom domain-ul izz.ro
  din proiectul Pages; Worker-ul îl scurtcircuitează oricum.
- Mirror-ul NU are custom domain (fără `CNAME`) — Worker-ul face Host-rewrite; asta evită
  provizionarea unui cert Let's Encrypt pe GitHub (care ar fi imposibilă cât timp DNS-ul e la CF).
- Cheia de deploy a mirror-ului = secret `MIRROR_DEPLOY_KEY` pe Ramanul/izz-ro (deploy key cu
  write pe Ramanul/ramanul.github.io, id 158203022).
