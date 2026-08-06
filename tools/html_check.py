#!/usr/bin/env python
"""Verifica HTML-ul CONSTRUIT din output/: legaturi interne moarte, ancore inexistente,
imagini fara alt, active lipsa.

  python tools/html_check.py            # 0 = ok, 1 = probleme peste prag
  python tools/html_check.py --raport   # doar numara, nu pica niciodata (calibrare)

DE CE EXISTA. `tools/qa_check.py` auditeaza DATELE (surse incoerente, categorii goale, rata de
duplicate) — nimic nu se uita la HTML-ul rezultat. Deci o regresie de template care sparge o
legatura interna sau scoate un `alt` ajunge pe live si se vede abia in Search Console, saptamani
mai tarziu. Asta e gaura pe care findingul #25 (html-proofer) o numeste.

STDLIB-ONLY, deliberat. `html-proofer` e Ruby, `html5validator` are nevoie de Java (`vnu.jar`).
Ambele ar adauga un runtime intreg in CI pentru un set de verificari pe care `HTMLParser` le face
in cateva secunde. Ce PIERDEM asa: validarea structurala a HTML-ului (taguri neinchise, atribute
interzise). Acceptabil aici — sabloanele sunt Jinja2 cu autoescape, deci HTML-ul e bine format
prin constructie, iar defectele noastre reale sunt de LEGATURA, nu de sintaxa.

NU verifica legaturi EXTERNE: ar face suita dependenta de retea si de disponibilitatea a ~75 de
publicatii, exact ce `tests.yml` evita deliberat (feedcheck ruleaza separat, non-blocant).
"""
import argparse
import os
import sys
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")
SITE = "https://izz.ro"

# Elemente pe care un `alt` gol e CORECT, nu o scapare: imaginea e decorativa si sablonul
# o ascunde deja de cititoarele de ecran (`aria-hidden` pe cardul-parinte, `_card.html`).
# De aceea se verifica ABSENTA atributului, nu `alt=""`.


class _Pagina(HTMLParser):
    """Aduna din pagina: legaturi, surse, ancore tinta si imaginile fara `alt`."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.linkuri: list = []       # href-uri (a, link)
        self.surse: list = []         # src/srcset (img, source, script)
        self.id_uri: set = set()
        self.img_fara_alt = 0
        self.total_img = 0

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        if ad.get("id"):
            self.id_uri.add(ad["id"])
        if ad.get("name") and tag == "a":
            self.id_uri.add(ad["name"])
        if tag == "a" and ad.get("href"):
            self.linkuri.append(ad["href"])
        elif tag == "link" and ad.get("href") and "stylesheet" in (ad.get("rel") or ""):
            self.surse.append(ad["href"])
        elif tag == "img":
            self.total_img += 1
            if "alt" not in ad:
                self.img_fara_alt += 1
            if ad.get("src"):
                self.surse.append(ad["src"])
        elif tag in ("script", "source") and (ad.get("src") or ad.get("srcset")):
            # srcset poate purta mai multi candidati; aici e mereu unul singur (format webp)
            self.surse.append((ad.get("src") or ad["srcset"]).split(",")[0].strip().split(" ")[0])


def _intern(url: str) -> str | None:
    """Calea interna a unui URL, sau None daca e extern / neverificabil aici."""
    if url.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return None
    if url.startswith(SITE):
        url = url[len(SITE):] or "/"
    elif url.startswith(("http://", "https://", "//")):
        return None
    return url or None


def _fisier_pentru(cale: str) -> str:
    """/politic/x/ -> output/politic/x/index.html ; /feed.xml -> output/feed.xml"""
    cale = unquote(cale.split("?")[0])
    rel = cale.lstrip("/")
    tinta = os.path.join(OUT, rel.replace("/", os.sep))
    if cale.endswith("/") or not os.path.splitext(rel)[1]:
        tinta = os.path.join(tinta, "index.html")
    return tinta


def main() -> int:
    ap = argparse.ArgumentParser(description="verificare HTML pe output/ construit")
    ap.add_argument("--raport", action="store_true", help="numara, nu pica niciodata")
    arg = ap.parse_args()

    if not os.path.isdir(OUT):
        print("!! output/ lipseste — ruleaza intai `python -m generator.main --render-only`")
        return 1

    pagini = [os.path.join(d, f) for d, _, fs in os.walk(OUT) for f in fs if f.endswith(".html")]
    # Ancorele se rezolva DUPA ce s-au citit toate paginile: un link din pagina A catre
    # `/b/#sectiune` are nevoie de id-urile paginii B, care poate fi parsata mai tarziu.
    id_uri: dict = {}
    de_verificat: list = []      # (pagina_sursa, href)
    probleme = Counter()
    exemple: dict = {}

    def _noteaza(fel: str, detaliu: str) -> None:
        probleme[fel] += 1
        exemple.setdefault(fel, []).append(detaliu)

    total_img = fara_alt = 0
    for p in pagini:
        with open(p, encoding="utf-8", errors="replace") as fh:
            parser = _Pagina()
            try:
                parser.feed(fh.read())
            except Exception as exc:                       # HTML atat de stricat incat rupe parserul
                _noteaza("html_neparsabil", f"{os.path.relpath(p, OUT)}: {exc}")
                continue
        rel = os.path.relpath(p, OUT).replace(os.sep, "/")
        id_uri[rel] = parser.id_uri
        total_img += parser.total_img
        fara_alt += parser.img_fara_alt
        if parser.img_fara_alt:
            _noteaza("img_fara_alt", f"{rel}: {parser.img_fara_alt} img")
        for href in parser.linkuri:
            de_verificat.append((rel, href))
        for src in parser.surse:
            cale = _intern(src)
            if cale and not os.path.exists(_fisier_pentru(cale)):
                _noteaza("activ_lipsa", f"{rel} -> {src}")

    for rel, href in de_verificat:
        cale = _intern(href)
        if not cale:
            continue
        parti = urlsplit(cale)
        if parti.path in ("", None) and parti.fragment:      # ancora in aceeasi pagina
            tinta_rel, frag = rel, parti.fragment
        else:
            fisier = _fisier_pentru(parti.path)
            if not os.path.exists(fisier):
                _noteaza("legatura_moarta", f"{rel} -> {href}")
                continue
            tinta_rel, frag = os.path.relpath(fisier, OUT).replace(os.sep, "/"), parti.fragment
        if frag and frag not in id_uri.get(tinta_rel, set()):
            _noteaza("ancora_moarta", f"{rel} -> {href}")

    print(f"=== html_check — {len(pagini)} pagini, {len(de_verificat)} legaturi, {total_img} imagini ===")
    for fel in ("legatura_moarta", "activ_lipsa", "ancora_moarta", "img_fara_alt", "html_neparsabil"):
        n = probleme[fel]
        marca = "ok  " if not n else "!!  "
        print(f"{marca}{fel:18} {n}")
        for ex in exemple.get(fel, [])[:5]:
            print(f"      {ex}")
        if n > 5:
            print(f"      ... si inca {n - 5}")

    if arg.raport:
        print("\n--raport: nu pic niciodata (mod de calibrare)")
        return 0
    # Pragurile sunt ZERO pe toate: nu sunt alese, sunt starea masurata a lui `main` la
    # 2026-08-06, cand poarta a fost cablata. Un prag pozitiv ar insemna „acceptam N pagini
    # stricate", ceea ce nu vrem sa devina normal fara o decizie explicita.
    rau = sum(probleme.values())
    if rau:
        print(f"\nFAIL: {rau} probleme in HTML-ul construit.")
        return 1
    print("\nOK: legaturi interne, ancore, active si `alt` — toate curate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
