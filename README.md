# IZZ.ro — Informația Zero Zgomot

> **Portalul știrilor tale** · [izz.ro](https://izz.ro)

Agregator de știri românești construit pe o promisiune simplă: **mai puțin zgomot, mai multă informație**. Titlurile sunt reformulate faptic, fără cârlige emoționale. Rezumatele sunt scrise cu cuvinte proprii și duc întotdeauna la sursa originală. Când mai multe publicații relatează același eveniment, subiectul apare o singură dată, cu toate sursele enumerate. Imaginile sunt grafică generată pentru fiecare articol, nu fotografii preluate.

Site-ul este **100% static (SSG)**, publicat serverless: pipeline-ul rulează în GitHub Actions, publicarea se face prin Cloudflare Workers. Fără server propriu, fără baze de date gestionate, fără publicitate.

---

## Ce oferă site-ul

- **Trei tipuri de conținut**, afișate explicit pe fiecare card: *Sinteză multi-sursă* (mai multe publicații despre același eveniment), *Rezumat dintr-o sursă* (un singur articol de referință) și *Anunț oficial* (textul integral se citește la instituția emitentă).
- **Categoriile:** Național · Regional · Județean · Local · Politică · Economie · Externe · Sport · Inteligență artificială · Tech · Auto · Sănătate · Cultură · Lifestyle · Discounturi · Ghiduri.
- **Harta știrilor** — acoperirea județeană, vizualizată pe hartă.
- **„Ce urmează"** (`/calendar/`) — calendarul evenimentelor care urmează în știri.
- **Instrumente** — utilitare, inclusiv calculator de salariu.
- **Căutare** (`/cauta/`) și **RSS** (`/feed.xml`).
- **PWA instalabilă** (manifest `static/site.webmanifest`, pictograme dedicate) și temă cu comutare deschis/închis.
- **Pagini publice de transparență:** Cum sintetizăm (metodologia), Surse & originalitate, Corecții, Securitate, Politica imaginilor, Drepturi de autor.

## Arhitectura pipeline-ului

```
Surse RSS (SOURCES din generator/config.py)
  │
  ├─ fetch.py       descărcare fluxuri
  ├─ state.py       stare, dedup, expirare        → data/articles.json (comis în repo)
  ├─ cluster.py     grupare multi-sursă
  ├─ select.py      selecție editorială
  ├─ process.py     sinteză AI (model B/C)
  ├─ covers.py      grafică proprie per articol
  ├─ moderation.py  filtrare editorială          → moderation.yaml (om în buclă)
  └─ render.py      randare Jinja2               → output/
```

Modelul de conținut **B+C** corespunde celor două tipuri vizibile pe site: rezumat dintr-o sursă (**B**) și sinteză multi-sursă (**C**). Starea persistă între rulări prin `data/articles.json`, comis în repo — nu există bază de date externă.

## Rulare local

```bash
pip install -r requirements.txt

# Pipeline complet (RSS → AI → HTML în output/) + salvează starea
python -m generator.main

# Doar test, fără salvare sau randare (afișează rezultatul + sursele RSS moarte)
python -m generator.main --dry-run

# Vizualizare locală
python -m http.server 8000 --directory output
# → http://localhost:8000
```

Fără cheie AI, pipeline-ul folosește un **fallback determinist** (rezumat din descrierea RSS) — util pentru testat structura. Pentru reformulare reală, pune `GEMINI_API_KEY` în `.env` (vezi `.env.example`).

## Structura repo-ului

```
generator/   pipeline-ul: fetch · state · cluster · select · process (AI B/C)
             covers · moderation · render · main · providers/
templates/   Jinja2 (autoescape ON): base · index · article · category · legal
             search · calendar · instrumente · calculator · ghid/ghiduri · surse
             sectiuni · subject · _card
static/      styles.css (temă auriu-dark) · logo · favicon · og-image · pictograme
             PWA · site.webmanifest · theme.js · search.js · calc-salariu.js
             fonts/ · harta-stiri/
content/     pagini legale și metodologice (markdown): method (Cum sintetizăm),
             terms, privacy, corrections, security, images, takedown,
             accessibility, contact
data/        articles.json — starea comisă în repo
moderation.yaml   control editorial (om în buclă) — vezi REVIEW.md
infra/       Worker de failover pentru redundanța originii (vezi infra/README-failover.md)
tools/       utilitare operaționale: qa_check, feed_check, verify_release,
             title_quality_audit, build_harta*, indexnow_submit etc.
tests/       teste Python
.github/     workflows (build, tests, monitor, editorial-quality, security…)
```

Documente de proiect comise: `CLAUDE.md` și `AGENTS.md` (reguli pentru dezvoltare asistată de agenți AI), `REVIEW.md` (fluxul de moderare), `REGULI-SINTEZA.md` (regulile de sinteză), `specs/`, `notes/`, `sessions/` (istoric de lucru intern).

## Configurare

- **Surse RSS, praguri B/C, TTL, max/sursă:** `generator/config.py`.
- **Ce apare pe site:** `moderation.yaml` (fluxul e descris în `REVIEW.md`).
- **Chei AI:** în `.env` local / secrete GitHub — nu se comit niciodată.

## AI: provideri și router

| Scenariu | Configurare |
|---|---|
| Implicit | `GEMINI_API_KEY` (secret GitHub sau `.env`) · fluxul `Gemini → Ollama local fallback` |
| Claude API | secret `ANTHROPIC_API_KEY` + `AI_PROVIDER: anthropic` în `build.yml` |
| Router multi-provider (opțional) | `AI_ROUTER_MODE=multi` + `AI_FALLBACK_PROVIDERS=groq,cerebras,mistral,openrouter` |
| Fără cheie | fallback determinist din descrierea RSS |

Routerul multi-provider este o cascadă: providerul principal configurat, apoi providerii din `AI_FALLBACK_PROVIDERS` în ordinea declarată (endpointuri OpenAI-compatible), apoi Ollama dacă e activ. Un provider fără cheie proprie este ignorat automat; implicit rămâne `AI_PROVIDER=gemini`. Exemplu local:

```shell
AI_ROUTER_MODE=multi
AI_FALLBACK_PROVIDERS=groq,cerebras,mistral,openrouter
```

## Publicare (GitHub Actions + Cloudflare Workers)

Arhitectura separă **munca grea** de **publicare**:

1. **GitHub Actions** — `.github/workflows/build.yml`, cron `13 * * * *`: rulează pipeline-ul (fetch + AI, cu buget per rulare) și comite `data/articles.json` în repo. Secret necesar: `GEMINI_API_KEY`.
   **Încearcă orar, publică la ~2h:** un job de poartă taie rularea dacă ultimul conținut e mai proaspăt de 105 minute. Cron-ul orar dens acoperă firings-urile sărite de planificatorul GitHub; pragul păzește și bugetul lunar de build Cloudflare (≈500 rulări pe planul gratuit).
2. **Cloudflare Workers Static Assets** (Workers Builds, conectat la repo, auto-deploy la fiecare commit): rulează doar **render-only** și servește `output/`. Configurația versionată stă în `wrangler.jsonc`:
   - `assets.directory: ./output` — proiect assets-only, fără `main`;
   - `not_found_handling: "404-page"` — fără linia asta, `output/404.html` nu ar fi servit niciodată;
   - `preview_urls: true` — preview per ramură.

   Comanda de build și variabilele de mediu (`PYTHON_VERSION`, `SITE_BASE`) stau în Workers Builds → Settings. GEMINI nu e necesar aici — render-only nu apelează AI.

Fluxul: Actions face fetch + AI și salvează starea → commit-ul declanșează Cloudflare → Cloudflare randează rapid (fără AI/quota) și publică pe **izz.ro**. *(Migrat de pe Cloudflare Pages pe Workers în august 2026.)*

### Domeniul izz.ro

1. Cloudflare → „Add a site" → izz.ro → primești două nameservere.
2. La registrar (ICI/ROTLD) setezi acele nameservere pentru izz.ro.
3. Workers → serviciul izz-ro → Domains & Routes → adaugi izz.ro.

## Controale autonome de calitate

Calitatea editorială și disponibilitatea nu depind de intervenția manuală. Verificările deterministe rulează în GitHub Actions; o execuție eșuată devine vizibilă în pagina Actions și prin notificările GitHub.

| Verificare | Declanșare | Ce verifică |
|---|---|---|
| `tests.yml` | PR-uri și schimbări de cod pe `main` | lint (ruff), teste Python, contractul titlurilor, randare, integritate HTML |
| `QA check` (în `build.yml`) | după fiecare actualizare de conținut | surse incoerente, categorii goale, titluri oficiale goale sau peste 110 caractere |
| `editorial-quality.yml` | zilnic, 06:37 UTC + manual | audit independent al titlurilor, raport JSON reținut 30 de zile |
| `monitor.yml` | periodic, independent de deploy | lipsa răspunsului pe domeniul public sau căderea simultană a ambelor origini |
| `release-probe` (în `build.yml`) | după publicare | potrivirea commitului publicat cu manifestul `/build.json` servit pe izz.ro |

Repo-ul include și analiză statică de securitate (CodeQL, Semgrep), verificarea dependențelor (Dependabot) și sonde de fum/trafic (smoke, visual, probe, trafic).

### Contractul titlurilor oficiale

`tools/title_quality_audit.py` verifică regula de lectură mobilă, fără apeluri AI și fără servicii externe:

```bash
python tools/title_quality_audit.py
python tools/title_quality_audit.py --report title-quality-report.json
```

Un rezultat reușit garantează că titlul de afișare al fiecărui anunț oficial este nevid și are cel mult **110 caractere**. Titlul instituției rămâne neschimbat în `data/articles.json`; reducerea se aplică doar câmpului de afișare, calculat la randare. Dacă regula este încălcată, workflow-ul eșuează și raportul conține exemplele concrete care necesită corectare.

Programarea GitHub acoperă controalele zilnice de consistență; pentru detectare garantată la minut a indisponibilității externe ar fi necesar un serviciu de monitorizare dedicat, configurat separat la nivel de cont.

### Răspuns operațional

Nu este necesară nicio acțiune la rulările verzi. Dacă un workflow devine roșu: deschide execuția din GitHub Actions, descarcă artefactul `title-quality-report` când e disponibil și corectează articolul sau regula indicată. După un commit, testele și verificarea release-ului rulează din nou automat.

## Proiectul

- **Independent**, operat de o persoană fizică din România; nu aparține niciunui trust de presă, fără afilieri politice sau comerciale, fără publicitate.
- Agregă exclusiv **publicații cu flux RSS public**; agențiile de presă (conținut licențiat) sunt excluse.
- **Metodologia este publică:** [Cum sintetizăm](https://izz.ro/despre/) și [Surse & originalitate](https://izz.ro/surse/).
- Contact: **contact@izz.ro** sau pagina [Contact](https://izz.ro/contact/).
