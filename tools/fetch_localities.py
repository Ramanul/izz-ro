#!/usr/bin/env python
"""Construieste `data/localities.json` — datasetul de UAT-uri din Romania (Wikidata).

Se ruleaza RAR si MANUAL (nu din build.yml): lista unitatilor administrative se schimba
o data la ani, iar pipeline-ul trebuie sa poata construi site-ul fara sa depinda de
disponibilitatea Wikidata. Rezultatul se comite in repo.

Detalii care au costat masuratori si merita pastrate:
- Clasele corecte sunt Q659103 (comuna), Q16858213 (oras), Q640364 (municipiu), cerute
  DIRECT cu wdt:P31. `P31/P279* Q15284` rateaza TOATE orasele (nu sunt sub acea clasa),
  iar `P31/P279* Q486972` face endpointul sa raspunda 504.
- Formatul cerut e XML, nu JSON: raspunsul JSON de ~2 MB vine trunchiat intermitent prin
  proxy, cu eroare de parsare determinista pe acelasi offset. `&format=csv` e ignorat.

  python tools/fetch_localities.py            # scrie data/localities.json
"""
import collections
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from generator.localities import norm  # noqa: E402

OUT = os.path.join(ROOT, "data", "localities.json")
UA = {"User-Agent": "izz.ro-localities/1.0 (https://izz.ro)"}
ENDPOINT = "https://query.wikidata.org/sparql"
NS = "{http://www.w3.org/2005/sparql-results#}"

QUERY = """
SELECT ?item ?itemLabel ?judetLabel ?img ?pop WHERE {
  VALUES ?cls { wd:Q659103 wd:Q16858213 wd:Q640364 }
  ?item wdt:P31 ?cls ; wdt:P17 wd:Q218 .
  OPTIONAL { ?item wdt:P131 ?judet . }
  OPTIONAL { ?item wdt:P18 ?img . }
  OPTIONAL { ?item wdt:P1082 ?pop . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "ro,en". }
}
"""


def _commons_filename(uri: str) -> str:
    """URI Special:FilePath -> numele fisierului, decodat ('Bistri%C8%9Ba.jpg' -> 'Bistrița.jpg')."""
    if not uri:
        return ""
    return urllib.parse.unquote(uri.rsplit("/", 1)[-1]).replace("_", " ")


def _rows(xml_text: str) -> list:
    out = []
    for result in ET.fromstring(xml_text).iter(f"{NS}result"):
        vals = {}
        for b in result.findall(f"{NS}binding"):
            node = b.find(f"{NS}uri")
            if node is None:
                node = b.find(f"{NS}literal")
            vals[b.get("name")] = (node.text or "") if node is not None else ""
        out.append(vals)
    return out


def fetch(retries: int = 4) -> list:
    url = f"{ENDPOINT}?query={urllib.parse.quote(QUERY)}"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=220) as r:
                raw = r.read().decode("utf-8")
            return _rows(raw)          # ET ridica exceptie pe raspuns trunchiat -> retry
        except Exception as exc:
            print(f"  ! incercarea {attempt + 1}/{retries}: {str(exc)[:90]}")
            if attempt == retries - 1:
                raise
            time.sleep(3 * (attempt + 1))
    return []


def build(rows: list) -> dict:
    by_name = collections.defaultdict(list)
    kept = skipped = 0
    for v in rows:
        label = (v.get("itemLabel") or "").strip()
        qid = (v.get("item") or "").rsplit("/", 1)[-1]
        # eticheta nerezolvata (SERVICE label cade inapoi pe QID) -> inutilizabila la potrivire
        if not label or not qid or re.fullmatch(r"Q\d+", label):
            skipped += 1
            continue
        pop = (v.get("pop") or "").strip()
        rec = {"qid": qid, "label": label,
               "judet": (v.get("judetLabel") or "").strip(),
               "img": _commons_filename((v.get("img") or "").strip()),
               "pop": int(float(pop)) if pop else 0}
        key = norm(label)
        # acelasi UAT poate aparea de mai multe ori (mai multe valori P18/P1082)
        if any(c["qid"] == rec["qid"] for c in by_name[key]):
            continue
        by_name[key].append(rec)
        kept += 1
    return {"source": "Wikidata (Q659103 comuna / Q16858213 oras / Q640364 municipiu)",
            "count": kept, "by_name": dict(by_name)}


def main() -> int:
    print(">> interogare Wikidata...")
    rows = fetch()
    data = build(rows)
    if data["count"] < 3000:
        print(f"!! doar {data['count']} UAT-uri (asteptat ~3178) — NU se scrie fisierul")
        return 1
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    withimg = sum(1 for recs in data["by_name"].values() for c in recs if c["img"])
    print(f">> {OUT}: {data['count']} UAT-uri, {len(data['by_name'])} nume distincte, "
          f"{withimg} cu fotografie ({os.path.getsize(OUT) // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
