#!/usr/bin/env python
"""Smoke-test pe site-ul LIVE — verifica regulile de format ale ownerului dupa deploy.

  BASE_URL=https://izz.ro python tools/smoke_live.py    # 0 = ok, 1 = incalcari

Ruleaza in GitHub Actions (runnerii au acces la internet; sandbox-urile de dev nu).
La exit!=0 ownerul e anuntat automat de GitHub. Verifica LIVE, nu codul — prinde
si regresiile de deploy/cache, nu doar pe cele de cod.

Reguli verificate (CLAUDE.md sectiunea 7, decizia ownerului):
  home:    descriptorul "Raportul stirilor principale" prezent; carduri cu linia
           Sursa:/Surse: cu nume-LINK extern; fara "Citeste"; fara "Provenienta"
  articol: fara disclaimerul metodologic (traieste doar in /legal/method);
           exact un sources-box cu linkuri externe; fara btn-source
"""
import os
import random
import re
import sys
import urllib.request

BASE = os.getenv("BASE_URL", "https://izz.ro").rstrip("/")
N_ARTICLES = 5
UA = {"User-Agent": "izz-smoke/1.0 (+https://izz.ro)"}

fails: list = []


def get(path: str) -> str:
    req = urllib.request.Request(BASE + path, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def check(cond: bool, page: str, rule: str) -> None:
    print(f"  {'ok ' if cond else 'FAIL'} {rule}")
    if not cond:
        fails.append(f"{page}: {rule}")


def main() -> int:
    print(f"=== smoke live pe {BASE} ===")

    print("home:")
    home = get("/")
    cards = re.findall(r'<article class="card.*?</article>', home, re.S)
    check("Raportul știrilor principale" in home, "/", "descriptorul brand prezent")
    check(len(cards) >= 10, "/", f"minim 10 carduri (gasite: {len(cards)})")
    check("Proveniență" not in home, "/", "eticheta 'Proveniență' nu exista (doar Sursă/Surse)")
    check(all('class="sources-inline"' in c for c in cards), "/", "fiecare card are linia de surse")
    check(all(re.search(r'sources-inline[^§]*?<a href="http', c, re.S) for c in cards),
          "/", "numele surselor sunt linkuri externe pe fiecare card")
    check(">Citește<" not in home and "read-more" not in home, "/", "fara CTA 'Citește' pe carduri")

    print(f"articole (esantion {N_ARTICLES} din sitemap):")
    sitemap = get("/sitemap.xml")
    paths = [re.sub(r"^https?://[^/]+", "", u) for u in re.findall(r"<loc>([^<]+)</loc>", sitemap)]
    arts = [p for p in paths if p.count("/") >= 3 and "/legal/" not in p]
    random.shuffle(arts)
    for p in arts[:N_ARTICLES]:
        html = get(p)
        page = p[:60]
        check('class="notice"' not in html, page, "fara disclaimer metodologic pe articol")
        check(html.count('class="sources-box"') == 1, page, "exact un sources-box")
        check(re.search(r'sources-box.*?<a href="http', html, re.S) is not None,
              page, "sursele din box sunt linkuri externe")
        check("btn-source" not in html, page, "fara btn-source")

    if fails:
        print(f"\nFAIL — {len(fails)} incalcari pe live:")
        for f in fails:
            print("  -", f)
        return 1
    print("\nOK: site-ul live respecta formatul.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
