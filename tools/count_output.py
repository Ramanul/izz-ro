#!/usr/bin/env python3
"""Numara fisierele din `output/` si desparte articolele de rest.

De ce exista: `config.OUTPUT_NON_ARTICLE_RESERVE` e o cifra masurata, iar o cifra
masurata imbatraneste. Fiecare rubrica noua, pagina de ghid sau feed de subiect o
creste fara ca nimeni sa observe -- pana cand randarea imparte un buget de imagini
pe baza unei rezerve prea mici si output-ul trece plafonul gazdei.

Ruleaza dupa `python -m generator.main --render-only` si compara cu configul.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import config  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


def masoara(out_dir: str = OUT) -> dict:
    """Imparte fisierele in `articol` (sub <categorie>/<slug>/) si `rest`."""
    cats = set(config.CATEGORIES)
    articol = rest = 0
    per_ext: dict[str, int] = {}
    for dirpath, _, files in os.walk(out_dir):
        rel = os.path.relpath(dirpath, out_dir)
        parts = [] if rel == "." else rel.split(os.sep)
        # un director de articol e exact <categorie>/<slug>, doua niveluri sub radacina
        e_articol = len(parts) == 2 and parts[0] in cats
        for f in files:
            if e_articol:
                articol += 1
                per_ext[os.path.splitext(f)[1]] = per_ext.get(os.path.splitext(f)[1], 0) + 1
            else:
                rest += 1
    return {"total": articol + rest, "articol": articol, "rest": rest, "per_ext": per_ext}


def main() -> int:
    if not os.path.isdir(OUT):
        print("output/ nu exista -- ruleaza intai: python -m generator.main --render-only")
        return 2
    m = masoara()
    print(f"total fisiere      : {m['total']}")
    print(f"  in articole      : {m['articol']}")
    print(f"  in afara lor     : {m['rest']}   <- asta e OUTPUT_NON_ARTICLE_RESERVE")
    print(f"buget configurat   : {config.OUTPUT_FILE_BUDGET}")
    print(f"rezerva configurata: {config.OUTPUT_NON_ARTICLE_RESERVE}")
    for ext, k in sorted(m["per_ext"].items(), key=lambda t: -t[1]):
        print(f"  {ext or '(fara)':<8} {k}")
    if m["rest"] > config.OUTPUT_NON_ARTICLE_RESERVE:
        print(f"\nREZERVA PREA MICA cu {m['rest'] - config.OUTPUT_NON_ARTICLE_RESERVE} fisiere.")
        return 1
    if m["total"] > config.OUTPUT_FILE_BUDGET:
        print(f"\nPESTE BUGET cu {m['total'] - config.OUTPUT_FILE_BUDGET} fisiere.")
        return 1
    print(f"\nsub buget, marja {config.OUTPUT_FILE_BUDGET - m['total']} fisiere.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
