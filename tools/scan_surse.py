"""Scaneaza feedurile surselor oficiale cu garda de ingestie si raporteaza ce ar fi respins.

De ce exista
------------
Pe 2026-08-09 o primarie compromisa (Rovinari) a impins warez pe izz.ro; pe 11 aug s-a gasit
a doua (Cajvana, defaced). Ambele au fost descoperite din INTAMPLARE — una fiindca proprietarul
a vazut-o pe site, alta masurand pentru altceva. Intrebarea „cate ALTE surse din catalog sunt in
aceeasi situatie" a stat deschisa fiindca nimeni nu masurase INTRAREA, doar iesirea.

De ce nu ajunge sa rulezi garda peste `data/articles.json`, cum s-a facut pe 12 aug: masuratoarea
aia e **partial circulara**. Articolele ingerate DUPA ce garda a inceput sa functioneze au fost
deja filtrate la fetch, deci „0 respingeri" pentru ele nu dovedeste ca sursa e curata — dovedeste
ca garda si-a facut treaba. Cele 8 de la Rovinari se vedeau acolo doar fiindca fusesera ingerate
INAINTE de garda. Un scan pe feedul VIU nu are problema asta: vede ce publica sursa acum,
indiferent ce am ingerat noi.

Cost: 129 de cereri HTTP, adica exact cat face o rulare normala de pipeline. Nu e trafic in plus
fata de ce trimitem oricum ora de ora.

Nu ingereaza nimic si nu scrie in `data/`. Doar citeste si raporteaza.

    python tools/scan_surse.py                # toate sursele oficiale (pl_/cj_/pr_)
    python tools/scan_surse.py --toate        # inclusiv sursele de presa
    python tools/scan_surse.py --json out.json
"""
import argparse
import concurrent.futures
import json
import os
import socket
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import feedparser  # noqa: E402

from generator import config, fetch, guard  # noqa: E402
from generator.util import clean_html  # noqa: E402

OFICIALE = ("pl_", "cj_", "pr_")


def _scaneaza(key: str, sursa: dict) -> dict:
    """Citeste feedul unei surse si trece fiecare intrare prin garda completa.

    Nu foloseste `fetch._fetch_one`: aia FILTREAZA si arunca itemele respinse, iar aici exact
    alea ne intereseaza. Reutilizeaza insa UA-ul, timeout-ul si plafonul de raspuns, ca scanul
    sa se poarte la fel ca productia fata de serverele primariilor.
    """
    rez = {"key": key, "nume": sursa.get("name", ""), "url": sursa.get("url", ""),
           "intrari": 0, "respinse": [], "eroare": None}
    try:
        req = urllib.request.Request(sursa["url"], headers={"User-Agent": fetch.USER_AGENT})
        with urllib.request.urlopen(req, timeout=fetch.TIMEOUT) as resp:
            raw = fetch._read_limitat(resp)
    except (urllib.error.HTTPError, urllib.error.URLError, socket.timeout, ValueError) as exc:
        rez["eroare"] = f"{type(exc).__name__}: {exc}"
        return rez

    if fetch._is_challenge(raw):
        # Sursa e vie; gazda ne-a servit un interstitial. NU e o sursa curata si nici una moarta
        # — e nemasurata. Daca o numim „0 respingeri" mintim in directia linistitoare.
        rez["eroare"] = "challenge anti-bot (nemasurabil, NU inseamna curat)"
        return rez

    feed = feedparser.parse(raw)
    lang = sursa.get("lang", "ro")
    for entry in feed.entries:
        titlu = clean_html(entry.get("title") or "")
        if not titlu:
            continue
        rez["intrari"] += 1
        corp = fetch._entry_body(entry)
        motiv = (guard.verdict(titlu, corp)
                 or guard.url_ostil(entry.get("link", "") or "")
                 or guard.anomalie(titlu, lang))
        if motiv:
            rez["respinse"].append({"titlu": titlu[:120], "motiv": motiv})
    return rez


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--toate", action="store_true",
                    help="scaneaza si sursele de presa, nu doar cele oficiale")
    ap.add_argument("--json", help="scrie rezultatul brut in fisierul asta")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    surse = {k: v for k, v in config.SOURCES.items()
             if args.toate or k.startswith(OFICIALE)}
    print(f">> scanez {len(surse)} surse ({'toate' if args.toate else 'doar oficiale'}), "
          f"{args.workers} in paralel")

    rezultate = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(_scaneaza, k, v): k for k, v in surse.items()}
        for i, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            rezultate.append(fut.result())
            if i % 25 == 0:
                print(f"   ... {i}/{len(surse)}")

    rezultate.sort(key=lambda r: (-len(r["respinse"]), r["key"]))
    murdare = [r for r in rezultate if r["respinse"]]
    erori = [r for r in rezultate if r["eroare"]]
    masurate = [r for r in rezultate if not r["eroare"]]
    carantina = [r for r in murdare
                 if len(r["respinse"]) >= guard.PRAG_CARANTINA]

    print()
    print(f"MASURATE     : {len(masurate)}/{len(surse)}")
    print(f"NEMASURABILE : {len(erori)}  (eroare de retea sau challenge — NU 'curate')")
    print(f"CU RESPINGERI: {len(murdare)}")
    print(f"IN CARANTINA : {len(carantina)}  (prag {guard.PRAG_CARANTINA}+ respingeri)")
    print()

    for r in murdare:
        eticheta = "  <<< CARANTINA" if len(r["respinse"]) >= guard.PRAG_CARANTINA else ""
        print(f"[{r['key']}] {len(r['respinse'])}/{r['intrari']} respinse — "
              f"{r['url']}{eticheta}")
        for x in r["respinse"][:8]:
            print(f"     - {x['titlu']!r}  [{x['motiv']}]")

    if erori:
        print()
        print("NEMASURABILE (fiecare e o gaura, nu o sursa curata):")
        for r in erori:
            print(f"  [{r['key']}] {r['eroare'][:90]}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(rezultate, fh, ensure_ascii=False, indent=1)
        print(f"\n>> brut in {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
