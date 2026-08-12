#!/usr/bin/env python
"""Genereaza datasetul static consumat de harta de stiri."""
from __future__ import annotations

import csv
import json
import os
import re
import unicodedata
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES = os.path.join(ROOT, "data", "articles.json")
MAP = os.path.join(ROOT, "data", "harta_judete.json")
SIRUTA = os.path.join(ROOT, "data", "siruta_raw.csv")
LOCALITIES = os.path.join(ROOT, "data", "harta_localitati.json")
OUT = os.path.join(ROOT, "static", "harta-stiri", "data", "map.json")
MAX_ARTICLES = 1500

STOPWORDS = {
    "UNIREA", "VICTORIA", "LIBERTATEA", "INDEPENDENTA", "PROGRESU", "PROGRESUL",
    "VIITORUL", "BISERICA", "BISERICANI", "GARA", "CENTRU", "PIATA", "VALEA",
    "DEALU", "DEALUL", "PADUREA", "LUNCA", "POIANA", "MOVILA", "IZVORU", "IZVORUL",
    "FANTANA", "FANTANELE", "PODURI", "PODUL", "MALU", "MALUL", "OSTROV", "SAT",
    "SATU", "SATUL", "SLOBOZIA", "RACOVITA", "COTU", "COASTA", "FRASIN", "FRUMOASA",
}
AMBIGUE = {
    "LUNA", "SAMBATA", "ROMAN", "BALA", "BANCA", "CURTEA", "VOLUNTARI", "TRAIAN",
    "VLADIMIR", "OVIDIU", "CRISTIAN", "BACIU", "DRAGUS", "CIOBANU", "FLORICA",
    "CATALINA", "MAIA", "AVRAM IANCU", "GEORGE ENESCU", "MIHAI BRAVU", "GRADINARI",
}
PREFIXES = ("MUNICIPIUL ", "ORASUL ", "ORAS ", "COMUNA ", "JUDETUL ", "SATUL ")


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", (value or "").strip())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.replace("Đ", "D").replace("đ", "d")
    value = re.sub(r"[^A-Za-z0-9]+", " ", value).upper().strip()
    return re.sub(r"\s+", " ", value)


def clean_name(value: str) -> str:
    name = norm(value)
    for prefix in PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):].strip()
    return name


def siruta_key(value: str) -> str:
    """Normalizeaza codul SIRUTA intre surse (ex. `32394,00` == `32394`)."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    return raw.split(",", 1)[0].strip().lstrip("0") or "0"


def read_siruta(county_alias: dict[str, str] | None = None) -> tuple[dict[str, str], dict[str, list[dict]]]:
    with open(SIRUTA, encoding="cp1250", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))

    county_alias = county_alias or {}
    counties: dict[str, str] = {}
    for row in rows:
        if row.get("NIV") != "1":
            continue
        code = str(row.get("JUD") or "").strip()
        name = clean_name(row.get("DENLOC") or "")
        if code and name:
            counties[code] = county_alias.get(norm(name), name)

    sat_names = [clean_name(r.get("DENLOC") or "") for r in rows if r.get("NIV") == "3"]
    counts: dict[str, int] = {}
    for name in sat_names:
        if name:
            counts[name] = counts.get(name, 0) + 1
    duplicate_sats = {name for name, count in counts.items() if count > 1}

    by_name: dict[str, list[dict]] = {}
    for row in rows:
        niv = str(row.get("NIV") or "")
        if niv not in {"2", "3"}:
            continue
        name = clean_name(row.get("DENLOC") or "")
        county = counties.get(str(row.get("JUD") or "").strip(), "")
        if not name or not county:
            continue
        if niv == "3" and (len(name) < 5 or name in STOPWORDS or name in AMBIGUE or name in duplicate_sats):
            continue
        siruta = ""
        for key in ("SIRUTA", "CODSIRUTA", "COD SIRUTA", "COD_SIRUTA", "COD_SIRUTA_LOCALITATE"):
            if row.get(key):
                siruta = str(row[key]).strip()
                break
        rec = {"name": name, "county": county, "siruta": siruta_key(siruta), "level": niv}
        by_name.setdefault(name, []).append(rec)
    return counties, by_name


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_locality_points() -> dict[str, dict]:
    if not os.path.exists(LOCALITIES) or os.path.getsize(LOCALITIES) == 0:
        return {}
    payload = load_json(LOCALITIES)
    return payload.get("localities") or {}


def point_for(locality: dict | None, points: dict[str, dict]) -> dict | None:
    if not locality:
        return None
    siruta = siruta_key(locality.get("siruta") or "")
    if siruta and siruta in points:
        return points[siruta]
    key = f"{norm(locality.get('name'))}|{norm(locality.get('county'))}"
    return points.get(key)


def explicit_county(text: str, county_keys: list[str]) -> str | None:
    t = norm(text)
    for county in sorted(county_keys, key=len, reverse=True):
        patterns = (
            rf"(?:JUDETUL|JUDETULUI|JUDETELE|JUDET|JUD\.)\s+{re.escape(norm(county))}\b",
            rf"\b{re.escape(norm(county))}\b",
        )
        if any(re.search(p, t) for p in patterns):
            return county
    return None


def source_county(source: str, county_keys: list[str]) -> str | None:
    t = norm(source)
    return next((c for c in sorted(county_keys, key=len, reverse=True) if norm(c) in t), None)


def locality_from_text(text: str, source_county: str | None, by_name: dict[str, list[dict]]) -> dict | None:
    padded = f" {norm(text)} "
    candidates = []
    for name, records in by_name.items():
        if len(name) < 4 or f" {name} " not in padded:
            continue
        same = [r for r in records if not source_county or norm(r["county"]) == norm(source_county)]
        if len(same) == 1:
            candidates.append(same[0])
    candidates.sort(key=lambda r: len(r["name"]), reverse=True)
    return candidates[0] if candidates else None


def locate(article: dict, county_keys: list[str], by_name: dict[str, list[dict]], points: dict[str, dict]) -> dict | None:
    if article.get("category") not in {"local", "zonal"}:
        return None
    text = " ".join(str(article.get(k) or "") for k in ("title", "teaser", "synthesis"))
    sc = source_county(str(article.get("source") or ""), county_keys)
    tc = explicit_county(text, county_keys)
    county = tc or sc
    locality = locality_from_text(text, county, by_name)
    if not county and locality:
        county = locality["county"]
    if not county:
        return None
    point = point_for(locality, points)
    return {
        "category": article.get("category", ""),
        "slug": article.get("slug", ""),
        "title": article.get("title") or article.get("original_title") or "Fără titlu",
        "teaser": article.get("teaser") or "",
        "synthesis": article.get("synthesis") or "",
        "published": article.get("published") or "",
        "source": article.get("source") or "",
        "county": county,
        "locality": locality["name"] if locality else "",
        "siruta": siruta_key(locality["siruta"]) if locality else "",
        "x": point.get("x") if point else None,
        "y": point.get("y") if point else None,
        "confidence": "text" if tc else "source" if sc else "siruta",
    }


def main() -> int:
    map_data = load_json(MAP)
    articles = load_json(ARTICLES)
    if not isinstance(articles, list):
        articles = articles.get("articles") or articles.get("items") or []
    counties = map_data.get("judete") or {}
    county_keys = list(counties)
    county_alias = {norm(key): key for key in county_keys}
    _, siruta = read_siruta(county_alias)
    points = load_locality_points()
    if not points:
        raise RuntimeError("harta_localitati.json nu contine puncte de localitati.")

    articles = sorted(articles, key=lambda a: str(a.get("published") or ""), reverse=True)
    located = []
    for article in articles[:MAX_ARTICLES]:
        item = locate(article, county_keys, siruta, points)
        if item:
            located.append(item)

    payload = {
        "version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "map": {"viewbox": map_data.get("viewbox", ""), "judete": counties},
        "articles": located,
        "stats": {
            "total": len(located),
            "local": sum(a["category"] == "local" for a in located),
            "zonal": sum(a["category"] == "zonal" for a in located),
            "counties": len({a["county"] for a in located}),
            "localities": len({a["siruta"] for a in located if a.get("siruta")}),
            "coordinates": sum(a.get("x") is not None and a.get("y") is not None for a in located),
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"harta-stiri: {len(located)} articole localizate; {payload['stats']['coordinates']} coordonate -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
