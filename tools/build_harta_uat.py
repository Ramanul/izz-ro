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
import sys
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

# O unitate de hartă ≈ 0,73 km (1000 units peste ~730 km de lată).
KM_PER_UNIT = (LON_MAX - LON_MIN) * 111.32 * K / WIDTH
FAR_PART_THRESHOLD = 8.0
# Lecția din 2 oct 2026 (vezi revert-ul PR #393): partea a doua a Comunei Mărașu
# (natcode 43493), la ~21 km nord de corp, a părut o eroare de sursă și a fost tăiată —
# dar e exclavă REALĂ: granița OSM (relația 10487259) o are identică, KMZ-ul oficial
# ANCPI 2014 o include, iar ariile OSM și WFS concordă la 0,1 km² (127,4 + 69,1 =
# 196,5). Tăierea a lăsat o gaură de ~69 km² pe hartă. Regula: o parte secundară
# îndepărtată NU se taie fără confirmare din a doua sursă oficială.

COUNTY_KEYS = {
    "BISTRITA NASAUD": "BISTRITA-NASAUD",
    "CARAS SEVERIN": "CARAS-SEVERIN",
}
COUNTY_FILTER_NAMES = {
    "BRAILA": "Brăila",
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


def _dedupe_ring_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Puncte consecutive duplicate + punctul de inchidere, inainte de simplificare."""
    out = [points[0]] if points else []
    for point in points[1:]:
        if point != out[-1]:
            out.append(point)
    while len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def _dp_keep(points: list[tuple[float, float]], tolerance: float) -> list[bool]:
    """Flagurile de pastrare ale Douglas–Peucker pentru un inel deschis (fara inchidere)."""
    keep = [False] * len(points)
    if not points:
        return keep
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue
        ax, ay = points[start]
        bx, by = points[end]
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy) or 1e-12
        distance, selected = 0.0, start
        for index in range(start + 1, end):
            px, py = points[index]
            candidate = abs(dx * (ay - py) - (ax - px) * dy) / length
            if candidate > distance:
                distance, selected = candidate, index
        if distance > tolerance:
            keep[selected] = True
            stack.append((start, selected))
            stack.append((selected, end))
    return keep


def _project_ring(ring: Iterable[Iterable[float]]) -> list[tuple[float, float]]:
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
    return points


# ---- simplificare topologica (vot global pe varfuri) --------------------------------------
# Douglas–Peucker pe fiecare inel INDEPENDENT taie granita comuna in doua copii divergente:
# masurat pe stratul comis 2026-10-02, 1094 perechi de vecini suprapusi (131 km2), ~1105 km2
# de fisii-gol si 104 puncte de localitate care cadeau in suprapunere si isi afisau stirea
# pe comuna vecina. Sursa ANCPI e mozaic perfect (0 suprapuneri, 0 goluri — masurat pe
# stratul brut), deci toate defectele astea sunt ale SIMPLIFICARII, si regula care le face
# imposibile e una singura:
#
#   Un varf se sterge doar daca NICIUN inel nu-l vrea pastrat.
#
# DP ruleaza pe fiecare inel pentru setul lui de pastrati; se face uniunea globala a
# seturilor, plus varfurile de jonctiune (prezente in >=3 inele distincte — colturile in T,
# de care se prinde si granita unui al treilea UAT: daca ar disparea, vecinul s-ar desprinde
# de muchia simplificata a celorlalti). Fiecare inel se reconstruieste apoi pastrand exact
# varfurile uniunii. Doua inele vecine impart ACEEASI multime de varfuri pe granita comuna,
# deci muchia simplificata le iese identica prin constructie — suprapunerea si golul nu mai
# au din ce sa apara. Costul: pe granitele comune se pastreaza unirea pastratilor ambelor
# parti, adica putin mai multe puncte decat ar pastra fiecare DP singur — se plateste in
# marimea fisierului, nu in corectitudine.

def topological_simplify(geometries: list[dict]) -> list[list[str]]:
    """Pentru fiecare geometrie, subcaile simplificate cu granite comune taiate o singura data.

    Intoarce, pe aceeasi pozitie ca `geometries`, cate o lista de subcai „M ... Z" (una per
    inel supravietuitor); inelele degenerate (<3 varfuri) lipsesc. Se apeleaza cu TOATE
    geometriile corectate deodata — topologia e globala, nu per județ.
    """
    all_rings: list[list[tuple[float, float]]] = []
    ring_indexes_per_geometry: list[list[int]] = []
    for geometry in geometries:
        kind = geometry.get("type")
        coords = geometry.get("coordinates") or []
        polygons = [coords] if kind == "Polygon" else coords if kind == "MultiPolygon" else []
        indexes: list[int] = []
        for polygon in polygons:
            if not isinstance(polygon, list):
                continue
            for ring in polygon:
                pts = _dedupe_ring_points(_project_ring(ring))
                if len(pts) >= 3:
                    indexes.append(len(all_rings))
                    all_rings.append(pts)
        ring_indexes_per_geometry.append(indexes)

    keep: set[tuple[float, float]] = set()
    incidence: dict[tuple[float, float], set[int]] = {}
    for ring_index, pts in enumerate(all_rings):
        for index, retained in enumerate(_dp_keep(pts, TOLERANCE)):
            if retained:
                keep.add(pts[index])
        for point in pts:
            incidence.setdefault(point, set()).add(ring_index)
    for point, rings_here in incidence.items():
        if len(rings_here) >= 3:
            keep.add(point)

    out: list[list[str]] = []
    for indexes in ring_indexes_per_geometry:
        paths = []
        for ring_index in indexes:
            pts = [point for point in all_rings[ring_index] if point in keep]
            if len(pts) >= 3:
                paths.append("M" + " L".join(f"{x:g} {y:g}" for x, y in pts) + " Z")
        out.append(paths)
    return out


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


def polygon_area(polygon: list) -> float:
    """Aria proiectată a inelului exterior; suficientă pentru compararea părților aceluiași UAT."""
    exterior = polygon[0] if polygon else []
    projected = [project(float(point[0]), float(point[1])) for point in exterior if len(point) >= 2]
    if len(projected) < 3:
        return 0.0
    area2 = 0.0
    for first, second in zip(projected, projected[1:] + projected[:1]):
        area2 += first[0] * second[1] - second[0] * first[1]
    return abs(area2) / 2.0


def ring_bbox(ring: list) -> tuple[float, float, float, float]:
    points = [(float(point[0]), float(point[1])) for point in ring if len(point) >= 2]
    projected = [project(x, y) for x, y in points]
    xs = [point[0] for point in projected]
    ys = [point[1] for point in projected]
    return min(xs), min(ys), max(xs), max(ys)


def bbox_distance(first: tuple, second: tuple) -> float:
    dx = max(first[0] - second[2], second[0] - first[2], 0.0)
    dy = max(first[1] - second[3], second[1] - first[3], 0.0)
    return math.hypot(dx, dy)


def far_parts(county: str, natcode: str, label: str, geometry: dict) -> list[str]:
    """Inventar: părți secundare ale unui UAT la peste ~6 km de corpul principal.

    Se rulează pe geometria sursei. Părțile secundare îndepărtate sunt de obicei exclave
    legitime (insule, balta, păduri administrate din comună — vezi lecția Mărașu de mai
    sus), deci raportul nu ratează build-ul: există ca rebuild-ul să arate structura
    multi-part a datelor la sursă.
    """
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    polygons = [coords] if kind == "Polygon" else coords if kind == "MultiPolygon" else []
    if len(polygons) < 2:
        return []
    areas = [polygon_area(polygon) for polygon in polygons]
    main = max(range(len(polygons)), key=lambda i: areas[i])
    if areas[main] <= 0 or not polygons[main] or not polygons[main][0]:
        return []
    main_box = ring_bbox(polygons[main][0])
    notes = []
    for index, polygon in enumerate(polygons):
        if index == main or not polygon or not polygon[0]:
            continue
        distance = bbox_distance(ring_bbox(polygon[0]), main_box)
        if distance > FAR_PART_THRESHOLD:
            notes.append(
                f"GARDĂ UAT: {county}/{label} ({natcode}) partea {index} la "
                f"{distance:.1f} map-units (~{distance * KM_PER_UNIT:.0f} km) de corpul principal, "
                f"aria {areas[index]:.0f} vs corp {areas[main]:.0f}"
            )
    return notes


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


# ---- garda geometrica a rebuild-ului ------------------------------------------------------
# Pragurile sunt valorile BUNE ale rebuild-ului topologic, cu aer pentru zgomotul mostenit
# de la sursa (ANCPI livreaza ~1170 geometrii invalide OGC, care se mostenesc partial).
# Un rebuild care inrautateste vreo cifra iese cu 1 — datele nu se comita orbeste. Cere
# shapely la rebuild; scriptul e rulare manuala, deliberat necablata in CI.
KM2_PER_UNIT2 = KM_PER_UNIT ** 2
# Masurat pe rebuild-ul topologic din 2 oct 2026: union 237.007 km2, 1 pereche suprapusa
# (0.0 km2), 0 goluri >0.5 km2, 1154 inele invalide. Inelele invalide se mostenesc de la
# sursa (ANCPI livreaza ~1172 geometrii „bowtie"; randarea canvas evenodd le deseneaza
# corect, doar metricile shapely au nevoie de buffer(0)) — pragul tine locul mostenirii,
# nu-i cere repararea.
GUARDA_MAX = {
    "suprapuneri_km2": 2.0,      # suma suprapunerilor > 2 ha
    "perechi_suprapuse": 20,     # perechi de UAT cu suprapunere > 2 ha
    "goluri": 5,                 # goluri de tesatura > 0.5 km2
    "inele_invalide": 1300,      # mostenite de la sursa (~1172 la ANCPI)
}
GUARDA_MIN_UNION_KM2 = 235500.0


def valida_geometrie() -> list[str]:
    """Masura suprapuneri/goluri/validitate pe fisierele scrise; intoarce incalcarile gărzii."""
    try:
        from shapely import STRtree
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
    except ImportError:
        return ["shapely lipseste (pip install shapely) — rebuild-ul NU a putut fi validat."]
    token = re.compile(r"[-+]?\d+(?:\.\d+)?")
    geoms = []
    inele_invalide = 0
    for filename in sorted(os.listdir(OUT_DIR)):
        if not filename.endswith(".json"):
            continue
        with open(os.path.join(OUT_DIR, filename), encoding="utf-8") as fh:
            data = json.load(fh)
        for uat in data["uats"]:
            parts = []
            for chunk in uat["path"].split("M"):
                if not chunk.strip():
                    continue
                nums = [float(value) for value in token.findall(chunk.replace("Z", ""))]
                pts = list(zip(nums[0::2], nums[1::2]))
                if len(pts) < 3:
                    continue
                poly = Polygon(pts)
                if not poly.is_valid:
                    inele_invalide += 1
                    # buffer(0), nu make_valid: pe inele „bowtie" make_valid poate intoarce
                    # colectie fara arie, iar UAT-ul ar disparea din uniune desi canvas-ul
                    # il randeaza. buffer(0) pastreaza aria, semantica fill-rule.
                    poly = poly.buffer(0)
                if poly.is_empty:
                    continue
                if poly.geom_type == "MultiPolygon":
                    parts.extend(poly.geoms)
                else:
                    parts.append(poly)
            if not parts:
                continue
            # evenodd exact, ca randarea din browser: XOR succesiv al inelelor.
            geom = parts[0]
            for extra in parts[1:]:
                geom = geom.symmetric_difference(extra)
            if not geom.is_valid:
                geom = geom.buffer(0)
            geoms.append(geom)

    tree = STRtree(geoms)
    perechi = 0
    suprapuneri_km2 = 0.0
    seen: set[tuple[int, int]] = set()
    for index, geom in enumerate(geoms):
        for other in tree.query(geom):
            other = int(other)
            if other <= index or (index, other) in seen:
                continue
            seen.add((index, other))
            inter = geom.intersection(geoms[other])
            if inter.is_empty:
                continue
            area_km2 = inter.area * KM2_PER_UNIT2
            if area_km2 > 0.02:
                perechi += 1
                suprapuneri_km2 += area_km2
    union = unary_union(geoms)
    union_km2 = union.area * KM2_PER_UNIT2
    goluri = 0
    for part in ([union] if union.geom_type == "Polygon" else list(union.geoms)):
        for index in range(len(part.interiors)):
            if Polygon(part.interiors[index]).area * KM2_PER_UNIT2 > 0.5:
                goluri += 1

    print(f"GARDA GEOMETRIE: union {union_km2:.0f} km2 | suprapuneri {perechi} perechi / "
          f"{suprapuneri_km2:.1f} km2 | goluri >0.5 km2: {goluri} | inele invalide: {inele_invalide}")
    failures = []
    if suprapuneri_km2 > GUARDA_MAX["suprapuneri_km2"]:
        failures.append(f"suprapuneri {suprapuneri_km2:.1f} km2 > prag {GUARDA_MAX['suprapuneri_km2']}")
    if perechi > GUARDA_MAX["perechi_suprapuse"]:
        failures.append(f"{perechi} perechi suprapuse > prag {GUARDA_MAX['perechi_suprapuse']}")
    if goluri > GUARDA_MAX["goluri"]:
        failures.append(f"{goluri} goluri > prag {GUARDA_MAX['goluri']}")
    if inele_invalide > GUARDA_MAX["inele_invalide"]:
        failures.append(f"{inele_invalide} inele invalide > prag {GUARDA_MAX['inele_invalide']}")
    if union_km2 < GUARDA_MIN_UNION_KM2:
        failures.append(f"union {union_km2:.0f} km2 sub minimul {GUARDA_MIN_UNION_KM2:.0f}")
    return failures


def main() -> int:
    features = request_features()
    label_overrides = load_label_overrides()
    report: list[str] = []
    kept: list[tuple[str, str, str, str, dict]] = []
    for feature in features:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        natcode = str(props.get("natcode") or feature.get("id") or "")
        labels = label_overrides.get(natcode, props)
        county = COUNTY_MN_KEYS.get(norm(labels.get("countyMn") or props.get("countyMn")), county_key(labels.get("county") or props.get("county")))
        label = display(labels.get("name") or props.get("name"))
        report.extend(far_parts(county, natcode, label, geometry))
        if county:
            kept.append((
                county, natcode, label,
                norm(labels.get("name") or props.get("name")),
                display(labels.get("natLevName") or props.get("natLevName")),
                geometry,
            ))

    # Topologia e GLOBALA: toate geometriile corectate intr-o singura trecere, ca granitele
    # comune sa fie taiate o singura data (vezi votul de varfuri de pe topological_simplify).
    paths_per_feature = topological_simplify([item[5] for item in kept])

    by_county: dict[str, list[dict]] = defaultdict(list)
    for (county, natcode, label, name, kind, geometry), paths in zip(kept, paths_per_feature):
        path = " ".join(paths)
        centre = centre_for_geometry(geometry)
        if not path or centre is None:
            continue
        entry = {
            "id": natcode,
            "name": name,
            "label": label,
            "kind": kind,
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
    for line in report:
        print(line, file=sys.stderr)
    if requested:
        # Rebuild partial (UAT_COUNTIES): tesatura nationala e incompleta, garda pe
        # suprapuneri/goluri n-ar masura ceva sensibil. Se reruleaza complet inainte de comit.
        print("GARDA GEOMETRIE: sarita — rebuild partial (UAT_COUNTIES).")
        return 0
    failures = valida_geometrie()
    if failures:
        for line in failures:
            print(f"GARDA GEOMETRIE PICA: {line}", file=sys.stderr)
        return 1
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
