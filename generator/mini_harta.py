"""Mini-harta puls pentru homepage (Faza 2).

SVG static, ZERO JS: judetele incalzite dupa volumul de stiri locale din ultimele 24h.
Reutilizeaza cache-ul de contururi din data/harta_judete.json (acelasi ca /surse/).
"""
from __future__ import annotations

import json
import os

from . import config, geo

_HARTA_CACHE: dict | None = None


def _load_harta() -> dict:
    global _HARTA_CACHE
    if _HARTA_CACHE is None:
        try:
            with open(os.path.join(config.ROOT, "data", "harta_judete.json"),
                      encoding="utf-8") as fh:
                _HARTA_CACHE = json.load(fh)
        except (OSError, ValueError):
            _HARTA_CACHE = {}
    return _HARTA_CACHE or {}


def mini_harta(pe_judet: dict | None) -> dict | None:
    """Mini-harta „puls": SVG static, trepte h0-h4 pe cuartele volumului.

    None cand nu exista stiri judetene sau lipseste conturul.
    """
    if not pe_judet:
        return None
    cache = _load_harta()
    if not cache.get("judete"):
        return None
    max_c = max(pe_judet.values())
    praguri = sorted({max_c * q // 4 for q in (1, 2, 3)} - {0})
    forme = []
    for judet, d in cache["judete"].items():
        c = pe_judet.get(judet, 0)
        treapta = 0 if c == 0 else 1 + sum(1 for p in praguri if c >= p)
        forme.append({
            "judet": judet,
            "label": geo.eticheta_judet(judet),
            "d": d,
            "count": c,
            "treapta": treapta,
        })
    return {
        "viewbox": cache.get("viewbox", "0 0 1000 704"),
        "forme": forme,
        "total": sum(pe_judet.values()),
    }
