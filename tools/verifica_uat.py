#!/usr/bin/env python
"""Garda de regresie geometrica pentru stratul UAT al hartii stirilor.

Rulat DUPA `tools/build_harta_uat.py` (manual sau in CI pe branch-uri care ating
`static/harta-stiri/data/uat/`). Verifica tesatura topologica a stratului comis si
pica (exit 1) daca un indicator se inrautateste peste pragurile de mai jos — stabilite
pe build-ul topologic din 2 oct 2026, nu pe-zero absolut, ca sa toleram zgomotul sursei
ANCPI (1172 geometrii invalide OGC chiar la sursa).

    python tools/verifica_uat.py

Depinde de shapely (doar unealta de verificare; build-ul ramane stdlib). Pragurile se
INGUSTE pe masura ce se repara cauzele, nu se largeste ca sa treaca un build stricat.
"""
from __future__ import annotations

import csv
import glob
import json
import math
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UAT_DIR = os.path.join(ROOT, "static", "harta-stiri", "data", "uat")
SIRUTA = os.path.join(ROOT, "data", "siruta_raw.csv")
PUNCTE = os.path.join(ROOT, "data", "harta_localitati.json")

LON_MIN, LON_MAX = 20.26240504971425, 29.720105921094994
LAT_MIN, LAT_MAX = 43.619254164890435, 48.26486964515059
WIDTH, HEIGHT = 1000.0, 703.53
K = math.cos(math.radians((LAT_MIN + LAT_MAX) / 2))
KM_PER_UNIT = (LON_MAX - LON_MIN) * 111.32 * K / WIDTH
KM2_PER_UNIT2 = KM_PER_UNIT ** 2
RO_OFFICIAL_KM2 = 238397.0

TOKEN = re.compile(r"[-+]?\d+(?:\.\d+)?")

# Praguri de esec (build topologic 2 oct 2026: suprapuneri 8 perechi / 0,52 km2,
# goluri 2, inele invalide 2829). Cele doua cazuri „1" de mai jos sunt cunoscute si
# DOCUMENTATE, nu tolerati din lene:
#  - Sancraiu de Mures (114382): punctul reședinței e în afara poligonului PROPRIU la
#    sursa ANCPI (verificat pe geometria brută WFS) — defect de sursă, nu de build.
# Praguri calibrate pe build-ul topologic de pe main (3 oct 2026): 0 suprapuneri,
# 0 goluri, union 237.007 km2, 1154 inele invalide, 0 puncte pe niciun UAT.
MAX_OVERLAP_PAIRS = 3
MAX_OVERLAP_KM2 = 0.5
MAX_HOLES = 2
MIN_UNION_KM2 = 237000.0
MAX_SEATS_OUTSIDE = 1
MAX_POINTS_OUTSIDE = 0
MAX_INVALID_RINGS = 1500


def siruta_key(value) -> str:
    raw = str(value or "").strip().split(",", 1)[0].strip()
    if raw.endswith(".0"):
        raw = raw[:-2]
    return raw.lstrip("0") or "0"


def parse_path(path: str) -> list[list[tuple[float, float]]]:
    rings = []
    for chunk in path.split("M"):
        if not chunk.strip():
            continue
        chunk = chunk.replace("Z", "").strip()
        nums = [float(t) for t in TOKEN.findall(chunk)]
        pts = list(zip(nums[0::2], nums[1::2]))
        if len(pts) >= 3:
            rings.append(pts)
    return rings


def evenodd_inside(rings, x, y) -> bool:
    """Regula even-odd exacta a canvas-ului: treceri impare ale razei peste toate muchiile."""
    cross = 0
    for pts in rings:
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if (y1 > y) != (y2 > y):
                xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                if xin > x:
                    cross += 1
    return cross % 2 == 1


def main() -> int:
    from shapely.geometry import Polygon, Point
    from shapely import STRtree
    from shapely.ops import unary_union

    failures: list[str] = []
    uats = []
    invalid_rings = 0
    for f in sorted(glob.glob(os.path.join(UAT_DIR, "*.json"))):
        data = json.load(open(f, encoding="utf-8"))
        for u in data["uats"]:
            rings = parse_path(u["path"])
            if not rings:
                failures.append(f"PATH gol: {data['county']}/{u['label']} ({u['id']})")
                continue
            uats.append({"county": data["county"], "label": u["label"],
                         "id": siruta_key(u["id"]), "kind": (u.get("kind") or ""),
                         "rings": rings})
            for pts in rings:
                if not Polygon(pts).is_valid:
                    invalid_rings += 1

    print(f"Strat: {len(uats)} UAT-uri, {sum(len(u['rings']) for u in uats)} inele, "
          f"{invalid_rings} inele invalide OGC (artefact DP/sursa, randate corect even-odd)")

    # geometrie even-odd pe UAT (XOR de inele); buffer(0), nu make_valid: pe inele "bowtie"
    # make_valid intoarce colectie fara arie si UAT-ul dispare din verificare desi canvas-ul
    # il randeaza — prima rulare a gărzii dadea union 32.162 km2 exact din cauza asta
    geoms = []
    for u in uats:
        parts = []
        for pts in u["rings"]:
            p = Polygon(pts)
            if not p.is_valid:
                p = p.buffer(0)
            if p.geom_type == "MultiPolygon":
                parts += [q for q in p.geoms if q.area > 0]
            elif p.geom_type == "Polygon" and p.area > 0:
                parts.append(p)
        g = parts[0] if parts else None
        for extra in parts[1:]:
            g = g.symmetric_difference(extra)
        if g is not None and not g.is_valid:
            g = g.buffer(0)
        u["g"] = g
        geoms.append(g)

    # suprapuneri + goluri
    indexed = [(i, g) for i, g in enumerate(geoms) if g is not None]
    tree = STRtree([g for _, g in indexed])
    n_overlap = 0
    total_overlap = 0.0
    for i, g in indexed:
        for k in tree.query(g):
            j = indexed[int(k)][0]
            if j <= i:
                continue
            inter = g.intersection(geoms[j])
            if inter.is_empty or inter.geom_type in ("LineString", "MultiLineString", "Point", "GeometryCollection"):
                continue
            a = inter.area * KM2_PER_UNIT2
            if a > 0.02:
                n_overlap += 1
                total_overlap += a
    union = unary_union([g for g in geoms if g is not None])
    union_km2 = union.area * KM2_PER_UNIT2
    holes = 0
    parts = [union] if union.geom_type == "Polygon" else list(union.geoms)
    for part in parts:
        for k in range(len(part.interiors)):
            if Polygon(part.interiors[k]).area * KM2_PER_UNIT2 > 0.5:
                holes += 1

    # sedii + puncte pe niciun UAT (regula even-odd exacta, ca in browser)
    child_parent = {}
    with open(SIRUTA, encoding="cp1250", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            if str(row.get("NIV") or "").strip() == "3":
                parent = siruta_key(row.get("SIRSUP"))
                if parent:
                    child_parent[siruta_key(row.get("SIRUTA"))] = parent
    by_siruta_pt = {}
    pdata = json.load(open(PUNCTE, encoding="utf-8"))
    for p in (pdata.get("localities") or {}).values():
        code = siruta_key(p.get("siruta") or "")
        if code and 0 <= p["x"] <= WIDTH and 0 <= p["y"] <= HEIGHT:
            by_siruta_pt.setdefault(code, p)

    seats_outside = 0
    children_by_parent = defaultdict(list)
    for child, parent in child_parent.items():
        children_by_parent[parent].append(child)
    for u in uats:
        # Sectoarele Bucureștiului n-au „reședință" proprie (punctul municipiului cade în
        # alt sector); check-ul de reședință are sens doar pentru UAT-urile cu teritoriu.
        if "Sectoarele" in u["kind"]:
            continue
        p = by_siruta_pt.get(u["id"])
        if not p:
            for child in children_by_parent.get(u["id"], ()):
                p = by_siruta_pt.get(child)
                if p:
                    break
        if not p:
            continue
        if not evenodd_inside(u["rings"], p["x"], p["y"]):
            seats_outside += 1
    points_outside = 0
    uat_ids = {u["id"] for u in uats}
    for key, p in by_siruta_pt.items():
        true_uat = key if key in uat_ids else child_parent.get(key)
        if not true_uat:
            continue
        pt = Point(p["x"], p["y"])
        # regula even-odd exacta (canvas), nu shapely covers: pe inele invalide cele doua
        # semantici diverg si garda ar raporta altceva decat vede utilizatorul
        candidates = [uats[indexed[int(k)][0]] for k in tree.query(pt)]
        if not any(evenodd_inside(u["rings"], p["x"], p["y"]) for u in candidates):
            points_outside += 1

    print(f"Suprapuneri > 2 ha: {n_overlap} perechi ({total_overlap:.2f} km2) | "
          f"Goluri > 0,5 km2: {holes} | Union: {union_km2:.0f} km2 din {RO_OFFICIAL_KM2:.0f}")
    print(f"Sedii in afara poligonului: {seats_outside} | Puncte de localitate pe niciun UAT: {points_outside}")

    if n_overlap > MAX_OVERLAP_PAIRS:
        failures.append(f"suprapuneri {n_overlap} > prag {MAX_OVERLAP_PAIRS}")
    if total_overlap > MAX_OVERLAP_KM2:
        failures.append(f"suprapuneri {total_overlap:.2f} km2 > prag {MAX_OVERLAP_KM2}")
    if holes > MAX_HOLES:
        failures.append(f"goluri {holes} > prag {MAX_HOLES}")
    if union_km2 < MIN_UNION_KM2:
        failures.append(f"union {union_km2:.0f} km2 < prag {MIN_UNION_KM2}")
    if seats_outside > MAX_SEATS_OUTSIDE:
        failures.append(f"sedi in afara {seats_outside} > prag {MAX_SEATS_OUTSIDE}")
    if points_outside > MAX_POINTS_OUTSIDE:
        failures.append(f"puncte pe niciun UAT {points_outside} > prag {MAX_POINTS_OUTSIDE}")
    if invalid_rings > MAX_INVALID_RINGS:
        failures.append(f"inele invalide {invalid_rings} > prag {MAX_INVALID_RINGS}")

    if failures:
        print("\nESEC garda:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nGarda UAT: OK")
    return 0


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
