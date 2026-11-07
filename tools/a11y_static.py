#!/usr/bin/env python
"""Accesibilitate statica pe HTML-ul construit din output/ — fara browser, fara retea.

  python tools/a11y_static.py              # raport; exit 1 doar la incalcarile „tari"
  python tools/a11y_static.py --raport     # doar numara (calibrare), nu pica niciodata

DE CE EXISTA. `tools/audit.sh` ar da scorul axe/Lighthouse, dar cere Chromium si doua
pachete npm; in sandboxul asta nu exista nici browser, nici acces la retea, deci scorul
rămâne nemăsurat (vezi specs/masuratori-frontend.md, „ce nu am putut masura"). Regulile
de mai jos sunt cele care se pot decide din DOM-ul servit: nume accesibil, ordinea
titlurilor, landmark-uri, `alt`, etichete de formular, `target=_blank` fara `noopener`.
Ce NU poate spune scriptul: contrastul real (depinde de fonturi si antialiasing), ordinea
de tabulare, comportamentul la zoom 400% — acelea cer browser.

Praguri. Incalcarile „tari" (nume accesibil lipsa, `<h1>` lipsa/dublu, input fara
eticheta, `tabindex` pozitiv) fac exit 1. Cele „moi" (saritura de nivel in titluri,
`target=_blank` fara rel) se numara si se listeaza, dar nu blocheaza: sunt semnalari de
curățat, nu regresii.
"""
from __future__ import annotations

import argparse
import collections
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")

VID = {"img", "br", "hr", "input", "meta", "link", "source", "area", "base", "col", "embed", "wbr"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class Pagina(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.titluri: list[tuple[int, str]] = []
        self._in_heading = 0
        self._heading_text: list[str] = []
        self._heading_tag = ""
        self.linkuri: list[dict] = []
        self._link_stack: list[dict] = []
        self.butoane: list[dict] = []
        self._btn_text: list[str] = []
        self._in_btn = 0
        self.imagini_fara_alt = 0
        self.imagini_fara_dimensiuni = 0
        self.imagini_total = 0
        self.inputuri_fara_eticheta = 0
        self.iduri: collections.Counter = collections.Counter()
        self.iframe_fara_titlu = 0
        self.target_blank_fara_rel = 0
        self.tabindex_pozitiv = 0
        self.are_main = False
        self.are_skip = False
        self.nav_fara_eticheta = 0
        self._nav_depth = 0
        self.etichete = set()
        self._in_label = 0        # <label> care INVELESTE inputul = eticheta implicita
        self.selectors = 0

    # --- colectare -------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = (a.get("lang") or "").strip().lower()
        if tag == "main" or a.get("role") == "main":
            self.are_main = True
        if "id" in a and a["id"]:
            self.iduri[a["id"]] += 1
        if tag == "nav":
            self._nav_depth += 1
            if not (a.get("aria-label") or a.get("aria-labelledby")):
                self.nav_fara_eticheta += 1
        if tag == "label":
            self._in_label += 1
            if a.get("for"):
                self.etichete.add(a["for"])
        if tag in HEADINGS:
            self._in_heading = 1
            self._heading_tag = tag
            self._heading_text = []
        if tag == "a":
            link = {"href": a.get("href", ""), "text": "", "label": a.get("aria-label") or
                    (a.get("title") or ""), "img_alt": "", "target": a.get("target", ""),
                    "rel": a.get("rel", ""),
                    # linkurile din jurul imaginii de card sunt duplicate intentionat ale
                    # titlului si sunt ascunse de cititoarele de ecran — nu le numaram
                    "ascuns": a.get("aria-hidden") == "true" or a.get("tabindex") == "-1"}
            self._link_stack.append(link)
            if tag and a.get("href", "").startswith("#") and not self.are_skip:
                if "skip" in (a.get("class") or "") or "sari" in (a.get("class") or ""):
                    self.are_skip = True
        if tag == "img":
            self.imagini_total += 1
            if "alt" not in a:            # alt="" e valid: imagine decorativa
                self.imagini_fara_alt += 1
            if not (a.get("width") and a.get("height")):
                self.imagini_fara_dimensiuni += 1
            if self._link_stack:
                self._link_stack[-1]["img_alt"] = self._link_stack[-1]["img_alt"] or a.get("alt", "")
        if tag == "input":
            tip = (a.get("type") or "text").lower()
            if tip not in {"hidden", "submit", "button", "reset", "image"}:
                if not (a.get("aria-label") or a.get("aria-labelledby")
                        or a.get("id") in self.etichete or self._in_label):
                    self.inputuri_fara_eticheta += 1
        if tag == "iframe" and not a.get("title"):
            self.iframe_fara_titlu += 1
        if tag == "button":
            self._in_btn += 1
            self._btn_text = []
            self.butoane.append({"label": a.get("aria-label") or "", "text": ""})
        if tag == "a" and a.get("target") == "_blank" and "noopener" not in (a.get("rel") or ""):
            self.target_blank_fara_rel += 1
        if a.get("tabindex", "").lstrip("-").isdigit() and int(a["tabindex"]) > 0:
            self.tabindex_pozitiv += 1
        self.selectors += 1

    def handle_endtag(self, tag):
        if tag in HEADINGS and self._in_heading:
            text = " ".join("".join(self._heading_text).split())
            nivel = int(self._heading_tag[1])
            self.titluri.append((nivel, text))
            self._in_heading = 0
        if tag == "a" and self._link_stack:
            self.linkuri.append(self._link_stack.pop())
        if tag == "button":
            self._in_btn = max(0, self._in_btn - 1)
            if self.butoane:
                self.butoane[-1]["text"] = " ".join("".join(self._btn_text).split())
        if tag == "nav":
            self._nav_depth = max(0, self._nav_depth - 1)
        if tag == "label":
            self._in_label = max(0, self._in_label - 1)

    def handle_data(self, data):
        if self._in_heading:
            self._heading_text.append(data)
        if self._in_btn:
            self._btn_text.append(data)
        for link in self._link_stack:
            link["text"] += data


def _fara_nume(link: dict) -> bool:
    """Un link fara text vizibil are totusi nume daca are aria-label sau un <img alt>."""
    return (link["text"].strip() == "" and not link["label"].strip()
            and not link["img_alt"].strip())


def verifica(cale: str) -> dict:
    with open(cale, encoding="utf-8", errors="replace") as fh:
        html = fh.read()
    p = Pagina()
    p.feed(html)
    p.close()

    probleme_tari = []
    slabe = []

    if p.lang != "ro":
        probleme_tari.append(f"lang={p.lang!r}")
    h1 = [t for n, t in p.titluri if n == 1]
    if len(h1) != 1:
        probleme_tari.append(f"{len(h1)} titluri h1")
    if p.imagini_fara_alt:
        probleme_tari.append(f"{p.imagini_fara_alt} img fara alt")
    if p.inputuri_fara_eticheta:
        probleme_tari.append(f"{p.inputuri_fara_eticheta} input fara eticheta")
    if p.tabindex_pozitiv:
        probleme_tari.append(f"{p.tabindex_pozitiv} tabindex pozitiv")
    linkuri_fara_nume = [l for l in p.linkuri if not l["ascuns"] and _fara_nume(l)]
    if linkuri_fara_nume:
        probleme_tari.append(f"{len(linkuri_fara_nume)} linkuri fara nume accesibil "
                             f"(ex. {linkuri_fara_nume[0]['href'][:40]!r})")
    butoane_fara_nume = [b for b in p.butoane if not b["text"] and not b["label"]]
    if butoane_fara_nume:
        probleme_tari.append(f"{len(butoane_fara_nume)} butoane fara nume")
    duble = [k for k, v in p.iduri.items() if v > 1]
    if duble:
        probleme_tari.append(f"{len(duble)} id-uri duplicate (ex. {duble[0]!r})")

    if not p.are_main:
        slabe.append("lipseste <main>")
    nivele = [n for n, _ in p.titluri]
    for a, b in zip(nivele, nivele[1:]):
        if b - a > 1:
            slabe.append(f"saritura de nivel h{a}->h{b}")
            break
    if p.imagini_fara_dimensiuni:
        slabe.append(f"{p.imagini_fara_dimensiuni}/{p.imagini_total} img fara width+height")
    if p.target_blank_fara_rel:
        slabe.append(f"{p.target_blank_fara_rel} target=_blank fara rel=noopener")
    if p.nav_fara_eticheta:
        slabe.append(f"{p.nav_fara_eticheta} nav fara aria-label")

    return {"tari": probleme_tari, "slabe": slabe,
            "meta": {"h1": len(h1), "img": p.imagini_total, "linkuri": len(p.linkuri),
                     "butoane": len(p.butoane)}}


def pagini(radacina: str = OUT, limita: int = 0):
    fisiere = []
    for root, _d, files in os.walk(radacina):
        for f in files:
            if not f.endswith(".html"):
                continue
            cale = os.path.join(root, f)
            if os.path.getsize(cale) < 500:      # redirectari, 404-uri goale
                continue
            fisiere.append(cale)
    fisiere.sort()
    return fisiere[:limita] if limita else fisiere


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raport", action="store_true", help="doar numara, nu pica")
    ap.add_argument("--limita", type=int, default=0)
    ap.add_argument("--exemple", type=int, default=6)
    args = ap.parse_args()

    if not os.path.isdir(OUT):
        print("output/ lipseste — ruleaza intai build-ul", file=sys.stderr)
        return 2

    fisiere = pagini(limita=args.limita)
    tari: collections.Counter = collections.Counter()
    slabe: collections.Counter = collections.Counter()
    exemple_tari: list[str] = []
    pagini_cu_tari = 0
    h1_total = 0
    img_total = 0

    for cale in fisiere:
        r = verifica(cale)
        h1_total += r["meta"]["h1"]
        img_total += r["meta"]["img"]
        if r["tari"]:
            pagini_cu_tari += 1
            if len(exemple_tari) < args.exemple:
                rel = os.path.relpath(cale, OUT)
                exemple_tari.append(f"{rel}: {', '.join(r['tari'])}")
        for t in r["tari"]:
            tari[re.sub(r"\(ex\. .*", "", t).strip()] += 1
        for s in r["slabe"]:
            slabe[s] += 1

    print(f"=== a11y_static — {len(fisiere)} pagini, {img_total} imagini, {h1_total} h1")
    print(f"    pagini cu incalcari tari: {pagini_cu_tari}")
    for tip, n in tari.most_common():
        print(f"    TARE  {tip} ×{n}")
    for tip, n in slabe.most_common(12):
        print(f"    moale {tip} ×{n}")
    for ex in exemple_tari:
        print(f"      · {ex}")

    if args.raport:
        return 0
    if pagini_cu_tari:
        print(f"\nFAIL: {pagini_cu_tari} pagini cu incalcari tari de accesibilitate")
        return 1
    print("\nOK: nume accesibile, un singur h1, alt-uri, etichete si id-uri — curate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
