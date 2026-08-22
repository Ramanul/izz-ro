"""Reconstruieste arhiva completa din istoricul git al lui data/articles.json.

DE CE EXISTA: `state.expire()` scoate articolele din starea curenta dupa
ARTICLE_TTL_DAYS (30), si asta a fost citit de mai multe ori ca „pipeline-ul isi
sterge arhiva zilnic, ireversibil". Nu e adevarat in repo-ul asta: `articles.json`
e COMIS la fiecare rulare (~2h), iar un articol traieste 30 de zile — deci apuca sa
fie comis de sute de ori inainte sa expire. Masurat 2026-08-04 pe 265 de commituri:
7001 articole distincte recuperabile, acoperire continua 2026-06-27 -> 2026-08-04,
fata de 2128 in starea curenta. Nimic nu s-a pierdut.

DE CE NU SE COMITE REZULTATUL: ar fi ~7 MB de blob-uri noi care dubleaza date deja
prezente in istoric. `data/archive/` e in .gitignore; cine are nevoie de seria
longitudinala ruleaza unealta asta (~2 min prima data, secunde la reluari).

Rulare:
    python tools/arhiva.py              # incremental, scrie data/archive/YYYY-MM.json
    python tools/arhiva.py --stats      # doar raporteaza, nu scrie
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARHIVA = os.path.join(ROOT, "data", "archive")
META = os.path.join(ARHIVA, "_meta.json")
CALE = "data/articles.json"


def _git(*args: str) -> str:
    """git cu encoding explicit: pe Windows locale-ul implicit (cp1252) pica pe diacritice."""
    return subprocess.run(["git", "-C", ROOT, *args],
                          capture_output=True, encoding="utf-8", errors="replace").stdout


def _articole(obj):
    """Starea a fost si lista simpla, si dict cu cheia `articles`. Accepta ambele."""
    return obj["articles"] if isinstance(obj, dict) and "articles" in obj else obj


def commituri() -> list:
    """Cele care ating articles.json, de la cel mai VECHI la cel mai nou.

    Ordinea conteaza: pastram prima aparitie a fiecarui URL, deci trebuie sa
    intalnim intai commitul vechi. `git log` da invers, de-aia reversed().
    """
    linii = _git("log", "--format=%H\t%cI", "--", CALE).strip().splitlines()
    return list(reversed([tuple(l.split("\t")) for l in linii if "\t" in l]))


def incarca_arhiva() -> tuple:
    """(dict url -> articol, set de sha-uri deja procesate). Goale daca nu exista."""
    if not os.path.isdir(ARHIVA):
        return {}, set()
    dupa_url = {}
    for nume in sorted(os.listdir(ARHIVA)):
        if not nume.endswith(".json") or nume.startswith("_"):
            continue
        with open(os.path.join(ARHIVA, nume), encoding="utf-8") as fh:
            for a in json.load(fh):
                dupa_url[a["url"]] = a
    procesate = set()
    if os.path.exists(META):
        with open(META, encoding="utf-8") as fh:
            procesate = set(json.load(fh).get("commituri", []))
    return dupa_url, procesate


def scrie(dupa_url: dict, procesate: set) -> dict:
    """Imparte pe luna de publicare. Sharding, ca sa nu ajungem la un fisier de 50 MB."""
    os.makedirs(ARHIVA, exist_ok=True)
    pe_luna = {}
    for a in dupa_url.values():
        luna = (a.get("published") or a.get("vazut_prima_data") or "necunoscut")[:7]
        pe_luna.setdefault(luna, []).append(a)
    for luna, arts in pe_luna.items():
        arts.sort(key=lambda x: x.get("published") or "")
        with open(os.path.join(ARHIVA, f"{luna}.json"), "w", encoding="utf-8") as fh:
            json.dump(arts, fh, ensure_ascii=False, indent=1)
    with open(META, "w", encoding="utf-8") as fh:
        json.dump({"commituri": sorted(procesate), "articole": len(dupa_url)}, fh)
    return pe_luna


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true", help="raporteaza fara sa scrie nimic")
    arg = ap.parse_args()

    dupa_url, procesate = incarca_arhiva()
    plecat_de_la = len(dupa_url)
    toate = commituri()
    de_facut = [(h, d) for h, d in toate if h not in procesate]
    print(f">> {len(toate)} commituri ating {CALE}; {len(de_facut)} neprocesate")

    for i, (h, data) in enumerate(de_facut, 1):
        brut = _git("show", f"{h}:{CALE}")
        if not brut:
            procesate.add(h)
            continue
        try:
            arts = _articole(json.loads(brut))
        except ValueError:
            # un commit cu JSON trunchiat nu trebuie sa opreasca reconstructia
            print(f"!! {h[:8]}: JSON invalid, sarit")
            procesate.add(h)
            continue
        for a in arts:
            u = a.get("url")
            if u and u not in dupa_url:
                # cand a intrat efectiv in pipeline — `published` e data SURSEI, nu a noastra
                dupa_url[u] = {**a, "vazut_prima_data": data}
        procesate.add(h)
        if i % 50 == 0:
            print(f"   {i}/{len(de_facut)} commituri, {len(dupa_url)} articole")

    noi = len(dupa_url) - plecat_de_la
    if arg.stats:
        print(f">> --stats: {len(dupa_url)} articole distincte ({noi} noi), NU s-a scris nimic")
        return 0

    pe_luna = scrie(dupa_url, procesate)
    print(f">> arhiva: {len(dupa_url)} articole distincte (+{noi}) in {len(pe_luna)} fisiere")
    for luna in sorted(pe_luna):
        print(f"   {luna}: {len(pe_luna[luna])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
