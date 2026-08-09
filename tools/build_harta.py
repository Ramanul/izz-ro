#!/usr/bin/env python
"""Construieste `data/harta_judete.json` — conturul fiecarui judet ca `path d` de SVG.

Sursa: Natural Earth, `ne_10m_admin_1_states_provinces` (nvkelso/natural-earth-vector).
Natural Earth e **domeniu public**, fara atribuire obligatorie si fara restrictie de
redistribuire — de-aia nu folosim GADM, care are exact aceleasi granite dar interzice
explicit redistribuirea si uzul comercial, iar noi comitem datele intr-un repo public.

De ce un fisier derivat, comis in repo, si nu geojson-ul brut: brutul are 39 MB, iar harta
trebuie sa fie inline in pagina (SVG static, fara JS, fara request suplimentar). Iesirea e
sub 100 KB dupa proiectie + simplificare, si nu depinde de retea la randare.

  python tools/build_harta.py cale/catre/ne_10m_admin_1_states_provinces.geojson

Env: TOLERANTA (implicit 0.6, in unitati de viewBox) — mai mare = contur mai grosier.
"""
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from generator.util import strip_diacritics  # noqa: E402

OUT = os.path.join(ROOT, "data", "harta_judete.json")

# Panza SVG. Latimea e fixa; inaltimea iese din raportul real al tarii, ca sa nu deformam.
LATIME = 1000.0
TOLERANTA = float(os.getenv("TOLERANTA", "0.6"))

# Natural Earth scrie numele in engleza/fara diacritice inconsecvent. Normalizam la forma
# folosita in `geo.REGIUNI` (majuscule, fara diacritice); doar capitala difera cu adevarat.
EXCEPTII = {"BUCHAREST": "BUCURESTI"}


def _normalizeaza(nume: str) -> str:
    return EXCEPTII.get(strip_diacritics(nume).strip().upper(),
                        strip_diacritics(nume).strip().upper())


def _inele(geom: dict) -> list:
    """Toate inelele exterioare, indiferent de Polygon vs MultiPolygon."""
    if geom["type"] == "Polygon":
        return [geom["coordinates"][0]]
    if geom["type"] == "MultiPolygon":
        return [poly[0] for poly in geom["coordinates"]]
    return []


def _simplifica(puncte: list, tol: float) -> list:
    """Douglas-Peucker iterativ (fara recursie: unele inele au mii de puncte).

    Inelele GeoJSON sunt INCHISE (ultimul punct = primul). Daca il lasam, segmentul de
    referinta A-B e degenerat, distantele ies 0 si algoritmul arunca tot conturul — exact
    ce s-a intamplat la prima rulare (0 judete). Il taiem si inchidem la final cu `Z`.
    """
    # Rotunjirea la o zecimala face puncte vecine sa coincida. Daca raman lipite, capetele
    # segmentului de referinta pot ajunge identice si toate distantele ies 0 — asa au disparut
    # Iasi si Vasluiul la a doua rulare, desi aveau 268 si 192 de puncte.
    fara_dubluri = [puncte[0]] if puncte else []
    for p in puncte[1:]:
        if p != fara_dubluri[-1]:
            fara_dubluri.append(p)
    puncte = fara_dubluri
    while len(puncte) > 1 and puncte[0] == puncte[-1]:
        puncte = puncte[:-1]
    if len(puncte) < 3:
        return puncte
    pastreaza = [False] * len(puncte)
    pastreaza[0] = pastreaza[-1] = True
    stiva = [(0, len(puncte) - 1)]
    while stiva:
        i, j = stiva.pop()
        if j <= i + 1:
            continue
        ax, ay = puncte[i]
        bx, by = puncte[j]
        dx, dy = bx - ax, by - ay
        norma = math.hypot(dx, dy) or 1e-12
        maxd, idx = 0.0, i
        for k in range(i + 1, j):
            px, py = puncte[k]
            # distanta punct-dreapta (produs vectorial / lungime)
            d = abs(dx * (ay - py) - (ax - px) * dy) / norma
            if d > maxd:
                maxd, idx = d, k
        if maxd > tol:
            pastreaza[idx] = True
            stiva.append((i, idx))
            stiva.append((idx, j))
    return [p for p, tine in zip(puncte, pastreaza) if tine]


def construieste(cale_geojson: str) -> dict:
    with open(cale_geojson, encoding="utf-8") as fh:
        date = json.load(fh)
    judete = [f for f in date["features"] if f["properties"].get("adm0_a3") == "ROU"]
    if not judete:
        raise SystemExit("nu am gasit niciun judet ROU in geojson")

    # Marginile reale ale tarii, ca proiectia sa umple panza fara spatiu mort.
    xs, ys = [], []
    for f in judete:
        for inel in _inele(f["geometry"]):
            for lon, lat in inel:
                xs.append(lon)
                ys.append(lat)
    lon_min, lon_max = min(xs), max(xs)
    lat_min, lat_max = min(ys), max(ys)

    # Equirectangulara cu corectie de latitudine: fara `cos(lat)`, tara apare intinsa pe
    # orizontala. La ~5 grade de latitudine, o singura paralela de referinta e suficienta.
    lat_ref = math.radians((lat_min + lat_max) / 2)
    k = math.cos(lat_ref)
    latime_geo = (lon_max - lon_min) * k
    inaltime_geo = lat_max - lat_min
    scara = LATIME / latime_geo
    inaltime = round(inaltime_geo * scara, 2)

    def proiecteaza(lon, lat):
        x = (lon - lon_min) * k * scara
        y = (lat_max - lat) * scara          # SVG are y in jos
        return (round(x, 1), round(y, 1))

    contur = {}
    for f in judete:
        nume = _normalizeaza(str(f["properties"].get("name") or ""))
        if not nume:
            continue
        bucati = []
        for inel in _inele(f["geometry"]):
            puncte = _simplifica([proiecteaza(lon, lat) for lon, lat in inel], TOLERANTA)
            if len(puncte) < 3:
                continue                      # insulita disparuta la simplificare
            d = "M" + " L".join(f"{x} {y}" for x, y in puncte) + " Z"
            bucati.append(d)
        if bucati:
            contur[nume] = " ".join(bucati)

    return {
        "sursa": "Natural Earth (domeniu public) — ne_10m_admin_1_states_provinces",
        "viewbox": f"0 0 {int(LATIME)} {inaltime}",
        "toleranta": TOLERANTA,
        "judete": dict(sorted(contur.items())),
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    date = construieste(sys.argv[1])
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(date, fh, ensure_ascii=False, separators=(",", ":"))
    marime = os.path.getsize(OUT)
    print(f"{len(date['judete'])} judete -> {OUT} ({marime / 1024:.0f} KB), "
          f"viewBox {date['viewbox']}, toleranta {TOLERANTA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
