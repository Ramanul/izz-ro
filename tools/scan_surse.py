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
import csv
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


def _surse_din_catalog(cale: str, limita: int = 0) -> dict:
    """Construieste dictionarul de surse din `data/primarii_status.csv`.

    Catalogul e recensamantul primariilor (3187 de randuri), nu lista surselor integrate in izz.ro
    (129). Diferenta conteaza: pe cele integrate garda deja filtreaza la fetch, deci un scan acolo
    masoara in mare parte propria noastra aparare. Catalogul e suprafata NEATINSA — acolo „0
    respingeri" chiar inseamna ceva.

    Ia doar randurile cu `rss_ok=yes` si `rss_url` nevid; restul n-au ce fi scanate. Deduplica pe
    URL, fiindca doua localitati pot arata catre acelasi feed (4 cazuri masurate pe 2026-08-14).
    """
    surse: dict[str, dict] = {}
    vazute: set[str] = set()
    with open(cale, encoding="utf-8", newline="") as fh:
        for rand in csv.DictReader(fh):
            url = (rand.get("rss_url") or "").strip()
            if not url or rand.get("rss_ok") != "yes" or url in vazute:
                continue
            vazute.add(url)
            judet = (rand.get("judet") or "??").strip()
            loc = (rand.get("localitate") or "??").strip()
            key = f"cat_{judet}_{loc}".replace(" ", "-")
            surse[key] = {"url": url, "name": f"Primaria {loc} ({judet})", "lang": "ro"}
            if limita and len(surse) >= limita:
                break
    return surse


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
    # Terminalul Windows porneste pe cp1252, iar titlurile primariilor au diacritice: fara asta
    # scanul moare cu UnicodeEncodeError FIX la afisarea primei respingeri — adica exact cand
    # a gasit ceva. Masurat pe 2026-08-14, esantion de 50.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser()
    ap.add_argument("--toate", action="store_true",
                    help="scaneaza si sursele de presa, nu doar cele oficiale")
    ap.add_argument("--json", help="scrie rezultatul brut in fisierul asta")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--catalog", nargs="?", const="data/primarii_status.csv",
                    help="scaneaza catalogul de primarii (implicit data/primarii_status.csv) "
                         "in loc de sursele integrate in izz.ro")
    ap.add_argument("--limita", type=int, default=0,
                    help="opreste-te dupa N surse (esantion; 0 = toate)")
    args = ap.parse_args()

    if args.catalog:
        surse = _surse_din_catalog(args.catalog, args.limita)
        eticheta = f"catalog {args.catalog}"
    else:
        surse = {k: v for k, v in config.SOURCES.items()
                 if args.toate or k.startswith(OFICIALE)}
        eticheta = "toate" if args.toate else "doar oficiale"
    print(f">> scanez {len(surse)} surse ({eticheta}), {args.workers} in paralel")

    pas = 100 if len(surse) > 300 else 25
    rezultate = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(_scaneaza, k, v): k for k, v in surse.items()}
        for i, fut in enumerate(concurrent.futures.as_completed(futures), 1):
            rezultate.append(fut.result())
            if i % pas == 0:
                print(f"   ... {i}/{len(surse)}", flush=True)

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
        for r in erori[:20]:
            print(f"  [{r['key']}] {r['eroare'][:90]}")
        if len(erori) > 20:
            # Pe catalog erorile sunt sute; lista intreaga inunda terminalul fara sa adauge nimic.
            # Detaliul complet e in --json, aici ramane distributia pe tip de esec.
            tipuri: dict[str, int] = {}
            for r in erori:
                tipuri[r["eroare"].split(":")[0]] = tipuri.get(r["eroare"].split(":")[0], 0) + 1
            print(f"  ... si inca {len(erori) - 20}. Pe tip de esec:")
            for tip, n in sorted(tipuri.items(), key=lambda kv: -kv[1]):
                print(f"     {n:5d}  {tip}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(rezultate, fh, ensure_ascii=False, indent=1)
        print(f"\n>> brut in {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
