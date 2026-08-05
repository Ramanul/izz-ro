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
inflight: set = set()     # requesturi pornite si neterminate -- dovada la esec de navigare


def check(cond: bool, rule: str) -> None:
    print(f"  {'ok ' if cond else 'FAIL'} {rule}")
    if not cond:
        fails.append(rule)


def _abs(href: str) -> str:
    if href.startswith("http"):
        return href
    return BASE + href


def _track(pg) -> None:
    """Urmareste requesturile in zbor, ca un esec de navigare sa spuna CE l-a tinut."""
    pg.on("request", lambda r: inflight.add(r.url))
    pg.on("requestfinished", lambda r: inflight.discard(r.url))
    pg.on("requestfailed", lambda r: inflight.discard(r.url))


def _goto(pg, url: str, label: str, wait: str = "load") -> None:
    """Navigheaza si, la esec, lasa DOVEZI in SHOT_DIR in loc sa moara mut.

    NU folosim wait_until="networkidle". Playwright insusi il descurajeaza, iar pe izz.ro
    nu se atinge niciodata din runnerul de CI: jobul a fost rosu 77 de rulari consecutive
    (17 iul - 5 aug 2026) cu exact acelasi `Page.goto: Timeout 30000ms exceeded`, fara
    niciun commit de cod in fereastra. Cloudflare Speed Brain e activ pe site
    (`Speculation-Rules: "/cdn-cgi/speculation"`), deci edge-ul mai lucreaza si dupa `load`.
    `load` se termina la evenimentul ferestrei, deci nu depinde de ce prefetch-eaza edge-ul.

    Vechea versiune murea la primul goto INAINTE de orice screenshot, asa ca artifactul a
    fost gol la fiecare din cele 77 de esecuri -- 19 zile fara nicio dovada vizuala.
    """
    try:
        pg.goto(url, wait_until=wait)
    except Exception as exc:
        print(f"  FAIL navigare {label} <{url}>: {type(exc).__name__}: {exc}")
        print(f"  requesturi neterminate in acel moment ({len(inflight)}):")
        for u in sorted(inflight)[:20]:
            print("    -", u)
        try:
            pg.screenshot(path=f"{SHOT_DIR}/FAIL-{label}.png")
            print(f"  screenshot de esec: {SHOT_DIR}/FAIL-{label}.png")
        except Exception as shot_exc:                       # pagina poate fi inutilizabila
            print(f"  (screenshot imposibil: {shot_exc})")
        raise


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
        # ignoram /cdn-cgi/* -- endpointuri injectate de Cloudflare (RUM/analytics),
        # nu activele noastre; beacon-ul rum poate fi abandonat inofensiv la navigare
        pg.on("requestfailed", lambda r: failed_local.append(r.url)
              if BASE in r.url and "/cdn-cgi/" not in r.url else None)
        _track(pg)

        # --- home ---
        _goto(pg, BASE + "/", "home")
        pg.screenshot(path=f"{SHOT_DIR}/home.png")

        # --- pagina de categorie: placeholder-ul cardurilor, masurat real ---
        cat = pg.get_attribute(".nav a", "href") or "/"
        _goto(pg, _abs(cat), "categorie", wait="domcontentloaded")
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
            _goto(pg, _abs(art), "articol")
            el = pg.query_selector(".article-art")
            if el:
                # `networkidle` garanta implicit ca imaginea apucase sa se descarce; acum
                # o asteptam explicit. Daca nu se completeaza, naturalWidth de mai jos
                # raporteaza FAIL corect -- deci timeoutul aici nu trebuie sa opreasca runul.
                try:
                    pg.wait_for_function(
                        "() => { const el = document.querySelector('.article-art');"
                        " return !el || el.complete; }", timeout=15000)
                except Exception as exc:
                    print(f"  (arta nu s-a completat in 15s: {type(exc).__name__})")
                nat = pg.eval_on_selector(".article-art",
                                          "el => el.naturalWidth || 0")
                check(nat > 0, f"arta articolului se incarca real (naturalWidth={nat})")
            else:
                check(False, ".article-art exista pe pagina de articol")
            pg.screenshot(path=f"{SHOT_DIR}/articol.png")

        # --- responsive (raport testare 2026-07-16): viewport de telefon, masurat real.
        #     Regresia clasica e overflow-ul orizontal (pagina "se misca" lateral) --
        #     scrollWidth trebuie sa incapa in viewport pe home + articol.
        mob = br.new_page(viewport={"width": 390, "height": 844},
                          user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                                     "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile Safari/604.1")
        _track(mob)
        for label, url in [("home", BASE + "/")] + ([("articol", _abs(art))] if art else []):
            _goto(mob, url, f"mobil-{label}")
            over = mob.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check(over <= 0, f"[mobil 390px] fara overflow orizontal pe {label} (depasire: {over}px)")
            mob.screenshot(path=f"{SHOT_DIR}/mobil-{label}.png")
        mob.close()

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
