#!/usr/bin/env python3
"""Numara fisierele din `output/` exact cum le imparte bugetul din randare.

De ce exista: `config.OUTPUT_NON_ARTICLE_RESERVE` e o cifra masurata, iar o cifra
masurata imbatraneste. Fiecare rubrica, pagina de ghid sau feed de subiect nou o
creste fara ca nimeni sa observe -- pana cand randarea imparte bugetul de imagini pe
o rezerva prea mica si output-ul trece plafonul gazdei, tacut.

Clasificarea urmeaza MODELUL BUGETULUI, nu adancimea directorului: un director de
articol e cel al carui `<categorie>/<slug>` chiar apare in `data/articles.json`.
Prima versiune numara dupa adancime si punea paginile de paginare si de subiect la
"articole" -- 253 de fisiere clasificate gresit, si bugetul a iesit cu 183 peste.

Ruleaza dupa `python -m generator.main --render-only`.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import config  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")
IMAGINI = {"art.jpg", "art.webp", "art-card.webp", "cover.jpg"}


def _slugs_de_articol() -> set[tuple[str, str]]:
    with open(os.path.join(ROOT, "data", "articles.json"), encoding="utf-8") as fh:
        return {(a["category"], a["slug"]) for a in json.load(fh)
                if a.get("category") and a.get("slug")}


def masoara(out_dir: str = OUT) -> dict:
    """Imparte fisierele in pagini de articol, imagini de articol si rest."""
    articole = _slugs_de_articol()
    pagini = imagini = rest = 0
    for dirpath, _, files in os.walk(out_dir):
        rel = os.path.relpath(dirpath, out_dir)
        parts = [] if rel == "." else rel.split(os.sep)
        e_articol = len(parts) == 2 and (parts[0], parts[1]) in articole
        for f in files:
            if not e_articol:
                rest += 1
            elif f in IMAGINI:
                imagini += 1
            else:
                pagini += 1
    return {"total": pagini + imagini + rest, "pagini": pagini,
            "imagini": imagini, "rest": rest}


def main() -> int:
    if not os.path.isdir(OUT):
        print("output/ nu exista -- ruleaza intai: python -m generator.main --render-only")
        return 2
    m = masoara()
    print(f"total fisiere        : {m['total']}")
    print(f"  pagini de articol  : {m['pagini']}")
    print(f"  imagini de articol : {m['imagini']}")
    print(f"  rest               : {m['rest']}   <- asta e OUTPUT_NON_ARTICLE_RESERVE")
    print(f"buget configurat     : {config.OUTPUT_FILE_BUDGET}")
    print(f"rezerva configurata  : {config.OUTPUT_NON_ARTICLE_RESERVE}")
    iesire = 0
    if m["rest"] > config.OUTPUT_NON_ARTICLE_RESERVE:
        print(f"\nREZERVA PREA MICA cu {m['rest'] - config.OUTPUT_NON_ARTICLE_RESERVE} fisiere: "
              f"ridica OUTPUT_NON_ARTICLE_RESERVE la cel putin {m['rest']}.")
        iesire = 1
    if m["total"] > config.OUTPUT_FILE_BUDGET:
        print(f"\nPESTE BUGET cu {m['total'] - config.OUTPUT_FILE_BUDGET} fisiere.")
        iesire = 1
    if not iesire:
        print(f"\nsub buget, marja {config.OUTPUT_FILE_BUDGET - m['total']} fisiere.")
    return iesire


if __name__ == "__main__":
    raise SystemExit(main())
