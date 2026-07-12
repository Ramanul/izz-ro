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
           "&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap")
# UA modern -> Google serveste woff2 + unicode-range per subset
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"}
SUBSETS = ("latin", "latin-ext")   # romana are nevoie de latin-ext (ă î ș ț)


def main() -> int:
    req = urllib.request.Request(CSS_URL, headers=UA)
    css = urllib.request.urlopen(req, timeout=30).read().decode()
    os.makedirs(OUT, exist_ok=True)
    out_css, kept, n = [], 0, 0
    # blocuri: /* subset */ @font-face { ... url(...) ... }
    for m in re.finditer(r"/\*\s*([a-z-]+)\s*\*/\s*(@font-face\s*\{[^}]+\})", css):
        subset, block = m.group(1), m.group(2)
        n += 1
        if subset not in SUBSETS:
            continue
        um = re.search(r"url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)", block)
        if not um:
            continue
        url = um.group(1)
        fam = re.search(r"font-family:\s*'([^']+)'", block).group(1).replace(" ", "")
        wgt = re.search(r"font-weight:\s*(\d+)", block).group(1)
        fn = f"{fam}-{wgt}-{subset}.woff2"
        data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
        open(os.path.join(OUT, fn), "wb").write(data)
        out_css.append(f"/* {subset} */\n" + block.replace(url, f"/static/fonts/{fn}"))
        kept += 1
        print(f"  {fn}  {len(data)} bytes")
    open(os.path.join(ROOT, "static", "fonts.css"), "w").write("\n".join(out_css) + "\n")
    print(f">> fonts: {kept}/{n} blocuri pastrate ({', '.join(SUBSETS)}), fonts.css scris")
    return 0 if kept else 1


if __name__ == "__main__":
    sys.exit(main())
