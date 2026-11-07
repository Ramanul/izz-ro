# Analiza multidimensională IZZ.ro — 2026-11-07

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
