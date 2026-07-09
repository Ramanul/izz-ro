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
import datetime as dt
import os
import random
import re
import sys
import urllib.request

FRESH_MAX_HOURS = 48   # cel mai nou articol de pe live trebuie sa fie mai recent de-atat

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

    print("prospetime:")
    sitemap = get("/sitemap.xml")
    # cel mai nou lastmod de articol (data publicarii) -> deploy-ul chiar publica
    # continut proaspat. Prinde site-ul INGHETAT (deploy sarit), pe care verificarile
    # de format nu-l vad. (5-9 iul 2026: [skip ci] pe commit sarea build-ul Cloudflare.)
    lastmods = re.findall(r"<lastmod>(\d{4}-\d{2}-\d{2})</lastmod>", sitemap)
    newest = max(lastmods) if lastmods else "—"
    fresh = False
    try:
        age_h = (dt.datetime.now(dt.timezone.utc).date() - dt.date.fromisoformat(newest)).days * 24
        fresh = age_h <= FRESH_MAX_HOURS
    except ValueError:
        pass
    check(fresh, "/sitemap.xml",
          f"cel mai nou articol e recent (lastmod {newest}, prag {FRESH_MAX_HOURS}h)")

    print(f"articole (esantion {N_ARTICLES} din sitemap):")
    paths = [re.sub(r"^https?://[^/]+", "", u) for u in re.findall(r"<loc>([^<]+)</loc>", sitemap)]
    arts = [p for p in paths if p.count("/") >= 3 and "/legal/" not in p]
    random.shuffle(arts)
    with_cover = 0
    with_art = 0
    for p in arts[:N_ARTICLES]:
        html = get(p)
        page = p[:60]
        check('class="notice"' not in html, page, "fara disclaimer metodologic pe articol")
        check(html.count('class="sources-box"') == 1, page, "exact un sources-box")
        check(re.search(r'sources-box.*?<a href="http', html, re.S) is not None,
              page, "sursele din box sunt linkuri externe")
        check("btn-source" not in html, page, "fara btn-source")
        # coperta generata: og:image per articol + imaginea chiar exista pe live
        m = re.search(r'property="og:image" content="([^"]+)"', html)
        cover_url = m.group(1) if m else ""
        if "/cover.jpg" in cover_url:
            with_cover += 1
            cpath = re.sub(r"^https?://[^/]+", "", cover_url)
            try:
                req = urllib.request.Request(BASE + cpath, headers=UA)
                with urllib.request.urlopen(req, timeout=30) as r:
                    ok_img = (r.headers.get("Content-Type", "").startswith("image/")
                              and len(r.read()) > 5000)
            except Exception:
                ok_img = False
            check(ok_img, page, "coperta og:image exista si e imagine reala (>5KB)")
        # arta pe site (faza 2): banner fara text -- verifica si ca FISIERUL art.jpg
        # chiar se incarca (nu doar ca tag-ul <img> exista in HTML). Altfel un art.jpg
        # lipsa/404 pe deploy trece neobservat: tag prezent, imagine goala pe ecran.
        am = re.search(r'class="article-art"[^>]*\ssrc="([^"]+)"', html)
        if am:
            apath = re.sub(r"^https?://[^/]+", "", am.group(1))
            try:
                req = urllib.request.Request(BASE + apath, headers=UA)
                with urllib.request.urlopen(req, timeout=30) as r:
                    ok_art = (r.headers.get("Content-Type", "").startswith("image/")
                              and len(r.read()) > 5000)
            except Exception:
                ok_art = False
            if ok_art:
                with_art += 1
    check(with_art >= max(1, N_ARTICLES - 1), "articole",
          f"arta pe site se incarca real pe esantion: {with_art}/{N_ARTICLES} (minim {N_ARTICLES - 1})")
    # cateva articole pot cadea legitim pe og-image static (generate() a esuat izolat),
    # dar majoritatea esantionului TREBUIE sa aiba coperta proprie
    check(with_cover >= max(1, N_ARTICLES - 1), "articole",
          f"coperti generate pe esantion: {with_cover}/{N_ARTICLES} (minim {N_ARTICLES - 1})")

    if fails:
        print(f"\nFAIL — {len(fails)} incalcari pe live:")
        for f in fails:
            print("  -", f)
        return 1
    print("\nOK: site-ul live respecta formatul.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
