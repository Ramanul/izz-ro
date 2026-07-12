#!/usr/bin/env python
"""Auto-gazduirea fonturilor (ruleaza in GitHub Actions -- sandbox-urile n-au net).

De ce: fonts.googleapis.com era o cerere externa BLOCANTA la randare (-620ms pe
mobil, plus IP-urile cititorilor expuse catre Google -- inconsistent cu politica
noastra de confidentialitate). Descarcam woff2-urile o singura data in
static/fonts/ si scriem static/fonts.css cu @font-face (font-display: swap),
pastrand subseturile latin + latin-ext (diacriticele romanesti).

  python tools/fetch_fonts.py
"""
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "static", "fonts")
CSS_URL = ("https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;800"
           "&family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap")
# UA VECHI -> Google serveste TTF-ul COMPLET per fata (fisierele woff2 per-subset
# NU contin fontul intreg si nu pot fi sursa unei subsetari corecte)
UA = {"User-Agent": "Wget/1.20"}


# glifele necesare romanei: Latin de baza + diacritice RO (inclusiv S/T cu virgula,
# U+0218-021B) + ghilimele/punctuatie tipografica. Subsetarea taie ~80% din bytes.
RO_UNICODES = "U+0000-00FF,U+0102-0103,U+0218-021B,U+015E-015F,U+0162-0163,U+2013-2014,U+2018-201E,U+2026,U+2192,U+00B7,U+2022"


def _subset(path: str) -> str:
    """Un singur woff2 per greutate, doar glifele RO (fonttools). Returneaza calea finala."""
    from fontTools.subset import main as ft_subset
    out = path.replace(".woff2", ".ro.woff2")
    ft_subset([path, f"--unicodes={RO_UNICODES}", "--flavor=woff2", f"--output-file={out}",
               "--layout-features=kern,liga", "--no-hinting", "--desubroutinize"])
    os.remove(path)
    return out


def main() -> int:
    req = urllib.request.Request(CSS_URL, headers=UA)
    css = urllib.request.urlopen(req, timeout=30).read().decode()
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):                      # curata setul vechi (ne-subsetat)
        os.remove(os.path.join(OUT, f))
    seen, out_css = set(), []
    for block in re.findall(r"@font-face\s*\{[^}]+\}", css):
        um = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", block)
        if not um:
            continue
        fam = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        wgt = re.search(r"font-weight:\s*(\d+)", block).group(1)
        key = (fam, wgt)
        if key in seen:
            continue
        seen.add(key)
        fn = f"{fam.replace(' ', '')}-{wgt}.woff2"
        p = os.path.join(OUT, fn)
        data = urllib.request.urlopen(urllib.request.Request(um.group(1), headers=UA), timeout=30).read()
        open(p, "wb").write(data)
        p = _subset(p)
        fn = os.path.basename(p)
        out_css.append("@font-face {\n"
                       f"  font-family: '{fam}';\n  font-style: normal;\n"
                       f"  font-weight: {wgt};\n  font-display: swap;\n"
                       f"  src: url(/static/fonts/{fn}) format('woff2');\n}}")
        print(f"  {fn}  {os.path.getsize(p)} bytes (subsetat)")
    open(os.path.join(ROOT, "static", "fonts.css"), "w").write("\n".join(out_css) + "\n")
    print(f">> fonts: {len(seen)} fete subsetate RO, fonts.css scris")
    return 0 if seen else 1


if __name__ == "__main__":
    sys.exit(main())
