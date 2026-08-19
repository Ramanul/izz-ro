#!/usr/bin/env python3
"""Construiește poligoanele UAT pentru harta știrilor.

Sursa este stratul public WFS ``geospatial:ro_uat_poligon`` oferit de
geo-spatial.org. Geometriile sunt proiectate în același viewBox ca harta
județelor și sunt simplificate înainte de publicare. Ieșirea este împărțită
pe județe, astfel încât browserul descarcă numai UAT-urile județului ales.

    python tools/build_harta_uat.py

Fișiere rezultate: ``static/harta-stiri/data/uat/<JUDET>.json``.
"""
from __future__ import annotations

import json
import math
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Iterable

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "static", "harta-stiri", "data", "uat")
WFS_URL = "https://services.geo-spatial.org/geoserver/wfs"
TYPE_NAME = "geospatial:ro_uat_poligon"
SOURCE_URL = "https://geo-spatial.org/ghiduri/procesari-etl/administrative-boundaries/ro-admin-lau-line/"

# Aceleași valori sunt utilizate de tools/build_harta_localitati.py și map.json.
LON_MIN = 20.26240504971425
LON_MAX = 29.720105921094994
LAT_MIN = 43.619254164890435
LAT_MAX = 48.26486964515059
WIDTH = 1000.0
HEIGHT = 703.53
LAT_REF = (LAT_MIN + LAT_MAX) / 2.0
K = math.cos(math.radians(LAT_REF))
SCALE_X = WIDTH / ((LON_MAX - LON_MIN) * K)
SCALE_Y = HEIGHT / (LAT_MAX - LAT_MIN)
TOLERANCE = float(os.getenv("UAT_TOLERANCE", "0.28"))

COUNTY_KEYS = {
    "BISTRITA NASAUD": "BISTRITA-NASAUD",
    "CARAS SEVERIN": "CARAS-SEVERIN",
}
COUNTY_FILTER_NAMES = {
    "TIMIS": "Timiș",
}


def norm(value: object) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9]+", " ", value)).strip().upper()


def county_key(value: object) -> str:
    return COUNTY_KEYS.get(norm(value), norm(value))


def display(value: object) -> str:
    return str(value or "").strip()


def project(lon: float, lat: float) -> tuple[float, float]:
    return round((lon - LON_MIN) * K * SCALE_X, 1), round((LAT_MAX - lat) * SCALE_Y, 1)


def simplify(points: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    """Simplificare Douglas–Peucker iterativă pentru un inel închis."""
    unique = [points[0]] if points else []
    for point in points[1:]:
        if point != unique[-1]:
            unique.append(point)
    while len(unique) > 1 and unique[0] == unique[-1]:
        unique.pop()
    if len(unique) < 3:
        return unique
    keep = [False] * len(unique)
    keep[0] = keep[-1] = True
    stack = [(0, len(unique) - 1)]
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue
        ax, ay = unique[start]
        bx, by = unique[end]
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy) or 1e-12
        distance, selected = 0.0, start
        for index in range(start + 1, end):
            px, py = unique[index]
            candidate = abs(dx * (ay - py) - (ax - px) * dy) / length
            if candidate > distance:
                distance, selected = candidate, index
        if distance > tolerance:
            keep[selected] = True
            stack.append((start, selected))
            stack.append((selected, end))
    return [point for point, retained in zip(unique, keep) if retained]


def ring_path(ring: Iterable[Iterable[float]]) -> str:
    points = []
    for pair in ring:
        if not isinstance(pair, list) or len(pair) < 2:
            continue
        try:
            lon, lat = float(pair[0]), float(pair[1])
        except (TypeError, ValueError):
            continue
        if -180 <= lon <= 180 and -90 <= lat <= 90:
            points.append(project(lon, lat))
    points = simplify(points, TOLERANCE)
    if len(points) < 3:
        return ""
    return "M" + " L".join(f"{x:g} {y:g}" for x, y in points) + " Z"


def path_for_geometry(geometry: dict) -> str:
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    polygons = [coords] if kind == "Polygon" else coords if kind == "MultiPolygon" else []
    paths = []
    for polygon in polygons:
        if not isinstance(polygon, list):
            continue
        for ring in polygon:
            path = ring_path(ring)
            if path:
                paths.append(path)
    return " ".join(paths)


def centre_for_geometry(geometry: dict) -> tuple[float, float] | None:
    """Centru aproximativ robust pentru eticheta numerică; poligonul păstrează hit-testul exact."""
    coords = geometry.get("coordinates") or []
    polygons = [coords] if geometry.get("type") == "Polygon" else coords if geometry.get("type") == "MultiPolygon" else []
    weighted_x = weighted_y = total = 0.0
    for polygon in polygons:
        if not polygon or not polygon[0]:
            continue
        exterior = polygon[0]
        projected = [project(float(point[0]), float(point[1])) for point in exterior if len(point) >= 2]
        if len(projected) < 3:
            continue
        area2 = cx = cy = 0.0
        for first, second in zip(projected, projected[1:] + projected[:1]):
            cross = first[0] * second[1] - second[0] * first[1]
            area2 += cross
            cx += (first[0] + second[0]) * cross
            cy += (first[1] + second[1]) * cross
        area = abs(area2) / 2.0
        if area <= 1e-6:
            continue
        weighted_x += (cx / (3.0 * area2)) * area
        weighted_y += (cy / (3.0 * area2)) * area
        total += area
    if total <= 1e-6:
        return None
    return round(weighted_x / total, 1), round(weighted_y / total, 1)


def request_features() -> list[dict]:
    source_file = os.getenv("UAT_SOURCE_FILE")
    if source_file:
        with open(source_file, encoding="utf-8") as fh:
            features = json.load(fh).get("features") or []
        if features:
            return features
        raise RuntimeError("Fișierul GeoJSON local nu conține poligoane UAT.")
    requested = [county_key(value) for value in os.getenv("UAT_COUNTIES", "").split(",") if value.strip()]
    target_names = [COUNTY_FILTER_NAMES.get(key, key.title()) for key in requested]
    queries = target_names or [None]
    features: list[dict] = []
    for county_name in queries:
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": TYPE_NAME,
            "outputFormat": "application/json",
            "srsName": "EPSG:4326",
            "count": "5000",
        }
        if county_name:
            params["CQL_FILTER"] = f"county='{county_name}'"
        request = urllib.request.Request(
            WFS_URL + "?" + urllib.parse.urlencode(params),
            headers={"User-Agent": "izz-ro-map-builder/3.0"},
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            payload = json.loads(response.read().decode("utf-8"))
        features.extend(payload.get("features") or [])
    if not features:
        raise RuntimeError("Stratul WFS nu a returnat poligoane UAT.")
    return features


def main() -> int:
    features = request_features()
    by_county: dict[str, list[dict]] = defaultdict(list)
    for feature in features:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        county = county_key(props.get("county"))
        path = path_for_geometry(geometry)
        centre = centre_for_geometry(geometry)
        if not county or not path or centre is None:
            continue
        entry = {
            "id": str(props.get("natcode") or feature.get("id") or ""),
            "name": norm(props.get("name")),
            "label": display(props.get("name")),
            "kind": display(props.get("natLevName")),
            "path": path,
            "center": list(centre),
        }
        by_county[county].append(entry)

    if not by_county:
        raise RuntimeError("Nu a rămas niciun poligon UAT valid după proiectare.")
    os.makedirs(OUT_DIR, exist_ok=True)
    requested = {county_key(value) for value in os.getenv("UAT_COUNTIES", "").split(",") if value.strip()}
    if not requested:
        for filename in os.listdir(OUT_DIR):
            if filename.endswith(".json"):
                os.remove(os.path.join(OUT_DIR, filename))
    total_size = 0
    for county, units in sorted(by_county.items()):
        units.sort(key=lambda item: item["label"].casefold())
        data = {
            "version": 1,
            "county": county,
            "source": "geo-spatial.org — Limită UAT România (poligon)",
            "source_url": SOURCE_URL,
            "source_crs": "EPSG:4326",
            "projection": "IZZ map viewBox 0 0 1000 703.53",
            "uats": units,
        }
        path = os.path.join(OUT_DIR, f"{county}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        total_size += os.path.getsize(path)
    print(f"{sum(map(len, by_county.values()))} UAT-uri în {len(by_county)} județe -> {OUT_DIR} ({total_size / 1024 / 1024:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
