# Diagnoza harta-stiri 2026-09-11: rasterizare culori/linii + masuratori geometrie.
# Fara dependente noi: doar Pillow (deja instalat) + json/re/math.
# Iesiri in notes/harta_diag/*.png + cifre pe stdout.
import json
import math
import os
import re

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "notes", "harta_diag")
os.makedirs(OUT, exist_ok=True)

S = 2  # supersampling: viewBox 1000x703.53 -> 2000x1407 px
W, H = 1000, 703.53


def parse_path(d):
    """M/L/Z cu coordonate repetitive implicite -> lista de inele (liste de (x,y))."""
    tokens = re.findall(r"[MLZmlz]|-?\d+(?:\.\d+)?", d)
    rings, cur, i, cx, cy = [], [], 0, 0.0, 0.0
    cmd = None
    while i < len(tokens):
        t = tokens[i]
        if t in "MLZmlz":
            cmd = t.upper()
            i += 1
            if cmd == "Z":
                if len(cur) >= 3:
                    rings.append(cur)
                cur = []
            elif cmd == "M":
                cx, cy = float(tokens[i]), float(tokens[i + 1])
                i += 2
                if cur:
                    rings.append(cur)
                cur = [(cx, cy)]
                cmd = "L"
            elif cmd == "L":
                cx, cy = float(tokens[i]), float(tokens[i + 1])
                i += 2
                cur.append((cx, cy))
        else:
            cx, cy = float(t), float(tokens[i + 1])
            i += 2
            cur.append((cx, cy))
    if len(cur) >= 3:
        rings.append(cur)
    return rings


def seg_dist(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    L2 = vx * vx + vy * vy
    if L2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / L2))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def boundary_segments(rings):
    segs = []
    for r in rings:
        for k in range(len(r)):
            ax, ay = r[k]
            bx, by = r[(k + 1) % len(r)]
            segs.append((ax, ay, bx, by))
    return segs


def min_dist_to_segments(pt, segs):
    return min(seg_dist(pt[0], pt[1], *s) for s in segs)


def draw_map(rings_by_county, fills, stroke, stroke_w, path_out, badges=None):
    img = Image.new("RGB", (int(W * S), int(H * S)), "#ffffff")
    dr = ImageDraw.Draw(img)
    for county, rings in rings_by_county.items():
        color = fills(county)
        for r in rings:
            pts = [(x * S, y * S) for x, y in r]
            dr.polygon(pts, fill=color)
    # contururi deasupra umplerilor, ca in canvas-ul real
    for county, rings in rings_by_county.items():
        for r in rings:
            pts = [(x * S, y * S) for x, y in r] + [(r[0][0] * S, r[0][1] * S)]
            dr.line(pts, fill=stroke, width=int(stroke_w * S), joint="curve")
    if badges:
        for x, y, r, label in badges:
            dr.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S],
                       fill="#b58b18", outline="#ffffff", width=int(1.5 * S))
    img.save(path_out)
    return path_out


m = json.load(open(os.path.join(ROOT, "static", "harta-stiri", "data", "map.json"), encoding="utf-8"))
mp = m["map"]
judete_ne = {k: parse_path(v) for k, v in mp["judete"].items()}
regiuni = mp["regiuni"]
reg_of = {c: r for r, cs in regiuni.items() for c in cs}

REGION_FILLS = {
    "Transilvania": "#bdd7ee", "Muntenia": "#f6d6ad", "Moldova": "#c9e6cf",
    "Banat": "#e4c6e8", "Dobrogea": "#f6df91", "Oltenia": "#f3c1bd", "Bucovina": "#cbd6f3",
}
NEUTRAL = "#e2dfd3"

# 1) Vederea "Toate" (neutra), asa cum o deseneaza canvas-ul: fill map-fill, stroke 1.2
draw_map(judete_ne, lambda c: NEUTRAL, "#83806f", 1.2,
         os.path.join(OUT, "national_neutral.png"))

# 2) Vederea "Regional" cu paleta pastel actuala
draw_map(judete_ne, lambda c: REGION_FILLS.get(reg_of.get(c, ""), NEUTRAL), "#83806f", 1.2,
         os.path.join(OUT, "national_regional.png"))

# 3) Judetul deschis: silueta UAT TIMIS peste vecini NE estompcati (alpha .32 -> amestec cu alb)
uat = json.load(open(os.path.join(ROOT, "static", "harta-stiri", "data", "uat", "TIMIS.json"),
                     encoding="utf-8"))
uat_rings = {}
for u in uat["uats"]:
    uat_rings[u["name"]] = parse_path(u["path"])


def blend(c1, c2, a):
    return tuple(round(a * int(c1[i:i + 2], 16) + (1 - a) * int(c2[i:i + 2], 16))
                 for i in (1, 3, 5))


dim = lambda c: blend("#e2dfd3", "#ffffff", 0.32)
acc = lambda c: "#d9a21b"


def mix_fill(c):
    return acc(c) if c == "TIMIS" else dim(c)


img = Image.new("RGB", (int(W * S), int(H * S)), "#ffffff")
dr = ImageDraw.Draw(img)
for county, rings in judete_ne.items():
    col = mix_fill(county)
    for r in rings:
        dr.polygon([(x * S, y * S) for x, y in r], fill=col)
for county, rings in judete_ne.items():
    if county == "TIMIS":
        continue
    for r in rings:
        pts = [(x * S, y * S) for x, y in r] + [(r[0][0] * S, r[0][1] * S)]
        dr.line(pts, fill=blend("#83806f", "#ffffff", 0.32), width=int(1.2 * S), joint="curve")
for rings in uat_rings.values():
    for r in rings:
        dr.polygon([(x * S, y * S) for x, y in r], fill="#b58b18")
for rings in uat_rings.values():
    for r in rings:
        pts = [(x * S, y * S) for x, y in r] + [(r[0][0] * S, r[0][1] * S)]
        dr.line(pts, fill="#171717", width=int(0.65 * S), joint="curve")
img.save(os.path.join(OUT, "timis_uat_pe_vecini_ne.png"))

# 4) Masuratori: cat de departe e conturul NE al TIMIS de silueta UAT (si invers)
ne_timis_segs = boundary_segments(judete_ne["TIMIS"])
uat_segs = []
for rings in uat_rings.values():
    uat_segs.extend(boundary_segments(rings))
d_ne_to_uat = [min_dist_to_segments(p, uat_segs) for p in judete_ne["TIMIS"][0]]
d_uat_to_ne = [min_dist_to_segments(p, ne_timis_segs) for p in
               [pt for rings in uat_rings.values() for r in rings for pt in r[::5]]]
for name, ds in (("NE->silueta UAT", d_ne_to_uat), ("silueta UAT->NE", d_uat_to_ne)):
    ds2 = sorted(ds)
    med = ds2[len(ds2) // 2]
    p95 = ds2[int(len(ds2) * 0.95)]
    print(f"{name}: mediana {med:.2f} px viewBox, p95 {p95:.2f}, max {max(ds):.2f}")
print("Pe desktop (~820px canvas): mediana in px ecran = x0.82; pe telefon (~364px): x0.36")

# 5) Suduri intre vecini la nivel national: distanta minima dintre granita a doua judete
# adiacente (0 = granita partajata exact -> vederea nationala nu are goluri)
for a, b in (("TIMIS", "ARAD"), ("CLUJ", "SALAJ"), ("ILFOV", "PRAHOVA")):
    sa = boundary_segments(judete_ne[a])
    sb_pts = [pt for r in judete_ne[b] for pt in r[::4]]
    dmin = min(min_dist_to_segments(p, sa) for p in sb_pts)
    print(f"granita {a}/{b}: distanta minima {dmin:.3f} px viewBox")
