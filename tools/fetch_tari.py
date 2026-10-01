#!/usr/bin/env python
"""Datasetul de TARI (data/tari.json) — construit rar din Wikidata, comis in repo.

De ce exista: stirile EXTERN isi numesc locul dupa Tara ("cutremur in Nepal",
"inundatii in Turcia"), iar geo.py acopera doar Romania + regiuni. Cu tari.json,
generator.eventdata poate rezolva tara din titlu -> cutie de cautare pentru EMSC
(coperta de cutremur extern) si numele englez pentru Commons (poze de eveniment).

Sursa: SPARQL pe Wikidata (state suverane P31=Q3624078): numele RO, numele EN,
coordonatele (P625), aria (P2046). Cutia de cautare = centroid ± jumatatea
dimensiunii estimate din arie, cu margine 1.35x — niciodata bataie de mana.

  python tools/fetch_tari.py        # interogheaza Wikidata, rescrie data/tari.json

Rulare rara: datasetul e comis; build-ul nu depinde de Wikidata (acelasi principiu
ca localities.json).
"""
import json
import math
import os
import re
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "tari.json")
UA = "izz.ro-pipeline/1.0 (dataset tari; contact: contact@izz.ro)"

SPARQL = """
SELECT ?iso2 ?ro ?en ?coord ?area WHERE {
  ?c wdt:P31 wd:Q3624078 ; wdt:P297 ?iso2 ; wdt:P625 ?coord ; wdt:P2046 ?area .
  ?c rdfs:label ?ro . FILTER(LANG(?ro) = "ro")
  ?c rdfs:label ?en . FILTER(LANG(?en) = "en")
}
"""


def _sparql() -> dict:
    qs = urllib.parse.urlencode({"query": SPARQL})
    req = urllib.request.Request(
        "https://query.wikidata.org/sparql?" + qs,
        headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
    return json.load(urllib.request.urlopen(req, timeout=60))


def _parse_coord(wkt: str) -> tuple[float, float] | None:
    m = re.match(r"Point\((-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)\)", wkt or "")
    if not m:
        return None
    return float(m.group(2)), float(m.group(1))  # lat, lon


def main() -> int:
    data = _sparql()
    tari: dict[str, dict] = {}
    for b in data["results"]["bindings"]:
        iso2 = b["iso2"]["value"]
        coord = _parse_coord(b["coord"]["value"])
        area = float(b["area"]["value"])
        ro, en = b["ro"]["value"], b["en"]["value"]
        if not coord or not ro or iso2 in tari:
            continue
        half = round(math.sqrt(max(area, 100.0)) / 111 / 2 * 1.35, 2)
        tari[iso2] = {"ro": ro, "en": en, "lat": round(coord[0], 3),
                      "lon": round(coord[1], 3), "jumatate_grade": half}
    by_name: dict[str, list[dict]] = {}
    for rec in tari.values():
        by_name.setdefault(rec["ro"].lower(), []).append(rec)
    json.dump({"by_iso": tari, "by_name": dict(sorted(by_name.items()))},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              sort_keys=True)
    print(f"tari scrise: {len(tari)} -> {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
