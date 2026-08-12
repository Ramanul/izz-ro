#!/usr/bin/env python
"""Genereaza datasetul static consumat de harta de stiri.

Sursa de adevar ramane starea editoriala (`data/articles.json`) si infrastructura geografica
existenta (`data/harta_judete.json`, SIRUTA). Browserul nu mai descarca fisiere interne din
repo si nu mai face matching O(N*M) pe CSV-ul SIRUTA; build-ul produce un singur JSON compact
in `static/harta-stiri/data/map.json`.

SIRUTA este folosit determinist pentru identificarea localitatii si codului SIRUTA. Cand
localitatea este ambigua intre mai multe judete, judetul trebuie sa fie cunoscut din sursa
sau din text; altfel articolul ramane localizat doar la nivel de judet.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTICLES = os.path.join(ROOT, "data", "articles.json")
MAP = os.path.join(ROOT, "data", "harta_judete.json")
SIRUTA = os.path.join(ROOT, "data", "siruta_raw.csv")
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
    value = (value or "").strip()
    value = value.replace("Ț", "T").replace("ț", "t").replace("Ș", "S").replace("ș", "s")
    value = re.sub(r"[^A-Za-z0-9]+", " ", value).upper().strip()
    return re.sub(r"\s+", " ", value)


def clean_name(value: str) -> str:
    name = norm(value)
    for prefix in PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix):].strip()
    return name


def read_siruta() -> tuple[dict[str, str], dict[str, list[dict]]]:
    """Returneaza maparea cod judet -> nume si indexul SIRUTA dupa localitate."""
    with open(SIRUTA, encoding="cp1250", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))

    counties: dict[str, str] = {}
    for row in rows:
        if row.get("NIV") != "1":
            continue
        code = str(row.get("JUD") or "").strip()
        name = clean_name(row.get("DENLOC") or "")
        if code and name:
            counties[code] = name

    # Identifica satele duplicate global, ca sa nu folosim un nume ambiguu fara context.
    sat_names = [clean_name(r.get("DENLOC") or "") for r in rows if r.get("NIV") == "3"]
    duplicate_sats = {n for n in sat_names if n and sat_names.count(n) > 1}

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
        rec = {"name": name, "county": county, "siruta": siruta, "level": niv}
        by_name.setdefault(name, []).append(rec)
    return counties, by_name


def load_json(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def explicit_county(text: str, county_keys: list[str]) -> str | None:
    t = norm(text)
    for county in sorted(county_keys, key=len, reverse=True):
        patterns = (
            rf"(?:JUDETUL|JUDETULUI|JUDETELE|JUDET|JUD\.)\s+{re.escape(county)}\b",
            rf"\b{re.escape(county)}\b",
        )
        if any(re.search(p, t) for p in patterns):
            return county
    return None


def source_county(source: str, county_keys: list[str]) -> str | None:
    t = norm(source)
    return next((c for c in sorted(county_keys, key=len, reverse=True) if c in t), None)


def locality_from_text(text: str, source_county: str | None, by_name: dict[str, list[dict]]) -> dict | None:
    padded = f" {norm(text)} "
    candidates = []
    for name, records in by_name.items():
        if len(name) < 4 or f" {name} " not in padded:
            continue
        same = [r for r in records if not source_county or r["county"] == source_county]
        # Fara context, accepta doar un nume unic; cu contextul sursei, poate dezambigua.
        if len(same) == 1:
            candidates.append(same[0])
    candidates.sort(key=lambda r: len(r["name"]), reverse=True)
    return candidates[0] if candidates else None


def locate(article: dict, county_keys: list[str], by_name: dict[str, list[dict]]) -> dict | None:
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
        "siruta": locality["siruta"] if locality else "",
        "confidence": "text" if tc else "source" if sc else "siruta",
    }


def main() -> int:
    map_data = load_json(MAP)
    articles = load_json(ARTICLES)
    if not isinstance(articles, list):
        articles = articles.get("articles") or articles.get("items") or []
    counties = map_data.get("judete") or {}
    county_keys = list(counties)
    _, siruta = read_siruta()

    articles = sorted(articles, key=lambda a: str(a.get("published") or ""), reverse=True)
    located = []
    for article in articles[:MAX_ARTICLES]:
        item = locate(article, county_keys, siruta)
        if item:
            located.append(item)

    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "map": {"viewbox": map_data.get("viewbox", ""), "judete": counties},
        "articles": located,
        "stats": {
            "total": len(located),
            "local": sum(a["category"] == "local" for a in located),
            "zonal": sum(a["category"] == "zonal" for a in located),
            "counties": len({a["county"] for a in located}),
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"harta-stiri: {len(located)} articole localizate -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
