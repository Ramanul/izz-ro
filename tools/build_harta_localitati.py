#!/usr/bin/env python3
"""Descarcă punctele localităților și le aliniază cu viewBox-ul hărții județelor.

Sursa este stratul public geo-spatial.org `geospatial:romania_localitati`.
Datasetul rezultat este static: browserul nu contactează serviciul GIS.
"""
from __future__ import annotations

import json
import math
import os
import re
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "harta_localitati.json")
URL = "https://services.geo-spatial.org/geoserver/wfs"
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


def request_bytes(output_format: str) -> bytes:
    params = urllib.parse.urlencode({
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": TYPE_NAME, "outputFormat": output_format,
    })
    request = urllib.request.Request(URL + "?" + params, headers={"User-Agent": "izz-ro-map-builder/1.2"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def parse_json(raw: bytes) -> list[dict]:
    payload = json.loads(raw.decode("utf-8"))
    return payload.get("features") or []


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_gml(raw: bytes) -> list[dict]:
    root = ET.fromstring(raw)
    features = []
    # GeoServer poate returna featureMember sau featureMembers, în funcție de versiunea WFS.
    for member in root.iter():
        if local_name(member.tag) not in {"featureMember", "member"}:
            continue
        feature = next((child for child in list(member) if isinstance(child.tag, str)), None)
        if feature is None:
            continue
        props = {}
        lon = lat = None
        for child in feature.iter():
            name = local_name(child.tag)
            text = (child.text or "").strip()
            if name in {"coordinates", "pos"} and text:
                parts = re.split(r"[ ,]+", text)
                if len(parts) >= 2:
                    try:
                        lon, lat = float(parts[0]), float(parts[1])
                    except ValueError:
                        pass
            elif child is not feature and text and len(list(child)) == 0:
                props[name] = text
        if lon is not None and lat is not None:
            features.append({"properties": props, "coordinates": [lon, lat]})
    return features


def load_features() -> list[dict]:
    raw = request_bytes("application/json")
    try:
        features = parse_json(raw)
        if features:
            return features
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    return parse_gml(request_bytes("application/gml+xml"))


def main() -> int:
    features = load_features()
    out = {}
    for feature in features:
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates") if geom else feature.get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
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
        "source": "geo-spatial.org — geospatial:romania_localitati",
        "source_url": URL,
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
