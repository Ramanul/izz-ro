#!/usr/bin/env python3
"""Pasul 1 din `specs/anomalie-linkuri.md`: unde duc linkurile din corpurile de articol.

DE CE. `specs/securitate-ingestie.md` §5.1 declara deschis ca detectia de anomalie e
livrata pe o singura axa din trei — limba. Ce nu prinde: un defacement scris in ROMANA.
Articolul „Hacked by Chinafans" de la cajvana.ro a trecut prin toate cele cinci straturi
din `guard.verdict` si a stat live doua zile; corpul lui continea linkuri catre
`t.me/Hack_0xTeam`. Destinatia linkurilor e singurul semnal care merge la n=1 (Cajvana
avea UN articol la noi) si nu depinde de limba.

DE CE MASURATOARE INAINTE DE GARDA. R3: pragurile se MASOARA, nu se aleg. Unele primarii
chiar au canal de Telegram; o lista de gazde interzise scrisa dupa cap ar respinge articole
legitime. Scriptul asta produce cifrele din care se alege lista, si NU decide nimic.

DE CE RULEAZA PE RUNNER. Site-urile de stiri sunt refuzate de proxy-ul de agent dintr-o
sesiune remote (`CONNECT tunnel failed 403`), dar runnerul de GitHub Actions ajunge la ele.
Al patrulea canal din CLAUDE.md §12a.

LIMITA, SPUSA EXPLICIT. Scriptul citeste feedurile cu `feedparser`, nu prin stratul HTTP al
pipeline-ului. `feed_check.py` a facut aceeasi alegere si a fost o greseala ACOLO, fiindca
raporta SANATATEA sursei si vedea 429/timeout pe surse pe care pipeline-ul le recupereaza.
Aici nu se raporteaza sanatate: se numara gazde. O sursa care nu raspunde inseamna doar mai
putine esantioane, iar numarul lor e tiparit. Confuzia din `feed_check.py` nu se reproduce.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from html import unescape
from urllib.parse import urlsplit

HREF = re.compile(r"""<a\b[^>]*?\bhref\s*=\s*["']([^"']+)["']""", re.IGNORECASE)

# Clase de destinatie, NU o lista de interdictii. Ce inseamna fiecare cifra decide omul.
CLASE: dict[str, tuple[str, ...]] = {
    "mesagerie":    ("t.me", "telegram.me", "telegram.org", "wa.me", "chat.whatsapp.com"),
    "file-locker":  ("mediafire.com", "mega.nz", "anonfiles.com", "gofile.io", "dropmefiles.com",
                     "zippyshare.com", "1fichier.com"),
    "torrent":      ("thepiratebay.org", "1337x.to", "rarbg.to", "torrent", "magnet"),
    "scurtatura":   ("bit.ly", "tinyurl.com", "goo.gl", "ow.ly", "cutt.ly", "is.gd", "t.co"),
    "paste":        ("pastebin.com", "ghostbin.com", "justpaste.it", "controlc.com"),
    "retea-sociala": ("facebook.com", "instagram.com", "x.com", "twitter.com", "youtube.com",
                      "tiktok.com", "linkedin.com"),
}


def gazde_din_html(html: str) -> list[str]:
    """Gazdele din `href`-urile unui corp BRUT, inainte de `clean_html`.

    Exact informatia pe care pipeline-ul o arunca azi: `util.clean_html()` scoate tagurile,
    deci `guard.verdict(titlu, corp)` nu mai are ce vedea.
    """
    gazde = []
    for url in HREF.findall(html or ""):
        try:
            gazda = urlsplit(unescape(url.strip())).hostname or ""
        except ValueError:
            continue
        if gazda:
            gazde.append(gazda.lower().removeprefix("www."))
    return gazde


def clasifica(gazda: str, gazda_sursei: str = "") -> str:
    """Clasa unei gazde. `proprie` = acelasi domeniu cu sursa, cazul covarsitor si normal."""
    gazda = (gazda or "").lower().removeprefix("www.")
    sursa = (gazda_sursei or "").lower().removeprefix("www.")
    if sursa and (gazda == sursa or gazda.endswith("." + sursa) or sursa.endswith("." + gazda)):
        return "proprie"
    for clasa, semne in CLASE.items():
        if any(semn in gazda for semn in semne):
            return clasa
    return "alta"


def e_local(cheie: str) -> bool:
    """Sursele de primarie/consiliu, care sunt populatia sensibila (cazul Cajvana)."""
    return cheie.startswith(("pl_", "cj_"))


def raport(numarare: dict[str, Counter], esantioane: dict[str, int]) -> list[str]:
    """Randurile raportului. Pur, deci testabil fara retea."""
    linii = []
    for grup in ("local", "national"):
        total = sum(numarare[grup].values())
        linii.append(f"\n=== {grup.upper()} — {esantioane[grup]} articole, {total} linkuri ===")
        if not total:
            linii.append("  (niciun link)")
            continue
        for clasa, n in numarare[grup].most_common():
            linii.append(f"  {clasa:<16} {n:>6}  ({n / total * 100:5.1f}%)")
    return linii


def main(argv: list[str]) -> int:
    try:
        import feedparser
    except ImportError:
        print("LIPSA: feedparser. `pip install -r requirements.txt`.")
        return 2
    sys.path.insert(0, ".")
    from generator.config import SOURCES

    plafon = int(argv[1]) if len(argv) > 1 else 40
    numarare = {"local": Counter(), "national": Counter()}
    esantioane = {"local": 0, "national": 0}
    surse_moarte = []

    for cheie, sursa in list(SOURCES.items())[:plafon]:
        url = sursa.get("url") or ""
        if not url or sursa.get("type"):     # doar feeduri, nu sitemap/html_list
            continue
        grup = "local" if e_local(cheie) else "national"
        gazda_sursei = urlsplit(url).hostname or ""
        try:
            feed = feedparser.parse(url)
        except Exception as exc:             # noqa: BLE001 - o sursa moarta nu opreste masuratoarea
            surse_moarte.append(f"{cheie}: {type(exc).__name__}")
            continue
        if not feed.entries:
            surse_moarte.append(f"{cheie}: 0 iteme")
            continue
        for entry in feed.entries[:8]:
            brut = " ".join([c.get("value") or "" for c in (entry.get("content") or [])
                             if isinstance(c, dict)]
                            + [entry.get("summary") or "", entry.get("description") or ""])
            esantioane[grup] += 1
            for gazda in gazde_din_html(brut):
                numarare[grup][clasifica(gazda, gazda_sursei)] += 1

    print("\n".join(raport(numarare, esantioane)))
    if surse_moarte:
        print(f"\nSurse fara esantion ({len(surse_moarte)}): {', '.join(surse_moarte[:12])}")
    print("\nCifrele de mai sus NU decid nimic. Lista de gazde a garzii se alege din ele,")
    print("cu fals-pozitivele numarate — `specs/anomalie-linkuri.md`, pasul 2.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
