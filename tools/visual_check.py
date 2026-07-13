#!/usr/bin/env python
"""Verificare VIZUALA pe site-ul LIVE cu browser real (Playwright/Chromium).

Conduce paginile ca un UTILIZATOR si masoara pixeli / stiluri calculate + erori de
consola/CSP + request-uri esuate -- complementul "as a user" al smoke_live.py (care
verifica doar HTML-ul brut via urllib). Ruleaza in GitHub Actions dupa deploy
(runnerii au internet; sandbox-urile de dev nu). La exit!=0 owner-ul e anuntat
automat de GitHub. Screenshot-urile se scriu in SHOT_DIR (urcate ca artifact in CI).

  BASE_URL=https://izz.ro python tools/visual_check.py
  PW_CHROME=/path/to/chrome BASE_URL=http://127.0.0.1:8000 python tools/visual_check.py  # test local

Verifica (CLAUDE.md §16 -- rol de utilizator, masurat nu presupus):
  - placeholder-ul .card-media NU e fundal inchis (regresia de flicker negru);
  - imaginea/arta articolului chiar se RANDEAZA (naturalWidth>0, nu pictograma goala);
  - zero erori CSP in consola; zero request-uri interne esuate (asset lipsa/404).
"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.getenv("BASE_URL", "https://izz.ro").rstrip("/")
SHOT_DIR = os.getenv("SHOT_DIR", "shots")
INK = "rgb(21, 23, 28)"   # var(--ink) -- fundalul negru care dadea flicker
fails: list = []


def check(cond: bool, rule: str) -> None:
    print(f"  {'ok ' if cond else 'FAIL'} {rule}")
    if not cond:
        fails.append(rule)


def _abs(href: str) -> str:
    if href.startswith("http"):
        return href
    return BASE + href


def main() -> int:
    os.makedirs(SHOT_DIR, exist_ok=True)
    print(f"=== visual check pe {BASE} (browser real) ===")
    csp_errors: list = []
    failed_local: list = []
    launch = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    if os.getenv("PW_CHROME"):                      # override pt. test local in sandbox
        launch["executable_path"] = os.environ["PW_CHROME"]

    with sync_playwright() as pw:
        br = pw.chromium.launch(**launch)
        pg = br.new_page(viewport={"width": 1280, "height": 900})
        pg.on("console", lambda m: csp_errors.append(m.text)
              if m.type == "error" and "Content Security Policy" in m.text else None)
        pg.on("requestfailed", lambda r: failed_local.append(r.url)
              if BASE in r.url else None)

        # --- home ---
        pg.goto(BASE + "/", wait_until="networkidle")
        pg.screenshot(path=f"{SHOT_DIR}/home.png")

        # --- pagina de categorie: placeholder-ul cardurilor, masurat real ---
        cat = pg.get_attribute(".nav a", "href") or "/"
        pg.goto(_abs(cat), wait_until="domcontentloaded")
        media = pg.query_selector(".card-media")
        if media:
            bg = pg.eval_on_selector(".card-media", "el => getComputedStyle(el).backgroundColor")
            check(bg != INK, f".card-media background NU e negru pe live (masurat: {bg})")
        else:
            check(False, ".card-media exista pe pagina de categorie")
        pg.screenshot(path=f"{SHOT_DIR}/categorie.png")

        # --- un articol: arta chiar se randeaza (nu pictograma goala / 404) ---
        art = pg.get_attribute(".card-title a", "href")
        if art:
            pg.goto(_abs(art), wait_until="networkidle")
            el = pg.query_selector(".article-art")
            if el:
                nat = pg.eval_on_selector(".article-art",
                                          "el => el.naturalWidth || 0")
                check(nat > 0, f"arta articolului se incarca real (naturalWidth={nat})")
            else:
                check(False, ".article-art exista pe pagina de articol")
            pg.screenshot(path=f"{SHOT_DIR}/articol.png")

        br.close()

    check(not csp_errors, f"zero erori CSP in consola ({len(csp_errors)})")
    check(not failed_local, f"zero request-uri interne esuate ({failed_local[:3] or 'niciunul'})")

    if fails:
        print(f"\nFAIL — {len(fails)} probleme vizuale pe live:")
        for f in fails:
            print("  -", f)
        return 1
    print("\nOK: site-ul live arata corect (verificat cu browser real).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
