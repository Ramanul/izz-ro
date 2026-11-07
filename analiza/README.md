# Analiza și propunerile IZZ.ro — 2026-11-07

## Analiza multidimensională

| Fișier | Ce este |
|---|---|
| `2026-11-07-analiza-multidimensionala.md` | Raportul: 10 dimensiuni, măsurători, riscuri, propuneri prioritizate, plan 30/90/365 |
| `masuratori.json` | Cifrele brute ale analizei (generate, nu scrise de mână) |
| `masuratori.py` | Scriptul care le reproduce, pe `output/` + `data/articles.json` (stdlib only) |

Reproducere:

```bash
python -m generator.main --render-only   # output/ real, ~49 s
cat output/build.json                    # article_count trebuie sa fie ~6500
python analiza/masuratori.py             # rescrie masuratori.json
```

Atenție: `pytest` re-randează `output/` cu un fixture de ~190 de articole. Nu rula
testele între randare și măsurători, altfel cifrele descriu fixture-ul, nu site-ul.

## Propunerea de rebranding vizual

| Fișier | Ce este |
|---|---|
| `rebranding/PROPUNERE.md` | Raționamentul, cele trei direcții, tokenii vechi→nou, planul pe faze, riscurile |
| `rebranding/index.html` | Macheta interactivă (direcții · prima pagină · articol · sistem) |
| `rebranding/fonts/` | Newsreader variabilă (OFL) + Inter 400/600, doar pentru machetă |
| `rebranding/img/` | două fotografii CC0 din `output/leads/`, pentru machetă |

Vizualizare locală:

```bash
python -m http.server 8080 --directory analiza/rebranding
# → http://localhost:8080
```
