#!/usr/bin/env python3
"""Masoara atribuirea (categorie + loc pe badge) pe setul de aur. Cifra, nu impresie.

De ce exista: pana acum fiecare masuratoare de clasificare a fost aruncata dupa ce a fost facuta,
deci nimeni nu putea spune „am reparat" — doar „am schimbat". Cu 663 de articole care au stat pe
rubrica gresita saptamani intregi fara ca cineva sa afle (vezi `specs/atribuire-cercetare-si-plan.md`
C7/C8), lipsa masuratorii E defectul, nu un lux.

Ruleaza:  python tools/eval_atribuire.py [--verbose]
Iesire:   doua fractii — categoria corecta si locul de pe badge — plus rândurile picate.

Compara starea de ACUM a codului cu judecata manuala din `specs/gold-geo-*.tsv`. Nu foloseste
coloana `badge_verdict` din TSV ca adevar: aia a fost data pe codul de la momentul judecatii, iar
codul se schimba. Adevarul e `cat_corecta` + `loc_corect`, care sunt judecati despre STIRE, nu
despre cod, deci nu expira.
"""
import argparse
import csv
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from generator import geo, htmlart  # noqa: E402
from generator.util import strip_diacritics  # noqa: E402


def _norm(s: str) -> str:
    return strip_diacritics(s or "").strip().lower()


def _gold(path: str | None = None) -> list[dict]:
    """Cel mai recent set de aur din `specs/`, sau cel indicat."""
    if not path:
        cand = sorted(glob.glob(os.path.join(ROOT, "specs", "gold-geo-*.tsv")))
        if not cand:
            raise SystemExit("!! niciun specs/gold-geo-*.tsv")
        path = cand[-1]
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def _articole() -> dict:
    """{url: articol} din starea pipeline-ului."""
    with open(os.path.join(ROOT, "data", "articles.json"), encoding="utf-8") as fh:
        date = json.load(fh)
    lst = date if isinstance(date, list) else (date.get("articles") or [])
    return {a["url"]: a for a in lst if isinstance(a, dict) and a.get("url")}


def evalueaza(verbose: bool = False) -> int:
    rows, arts = _gold(), _articole()
    lipsa = [r for r in rows if r["url"] not in arts]
    prezente = [r for r in rows if r["url"] in arts]

    cat_ok = loc_ok = loc_total = 0
    picate = []
    for r in prezente:
        a = arts[r["url"]]
        # 1. Categoria stocata vs cea judecata manual
        if _norm(a.get("category")) == _norm(r["cat_corecta"]):
            cat_ok += 1
        else:
            picate.append(("CAT", r["idx"], f"{a.get('category')} != {r['cat_corecta']}",
                           (a.get("title") or "")[:52]))
        # 2. Locul de pe badge — doar unde exista un loc corect de asteptat
        astept = r["loc_corect"].strip()
        if not astept:
            continue
        loc_total += 1
        badge = htmlart._eticheta(a)
        if _norm(astept) in _norm(badge) or _norm(badge) in _norm(astept):
            loc_ok += 1
        else:
            picate.append(("LOC", r["idx"], f"badge={badge!r} != {astept!r}",
                           (a.get("title") or "")[:52]))

    n = len(prezente)
    print(f"set de aur: {len(rows)} randuri, {n} inca in articles.json"
          + (f", {len(lipsa)} expirate (ignorate)" if lipsa else ""))
    print(f"  categorie corecta : {cat_ok}/{n}" + (f"  ({cat_ok/n:.0%})" if n else ""))
    print(f"  loc corect pe badge: {loc_ok}/{loc_total}"
          + (f"  ({loc_ok/loc_total:.0%})" if loc_total else ""))
    if verbose and picate:
        print("\n  picate:")
        for tip, idx, ce, titlu in picate:
            print(f"    [{tip}] #{idx:>2}  {ce}\n           {titlu}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--verbose", "-v", action="store_true")
    sys.exit(evalueaza(p.parse_args().verbose))
