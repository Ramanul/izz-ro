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

## Deploy
GitHub Actions (`.github/workflows/build.yml`) rulează pipeline-ul, comite `data/articles.json` și publică `output/` pe **GitHub Pages**. Secrete necesare (repo → Settings → Secrets → Actions):
- `GEMINI_API_KEY` — cheia AI (altfel: fallback).
- `CF_ANALYTICS_TOKEN` — *opțional*, analytics cookieless.

### Trecere pe domeniul izz.ro (Cloudflare) — mai târziu
1. Cont Cloudflare + adaugă izz.ro + schimbă nameserverele la registrar.
2. Pages: poți comuta deploy-ul pe Cloudflare (token + Account ID) sau lega izz.ro ca *custom domain* peste GitHub Pages.
3. Setează `SITE_BASE=""` (gol) pentru domeniu la rădăcină.

### Comutare pe Claude API
Adaugă secret `ANTHROPIC_API_KEY` și pune `AI_PROVIDER: anthropic` în `build.yml`. Restul rămâne identic.
