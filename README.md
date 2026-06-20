# IZZ.ro — Informația Zero Zgomot

Agregator de știri românești anti-clickbait. Site **static (SSG)**, model de conținut **B+C** (rezumat scurt + link / sinteză multi-sursă), publicat **serverless**: GitHub Actions construiește și deployează automat la fiecare 30 de minute. AI implicit **Gemini** (gratuit), comutabil pe **Claude API**.

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
- **Surse RSS:** `generator/config.py` -> `SOURCES`. (`gsp` dă 404 — de înlocuit cu un feed valid.)
- **Praguri B/C, TTL, max/sursă:** tot în `config.py`.

## Deploy (GitHub Actions + Cloudflare Pages)

Arhitectura separă **munca grea** de **publicare**:

1. **GitHub Actions** (`.github/workflows/build.yml`, cron 30 min): rulează pipeline-ul (fetch + AI, cu buget per rulare), apoi **comite** `data/articles.json` în repo. Secret necesar: `GEMINI_API_KEY` (repo → Settings → Secrets → Actions).
2. **Cloudflare Pages** (conectat la repo, auto-deploy la fiecare commit): rulează doar **render-only** și publică `output/`. Setări în Cloudflare Pages → Settings:
   - **Build command:** `pip install -r requirements.txt && python -m generator.main --render-only`
   - **Build output directory:** `output`
   - **Environment variables:** `PYTHON_VERSION=3.11`, `SITE_BASE=` (gol). *(GEMINI nu e necesar aici — render-only nu apelează AI.)*

Astfel: Actions face fetch+AI și salvează starea → commit-ul declanșează Cloudflare → Cloudflare randează rapid (fără AI/quota) și publică. Cron-ul de auto-actualizare vine din Actions.

### Domeniul izz.ro
1. În Cloudflare „Add a site" → izz.ro → primești 2 nameservere.
2. La registrar (ICI/ROTLD) setezi acele nameservere pentru izz.ro.
3. În Pages → proiectul izz-ro → Custom domains → adaugi izz.ro.

### Comutare pe Claude API
Adaugă secret `ANTHROPIC_API_KEY` în GitHub și pune `AI_PROVIDER: anthropic` în `build.yml`.

### Comutare pe Claude API
Adaugă secret `ANTHROPIC_API_KEY` și pune `AI_PROVIDER: anthropic` în `build.yml`. Restul rămâne identic.
