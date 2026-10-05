"""Mini-harta puls pentru homepage (Faza 2).

SVG static, ZERO JS: judetele incalzite dupa volumul de stiri locale din ultimele 24h.
Contoarele vin din datasetul hartii mari (map.json — aceeasi atribuire geografica, deci
cele doua harti nu se contrazic); fallback: judetul sursei din `zi.pe_judet`.
Reutilizeaza cache-ul de contururi din data/harta_judete.json (acelasi ca /surse/).

Hook pe render._base_ctx (instalat din home_fresh la primul apel): injecteaza
`mini_harta` in contextul paginii de index cand exista `zi`.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

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


_DATASET_CACHE: dict | None = None


def _load_dataset() -> dict:
    """Datasetul hartii mari (static/harta-stiri/data/map.json), gol daca nu exista."""
    global _DATASET_CACHE
    if _DATASET_CACHE is None:
        try:
            with open(
                os.path.join(config.ROOT, "static", "harta-stiri", "data", "map.json"),
                encoding="utf-8",
            ) as fh:
                _DATASET_CACHE = json.load(fh)
        except (OSError, ValueError):
            _DATASET_CACHE = {}
    return _DATASET_CACHE or {}


def _counts_din_dataset(ore: int = 24) -> dict | None:
    """Contoare pe judet din datasetul hartii mari, fereastra `ore` ore.

    Sursa de adevar e ACEEASI atribuire geografica ca pe /static/harta-stiri/ — mini-harta
    si harta mare nu mai pot spune lucruri diferite despre acelasi judet (pana la 3 oct
    mini-harta folosea judetul sursei, harta mare geocodarea din text, iar OLT aparea
    unde nu era). None doar cand datasetul lipseste: atunci ramane fallback-ul istoric.
    """
    articles = _load_dataset().get("articles")
    if not isinstance(articles, list):
        return None
    prag = datetime.now(timezone.utc) - timedelta(hours=ore)
    counts: dict[str, int] = {}
    for a in articles:
        judet = a.get("county")
        if not judet:
            continue
        try:
            dt = datetime.fromisoformat(str(a.get("published") or ""))
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= prag:
            counts[judet] = counts.get(judet, 0) + 1
    return counts


def mini_harta(pe_judet: dict | None) -> dict | None:
    """Mini-harta „puls": SVG static, trepte h0-h4 pe sferturile volumului ZILEI.

    De ce NU pragurile absolute ale hartii mari (1/6/15/30, vezi `PRAGURI` din
    harta-stiri.js): fereastra e de 24 de ore, iar pe un interval atat de scurt aproape
    toate județele cad sub 6 stiri -- scara absoluta ar face harta aproape uniforma si
    inutila. Intrebarea pulsului e „cine e sus azi", deci treapta e RELATIVA la ziua
    curenta (cuartile), iar captionul paginii spune asta explicit. Culorile sunt insa
    identice (`.puls-map path.h0..h4` = `--map-h0..h4`), ca cele doua harti sa se citeasca
    ca un singur sistem.

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
            # Metodologie unica: contoarele vin din datasetul hartii mari (aceeasi
            # geocodare). `zi.pe_judet` (judetul sursei) rămâne doar fallback daca
            # datasetul nu poate fi citit, ca pagina sa nu ramana fara harta.
            counts = _counts_din_dataset()
            if counts is None:
                zi = extra.get("zi")
                counts = (zi.get("pe_judet") or {}) if isinstance(zi, dict) else {}
            extra["mini_harta"] = mini_harta(counts)
        return _orig(
            canonical_path,
            jsonld_nodes=jsonld_nodes,
            jsonld_page=jsonld_page,
            **extra,
        )

    r._base_ctx = _base_ctx_wrapped
    r._faza2_hooked = True
