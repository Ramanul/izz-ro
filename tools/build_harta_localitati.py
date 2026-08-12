#!/usr/bin/env python3
"""Descarcă punctele localităților și le aliniază cu viewBox-ul hărții județelor.

Sursa este stratul public geo-spatial.org `romania_localitati`, care are geometrie punctuală
și atribute provenite inclusiv din SIRUTA. Datasetul rezultat este static: browserul nu
contactează serviciul GIS.
"""
from __future__ import annotations

import json
import math
import os
import re
import unicodedata
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "harta_localitati.json")
WFS_URL = "https://services.geo-spatial.org/geoserver/wfs"
CATALOG_URL = "https://geo-spatial.org/vechi/download/romania-seturi-vectoriale"
TYPE_NAME = "geospatial:romania_localitati"

# Aceasta este aceeași proiecție equirectangulară folosită de build_harta.py.
LON_MIN = 20.26240504971425
LON_MAX = 29.720105921094994
LAT_MIN = 43.619254164890435
LAT_MAX = 48.26486964515059
WIDTH = 1000.0
LAT_REF = (LAT_MIN + LAT_MAX) / 2.0
K = math.cos(math.radians(LAT_REF))
SCALE = WIDTH / ((LON_MAX - LON_MIN) * K)


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9]+", " ", value)).strip().upper()


def first(props: dict, *names: str) -> str:
    lower = {str(k).lower(): v for k, v in props.items()}
    for name in names:
        value = lower.get(name.lower())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def project(lon: float, lat: float) -> tuple[float, float]:
    x = (lon - LON_MIN) * K * SCALE
    y = (LAT_MAX - lat) * SCALE
    return round(x, 1), round(y, 1)


def request_json(url: str, params: dict) -> dict:
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(url + "?" + query, headers={"User-Agent": "izz-ro-map-builder/2.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def load_wfs() -> list[dict]:
    payload = request_json(WFS_URL, {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": TYPE_NAME, "outputFormat": "application/json",
    })
    return payload.get("features") or []


def load_catalog_geojson() -> list[dict]:
    # Pagina geo-spatial.org publică explicit stratul „Localități România punct”
    # în GeoJSON. Extragem linkul din pagina oficială, deci nu hardcodăm un URL
    # volatil al fișierului.
    request = urllib.request.Request(CATALOG_URL, headers={"User-Agent": "izz-ro-map-builder/2.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        html = response.read().decode("utf-8", "replace")

    start = html.find("Localități România punct")
    if start < 0:
        start = html.find("Localitati Romania punct")
    if start < 0:
        raise RuntimeError("Nu am găsit stratul Localități România punct în catalogul geo-spatial.org.")

    block = html[start:start + 12000]
    matches = re.findall(r'href=["\']([^"\']+)["\'][^>]*>\s*GeoJSON\s*<', block, flags=re.I | re.S)
    if not matches:
        # Unele versiuni ale paginii pun textul GeoJSON înaintea atributului href.
        matches = re.findall(r'>\s*GeoJSON\s*</a>[^<]*', block, flags=re.I | re.S)
        if not matches:
            raise RuntimeError("Catalogul geo-spatial.org nu expune linkul GeoJSON pentru localități.")
        raise RuntimeError("Linkul GeoJSON pentru localități nu a putut fi extras din catalog.")

    href = matches[0]
    url = urllib.parse.urljoin(CATALOG_URL, href)
    request = urllib.request.Request(url, headers={"User-Agent": "izz-ro-map-builder/2.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload.get("features") or []


def load_features() -> tuple[list[dict], str]:
    try:
        features = load_wfs()
        if features:
            return features, WFS_URL
    except Exception as exc:
        print(f"WFS indisponibil ({exc}); folosesc GeoJSON-ul public din catalog.")
    features = load_catalog_geojson()
    return features, CATALOG_URL


def main() -> int:
    features, source = load_features()
    out = {}
    for feature in features:
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates")
        if geom.get("type") != "Point" or not isinstance(coords, list) or len(coords) < 2:
            continue
        try:
            lon, lat = float(coords[0]), float(coords[1])
        except (TypeError, ValueError):
            continue
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            continue

        name = first(props, "DENLOC", "denloc", "name", "NAME")
        siruta = first(props, "SIRUTA", "siruta", "CODSIRUTA", "codsiruta", "natCode")
        county = first(props, "JUD", "jud", "county", "COUNTY", "DENJUD", "judet")
        level = first(props, "NIV", "niv", "level")
        if not name:
            continue
        x, y = project(lon, lat)
        record = {"name": norm(name), "siruta": siruta, "county": norm(county), "level": level, "x": x, "y": y}
        key = siruta or f"{norm(name)}|{norm(county)}"
        out[str(key)] = record

    if not out:
        raise RuntimeError("Sursa geospațială nu a returnat nicio localitate punctuală.")

    result = {
        "version": 1,
        "source": "geo-spatial.org — Localități România punct",
        "source_url": source,
        "source_crs": "EPSG:4326",
        "projection": {"lon_min": LON_MIN, "lon_max": LON_MAX, "lat_min": LAT_MIN, "lat_max": LAT_MAX, "width": WIDTH},
        "localities": out,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"harta-stiri: {len(out)} localități -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
