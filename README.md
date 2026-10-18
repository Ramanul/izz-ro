# IZZ.ro — Informația Zero Zgomot

> **Știri românești, fără titluri-capcană.** · [izz.ro](https://izz.ro)

IZZ.ro adună știri din fluxuri RSS publice, rescrie titlurile și rezumă informația în limbaj factual. Când mai multe publicații relatează același eveniment, sinteza reunește relatările și păstrează linkurile către fiecare sursă originală. AI-ul ajută la colectare, grupare și redactarea inițială. Operatorul stabilește regulile editoriale și gestionează corecțiile; nu afirmăm că fiecare articol este citit individual de un om înainte de publicare.

[Metodologie](https://izz.ro/legal/method/) · [Surse](https://izz.ro/surse/) · [Corecții](https://izz.ro/legal/corrections/) · [Contact](https://izz.ro/legal/contact/)

## Ce oferă

- **Context, nu clickbait:** rezumate concise și titluri reformulate factual.
- **Surse la vedere:** fiecare articol trimite la publicația originală; relatările despre același eveniment pot fi grupate într-o sinteză multi-sursă.
- **Control editorial:** articolele sunt filtrate prin reguli editoriale și `moderation.yaml`.
- **Instrumente pentru cititori:** căutare, RSS, hartă, calendar, aplicație instalabilă cu citire offline și notificări push opționale, limitate la cel mult una pe zi.
- **Transparență:** metodologia, sursele, corecțiile și politicile proiectului sunt publice.

## Cum funcționează

```text
Fluxuri RSS → colectare și deduplicare → gruparea relatărilor
            → sinteză asistată de AI → aplicarea regulilor editoriale → site static
```

Generatorul este scris în Python, iar paginile sunt randate cu Jinja2. GitHub Actions rulează pipeline-ul și verificările; Cloudflare Workers publică site-ul static. Starea articolelor este versionată în `data/articles.json`, fără bază de date externă.

## Previzualizare locală

Poți randa o previzualizare din articolele deja salvate în repo, fără cheie AI:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m generator.main --render-only
python -m http.server 8000 --directory output
```

Deschide apoi [http://localhost:8000](http://localhost:8000). Pentru o rulare de dezvoltare cu RSS și sinteză AI, configurează `GEMINI_API_KEY` local, folosind `.env.example` ca model. `python -m generator.main --dry-run` este disponibil pentru o rulare de probă. Pipeline-ul complet poate actualiza starea din `data/articles.json`; verifică diff-ul înainte de orice commit.

## Verificări pentru dezvoltare

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -q
python -m ruff check .
```

Înainte de contribuții, citește [CONTRIBUTING.md](CONTRIBUTING.md). Regulile editoriale sunt în [REVIEW.md](REVIEW.md) și [REGULI-SINTEZA.md](REGULI-SINTEZA.md).

## Structura proiectului

- `generator/` — colectare RSS, stare, grupare, procesare AI, moderare și randare.
- `templates/`, `static/` — pagini HTML, stiluri și resurse pentru site.
- `content/` — pagini de metodologie și politici publice.
- `data/` — articolele și starea persistentă a pipeline-ului.
- `infra/`, `wrangler.jsonc` — Cloudflare Worker și configurarea publicării.
- `tests/`, `tools/`, `.github/workflows/` — teste, utilitare și automatizări.

## Proiectul

IZZ.ro este un proiect independent, fără publicitate și fără afiliere la trusturi de presă, partide politice sau interese comerciale. Agregă publicații cu fluxuri RSS publice; linkurile și metodologia sunt prezentate pe site. Pentru întrebări sau corecturi: [contact@izz.ro](mailto:contact@izz.ro).
