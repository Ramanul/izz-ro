"""Mini-harta puls pentru homepage (Faza 2).

SVG static, ZERO JS: judetele incalzite dupa volumul de stiri locale din ultimele 24h.
Reutilizeaza cache-ul de contururi din data/harta_judete.json (acelasi ca /surse/).

Hook pe render._base_ctx (instalat din home_fresh la primul apel): injecteaza
`mini_harta` in contextul paginii de index cand exista `zi`.
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
        # Strict > (nu >=): altfel valoarea egală cu pragul inferior sare o treaptă
        # (ex. BRASOV=1 cu praguri [1,2,3] devenea h2 în loc de h1).
        treapta = 0 if c == 0 else 1 + sum(1 for p in praguri if c > p)
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


def install_hook() -> None:
    """Injecteaza mini_harta in contextul Jinja cand exista zi (homepage).

    Ataseaza si render._mini_harta pentru teste. Idempotent.
    """
    from generator import render as r

    r._mini_harta = mini_harta
    if getattr(r, "_faza2_hooked", False):
        return
    if not hasattr(r, "_base_ctx"):
        raise RuntimeError("render._base_ctx inca nedefinit")

    _orig = r._base_ctx

    def _base_ctx_wrapped(canonical_path: str, jsonld_nodes=None, jsonld_page=None, **extra):
        if "zi" in extra and "mini_harta" not in extra:
            zi = extra.get("zi")
            if zi and isinstance(zi, dict):
                extra["mini_harta"] = mini_harta(zi.get("pe_judet") or {})
            else:
                extra["mini_harta"] = None
        return _orig(
            canonical_path,
            jsonld_nodes=jsonld_nodes,
            jsonld_page=jsonld_page,
            **extra,
        )

    r._base_ctx = _base_ctx_wrapped
    r._faza2_hooked = True
