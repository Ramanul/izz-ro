"""Ruleaza verificarile mecanice pe corpusul EXISTENT si raporteaza cifre.

Nu modifica nimic. Scopul e sa stabilim pragul de respingere din date reale, nu ghicit —
vezi antetul din `generator/verifica_sinteza.py`.

    python tools/masoara_sinteza.py [cale_articles.json] [--exemple N]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generator.verifica_sinteza import verifica  # noqa: E402


def sursa_pentru(a: dict) -> str:
    """Textul pe care l-a VAZUT modelul, reconstituit din campurile pastrate in stare.

    Pentru fluxul B asta e titlul original + descrierea. Pentru C (multi-sursa) campurile
    per-sursa nu se pastreaza integral in stare, deci articolele alea se numara separat ca
    NEVERIFICABILE — a le trece drept curate ar fi o cifra falsa.
    """
    return f"{a.get('original_title') or ''} {a.get('description') or ''}".strip()


def main() -> int:
    cale = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("-") \
        else Path(__file__).resolve().parents[1] / "data" / "articles.json"
    nr_exemple = 5
    if "--exemple" in sys.argv:
        nr_exemple = int(sys.argv[sys.argv.index("--exemple") + 1])

    if not cale.exists():
        print(f"NU EXISTA: {cale}")
        return 1

    articole = json.loads(cale.read_text(encoding="utf-8"))
    if isinstance(articole, dict):
        articole = articole.get("articles") or articole.get("items") or []

    total = len(articole)
    neverificabile = 0
    fara_ai = 0
    verificate = 0
    coduri = Counter()
    cu_probleme = 0
    exemple: dict[str, list] = {}

    for a in articole:
        if a.get("processed_by") in ("official", "fallback"):
            fara_ai += 1
            continue
        sursa = sursa_pentru(a)
        if not sursa or a.get("model") == "C":
            neverificabile += 1
            continue
        verificate += 1
        rezumat = a.get("synthesis") if a.get("model") == "C" else a.get("teaser")
        probleme = verifica(a.get("title"), rezumat, sursa)
        if probleme:
            cu_probleme += 1
        for p in probleme:
            coduri[p.cod] += 1
            exemple.setdefault(p.cod, [])
            if len(exemple[p.cod]) < nr_exemple:
                exemple[p.cod].append({
                    "titlu": (a.get("title") or "")[:90],
                    "detaliu": p.detaliu,
                    "sursa": sursa[:140],
                })

    print(f"total articole in corpus       : {total}")
    print(f"  fara AI (official/fallback)  : {fara_ai}")
    print(f"  neverificabile (sursa lipsa) : {neverificabile}")
    print(f"  VERIFICATE                   : {verificate}")
    if not verificate:
        print("\nnimic de masurat")
        return 0
    proc = 100 * cu_probleme / verificate
    print(f"\narticole cu cel putin o problema: {cu_probleme} din {verificate} ({proc:.1f}%)")
    print("\nsemnale, pe cod:")
    for cod, n in coduri.most_common():
        print(f"  {cod:<18} {n:>5}  ({100 * n / verificate:.1f}% din verificate)")

    for cod, lista in exemple.items():
        print(f"\n--- exemple: {cod} ---")
        for e in lista:
            print(f"  titlu  : {e['titlu']}")
            print(f"  detaliu: {e['detaliu']}")
            print(f"  sursa  : {e['sursa']}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
