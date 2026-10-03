#!/usr/bin/env python3
"""Cate pagini din `output/` au o previzualizare sociala (og:image) care chiar FUNCTIONEAZA.

INTREBAREA 7 din `notes/30-intrebari-imagini-2026-10-03.md`: „Cate pagini ajung fara un
og:image functional — si stim ce vede atunci WhatsApp, LinkedIn sau un crawler?" Un tag
prezent nu e acelasi lucru cu un tag functional: un URL relativ, o cale cu typo, un fisier
sters sau o imagine gazduita pe alt domeniu trec toate de un simplu `grep` si nu produc
niciun card social. Unealta raspunde la intrebarea asa cum e pusa, nu la o aproximare a ei.

CE VERIFICA, pe fiecare pagina HTML din output/ (11.000+, static, fara browser, fara retea):
  1. exista `<meta property="og:image">` si are continut;
  2. URL-ul e ABSOLUT si pe originea site-ului — `og:image` relativ e cel mai frecvent mod
     tacut de a pierde previzualizarea: crawlerul il rezolva in contextul lui, iar
     `og:image:width/height` declarate atunci mint;
  3. fisierul la care trimite exista pe disc DUPA randare (calea, fara `?v=`);
  4. dimensiunile declarate in meta se potrivesc cu fisierul real (citite din header, fara
     Pillow: PNG si JPEG);
  5. `twitter:image` si `og:image` nu se contrazic, si nu exista doua valori `og:image`
     diferite pe aceeasi pagina (prima castiga la Facebook, a doua poate ajunge pe Twitter).

CLASIFICARE (nu toate valorile sunt la fel de utile, si raportul trebuie sa spuna care e care):
  `propriu`    — coperta articolului (1200x630, doar fereastra `OG_COVER_MAX_ARTICLES`);
  `categorie`  — coperta categoriei, `output/og/<categorie>.jpg` (acelasi fisier, mii de pagini);
  `generic`    — `static/og-image.png`, ultimul refugiu (fara el: card gol);
  `necunoscut` — alt URL; numarat, ca sa nu treaca drept „propriu" o regula noua de nume.

Iese 1 cand exista defecte blocante, ca sa poata fi pus in CI la nevoie.

    python tools/og_image_audit.py                       # raport pe output/ curent
    python tools/og_image_audit.py --json raport.json    # + raport masina
    python tools/og_image_audit.py --strict              # avertismentele devin erori

Ruleaza DUPA `python -m generator.main --render-only`. Cifrele nu supravietuiesc unei
randari noi: `cover.jpg` exista doar pentru primele `OG_COVER_MAX_ARTICLES` articole, deci
numarul de pagini pe coperta de categorie se schimba cu fereastra, nu cu calitatea.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output"

# Atributele de meta se cauta pe TAG si pe nume, nu pe o ordine fixa de atribute: `content`
# inaintea lui `property` e la fel de valid si a fost exact forma care a scapat unui grep
# naiv in timpul masuratorii.
TAG_META = re.compile(r"<meta\b([^>]*)/?>", re.I | re.S)
ATTR = re.compile(r"""([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*("([^"]*)"|'([^']*)')""")

DEFECTE = {
    "fara-tag": "nu are deloc <meta property=\"og:image\">",
    "gol": "tag prezent, dar continut gol",
    "relativ": "URL relativ — crawlerul il rezolva in contextul lui",
    "alta-origine": "URL absolut, dar pe alt domeniu decat site-ul",
    "fisier-lipsa": "fisierul nu exista in output/ dupa randare",
}


def _atribute(brut: str) -> dict:
    out = {}
    for nume, _, v1, v2 in ATTR.findall(brut):
        out[nume.lower()] = unescape(v1 if v1 else v2)
    return out


def extrage_meta(html: str) -> dict:
    """Meta-urile relevante pentru previzualizarea sociala, in ordinea din document.

    Lista, nu valoare unica: doua `og:image` diferite pe aceeasi pagina sunt un defect de
    nedeterminat (cine citeste primul castiga), nu o redundanta.
    """
    og: list[str] = []
    twitter: list[str] = []
    lat = inalt = None
    for brut in TAG_META.findall(html):
        a = _atribute(brut)
        if a.get("property") == "og:image":
            og.append((a.get("content") or "").strip())
        elif a.get("name") == "twitter:image":
            twitter.append((a.get("content") or "").strip())
        elif a.get("property") == "og:image:width":
            lat = (a.get("content") or "").strip()
        elif a.get("property") == "og:image:height":
            inalt = (a.get("content") or "").strip()
    return {"og": og, "twitter": twitter, "width": lat, "height": inalt}


def nivel(url_path: str) -> str:
    """Tipul de imagine, dupa cale — clasificare de ROL, nu de calitate."""
    if url_path.startswith("/static/"):
        return "generic"
    if url_path.startswith("/og/") and url_path.endswith(".jpg"):
        return "categorie"
    if url_path.rsplit("/", 1)[-1] in {"cover.jpg", "photo.jpg"}:
        return "propriu"
    return "necunoscut"


def dimensiuni_fisier(cale: Path) -> tuple[int, int] | None:
    """(latime, inaltime) citite din header — PNG sau JPEG, fara Pillow.

    De ce fara Pillow: unealta trebuie sa poata rula si pe un output fara `PIL` instalat
    (verificarea e despre HTML si fisiere, nu despre pixeli). Header-ul ajunge pentru ambele
    formate pe care le scrie randarea.
    """
    try:
        with open(cale, "rb") as fh:
            cap = fh.read(262144)
    except OSError:
        return None
    if cap[:8] == b"\x89PNG\r\n\x1a\n" and len(cap) >= 24:
        return struct.unpack(">II", cap[16:24])
    if cap[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(cap):
            if cap[i] != 0xFF:
                i += 1
                continue
            marker = cap[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            lungime = struct.unpack(">H", cap[i + 2:i + 4])[0]
            # SOF0..SOF15, mai putin DHT (C4), JPG (C8) si DAC (CC)
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                inalt, lat = struct.unpack(">HH", cap[i + 5:i + 9])
                return lat, inalt
            i += 2 + lungime
    return None


def analizeaza_pagina(cale: Path, out_dir: Path, origine: str) -> dict:
    """Verdictul unei pagini: stare, nivel, URL si avertismentele de consistenta."""
    html = cale.read_text(encoding="utf-8", errors="replace")
    m = extrage_meta(html)
    rec = {"pagina": cale.relative_to(out_dir).as_posix(), "stare": "ok", "nivel": None,
           "url": "", "dimensiuni_gresit": False, "twitter_diferit": False, "duplicat": False}
    if not m["og"]:
        rec["stare"] = "fara-tag"
        return rec
    val = m["og"][0]
    rec["url"] = val
    if not val:
        rec["stare"] = "gol"
        return rec
    rec["duplicat"] = len({v for v in m["og"] if v}) > 1
    rec["twitter_diferit"] = bool(m["twitter"]) and m["twitter"][0] != val

    p = urlsplit(val)
    if not p.scheme:
        rec["stare"] = "relativ"
        return rec
    if p.netloc != urlsplit(origine).netloc:
        rec["stare"] = "alta-origine"
        return rec

    rec["nivel"] = nivel(unquote(p.path))
    cale_fisier = out_dir / unquote(p.path).lstrip("/")
    if not cale_fisier.is_file():
        rec["stare"] = "fisier-lipsa"
        return rec
    if m["width"] and m["height"]:
        real = dimensiuni_fisier(cale_fisier)
        try:
            declarat = (int(m["width"]), int(m["height"]))
        except ValueError:
            rec["dimensiuni_gresit"] = True
            return rec
        # Doar cand fisierul chiar se citeste: un format necunoscut nu e o dovada de minciuna.
        rec["dimensiuni_gresit"] = real is not None and real != declarat
    return rec


def masoara(out_dir: Path | str = OUTPUT, origine: str = "https://izz.ro",
            exemple_max: int = 10) -> dict:
    """Agregatul pe tot `output/`. Fara retea; ordinea de parcurgere e sortata, deci stabila."""
    out_dir = Path(out_dir)
    total = 0
    blocante: list[dict] = []
    stari: dict[str, int] = {}
    niveluri: dict[str, int] = {}
    avertismente = {"dimensiuni_gresit": 0, "twitter_diferit": 0, "duplicat": 0,
                    "nivel_necunoscut": 0}
    exemple: dict[str, list[str]] = {}
    url_distincte: set[str] = set()
    for dirpath, dirnames, files in os.walk(out_dir):
        dirnames.sort()
        for f in sorted(files):
            if not f.endswith(".html"):
                continue
            total += 1
            r = analizeaza_pagina(Path(dirpath) / f, out_dir, origine)
            stari[r["stare"]] = stari.get(r["stare"], 0) + 1
            # Doar URL-urile care chiar servesc un card: un URL relativ spart nu e o imagine
            # "distincta", e acelasi fisier nereusit numarat de doua ori.
            if r["stare"] == "ok":
                url_distincte.add(r["url"].split("?")[0])
            if r["nivel"]:
                niveluri[r["nivel"]] = niveluri.get(r["nivel"], 0) + 1
                if r["nivel"] == "necunoscut":
                    avertismente["nivel_necunoscut"] += 1
            for k in ("dimensiuni_gresit", "twitter_diferit", "duplicat"):
                if r[k]:
                    avertismente[k] += 1
            if r["stare"] != "ok":
                blocante.append(r)
                if len(exemple.setdefault(r["stare"], [])) < exemple_max:
                    exemple[r["stare"]].append(r["pagina"])
    return {
        "pagini": total,
        "functionale": total - len(blocante),
        "blocante": len(blocante),
        "stari": stari,
        "niveluri": niveluri,
        "avertismente": avertismente,
        "url_distincte": len(url_distincte),
        "exemple": exemple,
        "origine": origine,
    }


def raport_text(r: dict) -> str:
    linii = [f">> og:image: {r['functionale']}/{r['pagini']} pagini cu previzualizare sociala "
             f"functionala; {r['blocante']} cu defecte blocante"]
    if r["blocante"]:
        detalii = ", ".join(f"{k}={v}" for k, v in sorted(r["stari"].items()) if k != "ok")
        linii.append(f"   defecte: {detalii}")
        for stare, pagini in sorted(r["exemple"].items()):
            linii.append(f"   {stare}: {', '.join(pagini)}")
    imagini = ", ".join(f"{k} {v}" for k, v in sorted(r["niveluri"].items(),
                                                     key=lambda kv: -kv[1]))
    linii.append(f"   imagini: {imagini} ({r['url_distincte']} URL-uri distincte)")
    active = ", ".join(f"{k}={v}" for k, v in sorted(r["avertismente"].items()) if v)
    linii.append(f"   avertismente: {active or 'niciunul'}")
    return "\n".join(linii)


def main() -> int:
    ap = argparse.ArgumentParser(description="og:image functional pe paginile din output/")
    ap.add_argument("--output-dir", default=str(OUTPUT))
    ap.add_argument("--origine", default=None,
                    help="originea site-ului (implicit din generator.config.SITE)")
    ap.add_argument("--json", dest="json_path", default=None, help="scrie raportul masina aici")
    ap.add_argument("--strict", action="store_true", help="avertismentele devin erori")
    ap.add_argument("--exemple", type=int, default=10, help="cate pagini-exemplu per defect")
    args = ap.parse_args()

    out_dir = Path(args.output_dir)
    if not out_dir.is_dir():
        print(f"OG AUDIT: {out_dir} lipseste — ruleaza intai randarea")
        return 0
    origine = args.origine
    if origine is None:
        try:
            sys.path.insert(0, str(ROOT))
            from generator import config
            origine = config.SITE["url"]
        except Exception:
            origine = "https://izz.ro"
    r = masoara(out_dir, origine, args.exemple)
    print(raport_text(r))
    if args.json_path:
        Path(args.json_path).write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n",
                                        encoding="utf-8")
    if r["blocante"]:
        return 1
    if args.strict and any(r["avertismente"].values()):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
