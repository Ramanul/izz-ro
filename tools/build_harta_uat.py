#!/usr/bin/env python
# RULARE MANUALA, deliberat necablata in CI (audit 2026-08-20).
#
# Scriptul descarca poligoanele UAT din stratul public WFS `geospatial:ro_uat_poligon` de la
# geo-spatial.org si le proiecteaza in viewBox-ul hartii. Fisierele rezultate
# (`static/harta-stiri/data/uat/<JUDET>.json`) sunt servite public si NU se regenereaza singure:
# datele raman inghetate la momentul ultimei rulari manuale.
#
# De ce NU e pus pe un cron: granitele UAT se schimba la reorganizari administrative, adica la
# ani distanta, iar un job periodic care ia geometrie de la un serviciu extern si o COMITE adauga
# mai multa suprafata de esec decat economiseste — daca serviciul raspunde partial sau schimba
# schema, ajunge in productie o harta stricata, tacut.
#
# CAND se re-ruleaza: dupa o reorganizare administrativa, dupa o schimbare de schema la sursa,
# sau daca apar UAT-uri lipsa pe harta. Se ruleaza local, se verifica diff-ul, se comite explicit.3
"""Construiește poligoanele UAT pentru harta știrilor.

Sursa este stratul public WFS ``geospatial:ro_uat_poligon`` oferit de
geo-spatial.org. Geometriile sunt proiectate în același viewBox ca harta
județelor și sunt simplificate înainte de publicare. Ieșirea este împărțită
pe județe, astfel încât browserul descarcă numai UAT-urile județului ales.

    python tools/build_harta_uat.py

Fișiere rezultate: ``static/harta-stiri/data/uat/<JUDET>.json``.
"""
from __future__ import annotations

import io
import json
import math
import os
import re
import struct
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
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
# Codurile județene sunt stabile în exportul UAT și evită problemele de codare DBF ale diacriticelor.
COUNTY_MN_KEYS = {
    "AB": "ALBA", "AR": "ARAD", "AG": "ARGES", "BC": "BACAU", "BH": "BIHOR",
    "BN": "BISTRITA-NASAUD", "BT": "BOTOSANI", "BR": "BRAILA", "BV": "BRASOV",
    "B": "BUCURESTI", "BZ": "BUZAU", "CL": "CALARASI", "CS": "CARAS-SEVERIN",
    "CJ": "CLUJ", "CT": "CONSTANTA", "CV": "COVASNA", "DB": "DAMBOVITA", "DJ": "DOLJ",
    "GL": "GALATI", "GR": "GIURGIU", "GJ": "GORJ", "HR": "HARGHITA", "HD": "HUNEDOARA",
    "IL": "IALOMITA", "IS": "IASI", "IF": "ILFOV", "MM": "MARAMURES", "MH": "MEHEDINTI",
    "MS": "MURES", "NT": "NEAMT", "OT": "OLT", "PH": "PRAHOVA", "SJ": "SALAJ",
    "SM": "SATU MARE", "SB": "SIBIU", "SV": "SUCEAVA", "TR": "TELEORMAN", "TM": "TIMIS",
    "TL": "TULCEA", "VL": "VALCEA", "VS": "VASLUI", "VN": "VRANCEA",
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


def _transform_coordinates(value, transformer, swap_axes: bool = False):
    if isinstance(value, (list, tuple)) and len(value) >= 2 and isinstance(value[0], (int, float)):
        first, second = float(value[0]), float(value[1])
        # Exportul Stereo 70 al sursei stochează coordonatele în ordinea nord-est,
        # iar Transformer(always_xy=True) primește est-nord.
        lon, lat = transformer.transform(second, first) if swap_axes else transformer.transform(first, second)
        return [lon, lat]
    return [_transform_coordinates(item, transformer, swap_axes) for item in value]


def parse_dbf(payload: bytes) -> list[dict]:
    """Citește atributele unui DBF dBase III; exportul WFS are field descriptors standard."""
    if len(payload) < 33:
        raise RuntimeError("DBF-ul UAT este prea mic.")
    record_count = struct.unpack("<I", payload[4:8])[0]
    header_length = struct.unpack("<H", payload[8:10])[0]
    record_length = struct.unpack("<H", payload[10:12])[0]
    fields = []
    offset = 32
    while offset + 32 <= len(payload) and payload[offset] != 0x0D:
        descriptor = payload[offset:offset + 32]
        name = descriptor[:11].split(b"\x00", 1)[0].decode("ascii", "ignore")
        kind = descriptor[11:12].decode("ascii", "ignore")
        width = descriptor[16]
        decimals = descriptor[17]
        fields.append((name, kind, width, decimals))
        offset += 32
    rows = []
    for index in range(record_count):
        start = header_length + index * record_length
        record = payload[start:start + record_length]
        if len(record) < record_length or record[:1] == b"*":
            continue
        row, cursor = {}, 1
        for name, kind, width, decimals in fields:
            raw = record[cursor:cursor + width]
            cursor += width
            text = raw.decode("iso-8859-1", "replace").strip()
            if kind in {"N", "F"}:
                try:
                    row[name] = float(text) if decimals else int(text)
                except ValueError:
                    row[name] = None
            else:
                row[name] = text
        rows.append(row)
    return rows


def load_shapefile_zip(source_file: str) -> list[dict]:
    try:
        import shapefile
        from pyproj import Transformer
    except ImportError as exc:
        raise RuntimeError("Pentru UAT_SOURCE_ZIP sunt necesare pachetele pyshp și pyproj.") from exc
    archive = Path(source_file)
    if not archive.is_file():
        raise RuntimeError(f"Nu găsesc arhiva shapefile: {source_file}")
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        shp_name = next((name for name in names if name.lower().endswith(".shp")), "")
        dbf_name = next((name for name in names if name.lower().endswith(".dbf")), "")
        shx_name = next((name for name in names if name.lower().endswith(".shx")), "")
        if not all((shp_name, dbf_name, shx_name)):
            raise RuntimeError("Arhiva UAT nu conține setul complet .shp/.shx/.dbf.")
        payloads = {name: bundle.read(name) for name in (shp_name, dbf_name, shx_name)}
    reader = shapefile.Reader(
        shp=io.BytesIO(payloads[shp_name]),
        shx=io.BytesIO(payloads[shx_name]),
    )
    records = parse_dbf(payloads[dbf_name])
    shapes = list(reader.iterShapes())
    if len(shapes) != len(records):
        raise RuntimeError(f"Shapefile și DBF au număr diferit de obiecte ({len(shapes)} vs {len(records)}).")
    transformer = Transformer.from_crs("EPSG:3844", "EPSG:4326", always_xy=True)
    features = []
    for shape, properties in zip(shapes, records):
        geometry = shape.__geo_interface__
        features.append({
            "id": str(properties.get("natcode") or ""),
            "properties": properties,
            "geometry": {
                "type": geometry.get("type"),
                "coordinates": _transform_coordinates(geometry.get("coordinates") or [], transformer, swap_axes=True),
            },
        })
    return features


def load_label_overrides() -> dict[str, dict]:
    source_file = os.getenv("UAT_LABELS_FILE")
    if not source_file:
        return {}
    with open(source_file, encoding="utf-8") as fh:
        payload = json.load(fh)
    return {
        str((feature.get("properties") or {}).get("natcode")): feature.get("properties") or {}
        for feature in payload.get("features") or []
        if (feature.get("properties") or {}).get("natcode")
    }


def request_features() -> list[dict]:
    source_zip = os.getenv("UAT_SOURCE_ZIP")
    if source_zip:
        features = load_shapefile_zip(source_zip)
        if features:
            return features
        raise RuntimeError("Arhiva shapefile nu conține poligoane UAT.")
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
    label_overrides = load_label_overrides()
    by_county: dict[str, list[dict]] = defaultdict(list)
    for feature in features:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        natcode = str(props.get("natcode") or feature.get("id") or "")
        labels = label_overrides.get(natcode, props)
        county = COUNTY_MN_KEYS.get(norm(labels.get("countyMn") or props.get("countyMn")), county_key(labels.get("county") or props.get("county")))
        path = path_for_geometry(geometry)
        centre = centre_for_geometry(geometry)
        if not county or not path or centre is None:
            continue
        entry = {
            "id": natcode,
            "name": norm(labels.get("name") or props.get("name")),
            "label": display(labels.get("name") or props.get("name")),
            "kind": display(labels.get("natLevName") or props.get("natLevName")),
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
    import sys
    # Windows: cp1252 nu are „ș"/„ț", deci un `print` cu diacritice arunca
    # UnicodeEncodeError si scriptul iese cu 1 — indistingibil de un esec real de
    # continut. Masurat 2026-08-20: `qa_check.py` iesea cu 1 pe date valide, iar cu
    # PYTHONIOENCODING=utf-8 cu 0. In CI (Linux, UTF-8) nu se vede. Acelasi idiom ca
    # in `scan_homepages.py`, extins la toate punctele de intrare cu diacritice.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
