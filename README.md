# IZZ.ro — Informația Zero Zgomot

Agregator de știri românești anti-clickbait. Site **static (SSG)**, model de conținut **B+C** (rezumat scurt + link / sinteză multi-sursă), publicat **serverless**: GitHub Actions rulează pipeline-ul orar și publică la ~2 ore (vezi *Deploy*). AI implicit **Gemini** (gratuit), comutabil pe **Claude API**.

## Cum rulezi local

```bash
pip install -r requirements.txt

# Pipeline complet (RSS -> AI -> HTML în output/) + salvează starea
python -m generator.main

# Doar test, fără să salveze sau să randeze (afișează rezultatul + sursele RSS moarte)
python -m generator.main --dry-run

# Vizualizare locală
python -m http.server 8000 --directory output
# -> http://localhost:8000
```

Fără cheie AI, pipeline-ul folosește un **fallback determinist** (rezumat din descrierea RSS) — util pentru testat structura. Pentru reformulare reală, pune `GEMINI_API_KEY` în `.env` (vezi `.env.example`).

## Structură

```
generator/   cod: fetch (RSS) · state (dedup/expirare) · cluster · process (AI B/C) · moderation · render (SSG) · main
templates/   Jinja2 (autoescape ON): base, index, article, category, legal, _card
static/      styles.css (auriu-dark) · logo.svg · favicon.svg
content/legal/  pagini legale (markdown)
data/articles.json  STAREA (comisă în repo — așa persistă între rulări)
moderation.yaml     control editorial (om în buclă)
output/      site generat (gitignored; deployat de Actions)
```

## Administrare
- **Ce apare pe site** se controlează din `moderation.yaml` (vezi `REVIEW.md`).
- **Surse RSS:** `generator/config.py` -> `SOURCES`.
- **Praguri B/C, TTL, max/sursă:** tot în `config.py`.

## Deploy (GitHub Actions + Cloudflare Workers)

Arhitectura separă **munca grea** de **publicare**:

1. **GitHub Actions** (`.github/workflows/build.yml`, cron `13 * * * *`): rulează pipeline-ul (fetch + AI, cu buget per rulare), apoi **comite** `data/articles.json` în repo. Secret necesar: `GEMINI_API_KEY` (repo → Settings → Secrets → Actions).
   **Încearcă orar, publică la ~2h:** un job de poartă taie rularea dacă ultimul conținut e mai proaspăt de 105 minute. Cron-ul e des *ca să apere* cele 2h — planificatorul GitHub sare firings de `schedule` (măsurat 2026-08-04: 4 rulări în loc de 12), iar cu încercări orare un firing pierdut se recuperează în ora următoare. Bugetul de build Cloudflare (~500/lună pe planul free) e păzit de poartă, nu de cron — **nu coborî pragul fără să refaci socoteala**.
2. **Cloudflare Workers Static Assets** (Workers Builds, conectat la repo, auto-deploy la fiecare commit): rulează doar **render-only** și servește `output/`. Configurația versionată stă în `wrangler.jsonc`:
   - `assets.directory: ./output` — site-ul e 100% static, deci proiectul **nu are** `main` (assets-only);
   - `not_found_handling: "404-page"` — Pages deducea singur pagina 404, Workers **nu**; fără linia asta orice URL inexistent întoarce un 404 gol, iar `output/404.html` nu mai e servit niciodată;
   - `preview_urls: true` — preview per ramură, pe care se bazează §16.3 din `CLAUDE.md`.

   Comanda de build și variabilele de mediu (`PYTHON_VERSION`, `SITE_BASE`) stau în Workers Builds → Settings. *(GEMINI nu e necesar aici — render-only nu apelează AI.)*

Astfel: Actions face fetch+AI și salvează starea → commit-ul declanșează Cloudflare → Cloudflare randează rapid (fără AI/quota) și publică. Cron-ul de auto-actualizare vine din Actions.

*Migrat de pe Cloudflare Pages pe Workers în #211 (2026-08-22); descrierea de mai sus a rămas pe Pages până pe 2026-08-30.*

### Domeniul izz.ro
1. În Cloudflare „Add a site" → izz.ro → primești 2 nameservere.
2. La registrar (ICI/ROTLD) setezi acele nameservere pentru izz.ro.
3. În Workers → serviciul izz-ro → Domains & Routes → adaugi izz.ro.

### Comutare pe Claude API
Adaugă secret `ANTHROPIC_API_KEY` în GitHub și pune `AI_PROVIDER: anthropic` în `build.yml`.

### Comutare pe Claude API
Adaugă secret `ANTHROPIC_API_KEY` și pune `AI_PROVIDER: anthropic` în `build.yml`. Restul rămâne identic.

## Router multi-provider (opțional)

Fluxul implicit rămâne `Gemini -> Ollama local fallback`, compatibil cu configurația existentă. Routerul multi-provider se activează numai explicit, cu `AI_ROUTER_MODE=multi`, și folosește ordinea din `AI_FALLBACK_PROVIDERS`. Sunt suportate endpointuri OpenAI-compatible pentru `groq`, `cerebras`, `mistral`, `openrouter`, `perplexity` și `upstage`; fiecare provider este ignorat automat dacă nu are cheia proprie în mediu. Cheile nu se comit și nu sunt incluse în configurația GitHub.

Exemplu local de activare, după validarea fluxului legacy:

```shell
AI_ROUTER_MODE=multi
AI_FALLBACK_PROVIDERS=groq,cerebras,mistral,openrouter
```

Routerul este o cascadă: încearcă providerul principal configurat, apoi providerii compatibili configurați în ordinea declarată, apoi fallback-ul Ollama dacă este activ. Un provider configurat dar fără cheie nu este apelat. Pentru CI, adăugarea de provideri se face ulterior, prin secrete separate și un test controlat; nu se schimbă implicit `AI_PROVIDER=gemini`.

## Controale autonome de calitate

Calitatea editorială și disponibilitatea nu depind de intervenția manuală a unui agent. Repository-ul rulează controale deterministe direct în GitHub Actions, iar o execuție eșuată devine vizibilă administratorului în pagina Actions și prin notificările GitHub configurate pentru repository.

| Control | Când rulează | Ce blochează sau semnalează |
|---|---|---|
| `tests.yml` | La orice pull request și la schimbări de cod pe `main` | Lint, teste Python, contractul titlurilor oficiale, randare și integritate HTML |
| `build.yml` → `QA check` | După fiecare actualizare automată de conținut | Surse incoerente, categorii goale și orice titlu oficial afișat peste 110 caractere sau gol |
| `editorial-quality.yml` | Zilnic la 06:37 UTC și la rulare manuală | Audit independent al titlurilor, raport JSON păstrat 30 de zile și verificarea corpusului publicabil |
| `monitor.yml` | Periodic, independent de deploy | Lipsa răspunsului pentru domeniul public sau indisponibilitatea simultană a ambelor origini |
| `build.yml` → `release-probe` | După publicarea unei actualizări | Nepotrivirea dintre commitul publicat și manifestul `/build.json` de pe Pages și `izz.ro` |

### Contractul titlurilor oficiale

`tools/title_quality_audit.py` este verificarea autonomă a regulii de lectură mobilă. Rulează fără apeluri AI și fără servicii externe:

```bash
python tools/title_quality_audit.py
python tools/title_quality_audit.py --report title-quality-report.json
```

Un rezultat reușit garantează că titlul de afișare al fiecărui anunț oficial este nevid și are cel mult **110 caractere**. Titlul instituției rămâne neschimbat în `data/articles.json`; reducerea se aplică doar în câmpul de afișare calculat la randare. Dacă regula este încălcată, workflow-ul eșuează și administratorul are în raport exemplele concrete care necesită corectare.

> Programarea GitHub este potrivită pentru controalele zilnice de consistență. Pentru detectare garantată la minut a indisponibilității externe ar fi necesar un serviciu de monitorizare dedicat, configurat separat la nivel de cont.

### Răspuns operațional fără agent

Nu este necesară nicio acțiune la fiecare rulare verde. Dacă un workflow devine roșu, administratorul deschide execuția din GitHub Actions, descarcă artefactul `title-quality-report` când este disponibil și corectează articolul sau regula indicată. După un commit, testele și verificarea release-ului rulează din nou automat.
