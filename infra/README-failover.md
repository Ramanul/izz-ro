# Redundanță izz.ro — două sisteme de servire + failover automat

Scop: site-ul public să nu pice la un incident de deploy sau la o cădere a hostului primar.

## Arhitectură

```
                    ┌─────────────── Cloudflare edge (izz.ro) ───────────────┐
   client ── TLS ──▶│  Worker izz-failover                                    │
                    │    0) Cache API la edge — HIT ⇒ raspuns fara fetch       │
                    │    1) fetch primar  https://izz-ro.andifreelancer2.workers.dev (1,5s)
                    │    2) la 5xx/eroare/timeout → https://ramanul.github.io  │
                    └────────────────────────────────────────────────────────┘
```

- **Sistem #1 (primar):** Worker de static assets — `izz-ro.andifreelancer2.workers.dev`, build
  la commit-ul de conținut. **Mutat de pe Pages pe 2026-08-22**: output-ul a depășit plafonul de
  20.000 de fișiere al Pages, deploy-urile erau refuzate tăcut, iar failover-ul continua să
  fetch-uiască o origine înghețată — 34 de ore de conținut vechi, cu tot lanțul verde în aval.
  Lecția e a arhitecturii, nu a gazdei: **failover-ul acoperă o origine CĂZUTĂ, nu una VECHE.**
  O origine care răspunde 200 cu conținut de ieri arată identic cu una sănătoasă.
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

## Ce deployează fiecare Worker — măsurat 2026-08-23

Auditul a pornit de la teza „starea Cloudflare a divergat de repo". **Codul nu a divergat.**
Sursa deployată a lui `izz-failover`, extrasă prin API și normalizată (bundle-ul e esbuild),
e identică semantic cu `infra/failover-worker.js`: singurele diferențe sunt `const`→`var`, o
virgulă finală și o redenumire de variabilă din destructurare. `PRIMARY`, `MIRROR`, `1500`,
`120`, `300` — toate la fel.

Ce lipsea era răspunsul la „**cine deployează originea primară**". E Workers Builds — integrare
Git configurată din dashboard pe 2026-08-22T20:12:58Z, invizibilă din repo. Config brut:

```
git_repository:  Ramanul/izz-ro (github, repo_id 1272998428), branch main
build_command:   pip install -r requirements.txt && python -m generator.main --render-only
deploy_command:  npx wrangler deploy          # trigger pe main -> productie
                 npx wrangler versions upload # trigger pe orice alta ramura -> preview
root_directory:  /        PYTHON_VERSION: 3.11        build_caching_enabled: false
deploy_hooks:    []       declansarea e exclusiv push_event pe GitHub
```

Deci lanțul complet: `push pe main` → Workers Builds rulează `--render-only` → `wrangler deploy`
publică `output/` în Worker-ul `izz-ro` → `izz-failover` îl fetch-uiește ca `PRIMARY`. Măsurat pe
build-ul de pe 2026-08-23: commit `03d700f2` la 15:54, deploy terminat 16:06:59 — **~12 minute**
de la commit la publicare. `last_deployed_from` rămâne gol fiindcă Workers Builds nu populează
câmpul; `annotations.workers/triggered_by: version_upload` e cel care spune adevărul.

| Componentă | Unde trăiește | Reconstruibil din git? |
|---|---|---|
| Cod + config `izz-failover` | `infra/failover-worker.js`, `infra/wrangler.toml` | **Da** — verificat prin diff |
| Config `izz-ro` | `wrangler.jsonc` în rădăcină (assets-only, fără `main`) | **Da** |
| **Conexiunea Workers Builds** | doar dashboard | **NU** — comenzile sunt mai sus |
| DNS, Page rule www→apex, SSL, challenge de zonă | doar dashboard | **NU** |

### Ipoteze picate — nu le redeschide

- **„`MIRROR` e greșit, ar trebui `ramanul.github.io/izz-ro`."** FALS, și ar fi rupt producția.
  Mirror-ul e un repo **separat**, `Ramanul/ramanul.github.io` (jobul `mirror` din `build.yml`:
  `external_repository`, `publish_branch: gh-pages`, `cname: ""`), deci **user page servit la
  rădăcină**. Măsurat: `https://ramanul.github.io/` → **200**, `.../izz-ro/` → **404**. Cu
  „reparația" aplicată, fiecare failover ar fi servit 404 — și doar în timpul unui incident
  real, adică exact când conta. Vezi IZZ-0241.
- **„Worker-ul `izz-ro` nu e deloc în repo."** FALS — `wrangler.jsonc` îl declară, iar
  `has_assets: true` / `has_modules: false` citite din API se potrivesc exact cu un assets-only
  fără `main`. Lipsea mecanismul de deploy, nu configurația. Vezi IZZ-0242.
- **„Redirect-ul www→apex nu funcționează, ruta Worker suprascrie Page rule-ul."** FALS.
  Măsurat: `curl -sI https://www.izz.ro/` → **301**, `Location: https://izz.ro/`. Vezi IZZ-0243.

Starea sănătoasă, măsurată în aceeași zi: `https://izz.ro/` → 200 cu `x-izz-origin: primary`;
originea primară servea `sitemap.xml` cu `lastmod` la zi și `404.html` propriu.

## De reținut

- Ruta Worker are prioritate peste custom domain-ul Pages — nu șterge custom domain-ul izz.ro
  din proiectul Pages; Worker-ul îl scurtcircuitează oricum.
- Mirror-ul NU are custom domain (fără `CNAME`) — Worker-ul face Host-rewrite; asta evită
  provizionarea unui cert Let's Encrypt pe GitHub (care ar fi imposibilă cât timp DNS-ul e la CF).
- Cheia de deploy a mirror-ului = secret `MIRROR_DEPLOY_KEY` pe Ramanul/izz-ro (deploy key cu
  write pe Ramanul/ramanul.github.io, id 158203022).
