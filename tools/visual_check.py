#!/usr/bin/env python
"""Verificare VIZUALA pe site-ul LIVE cu browser real (Playwright/Chromium)."""
import os
import sys
from playwright.sync_api import sync_playwright

BASE = os.getenv("BASE_URL", "https://izz.ro").rstrip("/")
SHOT_DIR = os.getenv("SHOT_DIR", "shots")
INK = "rgb(21, 23, 28)"
fails: list = []
inflight: set = set()


def check(cond: bool, rule: str) -> None:
    print(f"  {'ok ' if cond else 'FAIL'} {rule}")
    if not cond:
        fails.append(rule)


def _abs(href: str) -> str:
    if href.startswith("http"):
        return href
    return BASE + href


def _track(pg) -> None:
    pg.on("request", lambda r: inflight.add(r.url))
    pg.on("requestfinished", lambda r: inflight.discard(r.url))
    pg.on("requestfailed", lambda r: inflight.discard(r.url))


def _goto(pg, url: str, label: str, wait: str = "load") -> None:
    try:
        pg.goto(url, wait_until=wait)
    except Exception as exc:
        print(f"  FAIL navigare {label} <{url}>: {type(exc).__name__}: {exc}")
        try:
            pg.screenshot(path=f"{SHOT_DIR}/FAIL-{label}.png")
        except Exception:
            pass
        raise


def check_map(pg, mobile: bool = False) -> None:
    pg.wait_for_selector("#map canvas.map-canvas", timeout=15000)
    pg.wait_for_selector("#news-list .news-item", timeout=15000)

    canvas_count = pg.locator("#map canvas.map-canvas").count()
    news_items = pg.locator("#news-list .news-item").count()
    map_error = pg.locator("#map .error").count()
    list_error = pg.locator("#news-list .error").count()
    metrics = pg.evaluate("""() => {
        const c = document.querySelector('#map canvas.map-canvas');
        const host = document.querySelector('#map');
        return {
          canvasCount: document.querySelectorAll('#map canvas.map-canvas').length,
          width: c ? c.width : 0,
          height: c ? c.height : 0,
          cssWidth: c ? c.clientWidth : 0,
          cssHeight: c ? c.clientHeight : 0,
          hostHeight: host ? host.getBoundingClientRect().height : 0
        };
    }""")

    check(canvas_count == 1, f"harta are exact un canvas (gasite: {canvas_count})")
    check(metrics["width"] > 0 and metrics["height"] > 0, f"canvas are backing store valid ({metrics['width']}x{metrics['height']})")
    check(metrics["cssWidth"] > 0 and metrics["cssHeight"] > 0, f"canvas are dimensiuni CSS valide ({metrics['cssWidth']}x{metrics['cssHeight']})")
    check(news_items > 0, f"harta afiseaza articole localizate (gasite: {news_items})")
    check(map_error == 0, "harta nu afiseaza eroare de incarcare a datasetului")
    check(list_error == 0, "lista hartii nu afiseaza eroare de dataset")
    marker_dom = pg.locator("#map .count-bubble, #map .count-label").count()
    check(marker_dom == 0, f"harta Canvas nu are markere DOM duplicate (gasite: {marker_dom})")

    if mobile:
        nested_scrollable = pg.evaluate("""() => {
            const e=document.querySelector('#news-list');
            return !!e && e.scrollHeight > e.clientHeight + 1;
        }""")
        check(not nested_scrollable, "[mobil] lista de stiri nu creeaza un al doilea scroll vertical")
        before = pg.evaluate("() => ({h: document.documentElement.scrollHeight, w: document.documentElement.scrollWidth})")
        for _ in range(5):
            pg.mouse.wheel(0, 900)
            pg.wait_for_timeout(100)
            pg.mouse.wheel(0, -900)
            pg.wait_for_timeout(100)
        after = pg.evaluate("() => ({h: document.documentElement.scrollHeight, w: document.documentElement.scrollWidth})")
        check(after["w"] <= 390, f"[mobil] scrollul nu produce bara/overflow orizontal ({after['w']}px)")
        check(abs(after["h"] - before["h"]) <= 2, f"[mobil] inaltimea paginii ramane stabila dupa scroll ({before['h']} -> {after['h']})")
        canvas_after = pg.locator("#map canvas.map-canvas").count()
        check(canvas_after == 1, f"[mobil] scrollul nu multiplica canvas-ul ({canvas_after} dupa scroll)")
        post = pg.evaluate("""() => {
            const c=document.querySelector('#map canvas.map-canvas');
            const r=c ? c.getBoundingClientRect() : null;
            return r ? {w:r.width,h:r.height} : null;
        }""")
        check(bool(post and post["w"] > 0 and post["h"] > 0), "[mobil] canvasul ramane randabil dupa scroll sus/jos")


def main() -> int:
    os.makedirs(SHOT_DIR, exist_ok=True)
    print(f"=== visual check pe {BASE} (browser real) ===")
    csp_errors: list = []
    failed_local: list = []
    launch = {"args": ["--no-sandbox", "--disable-dev-shm-usage"]}
    if os.getenv("PW_CHROME"):
        launch["executable_path"] = os.environ["PW_CHROME"]

    with sync_playwright() as pw:
        br = pw.chromium.launch(**launch)
        pg = br.new_page(viewport={"width": 1280, "height": 900})
        pg.on("console", lambda m: csp_errors.append(m.text) if m.type == "error" and "Content Security Policy" in m.text else None)
        pg.on("requestfailed", lambda r: failed_local.append(r.url) if BASE in r.url and "/cdn-cgi/" not in r.url else None)
        _track(pg)
        _goto(pg, BASE + "/", "home")
        pg.screenshot(path=f"{SHOT_DIR}/home.png")
        if pg.query_selector("#challenge-running, #cf-challenge-running") or "security verification" in (pg.title() or "").lower():
            fails.append(f"Cloudflare bot challenge blocheaza verificarea pe {BASE}")
            br.close()
            return 1

        _goto(pg, BASE + "/static/harta-stiri/", "harta-stiri", wait="domcontentloaded")
        check_map(pg)
        pg.screenshot(path=f"{SHOT_DIR}/harta-stiri.png", full_page=True)

        _goto(pg, BASE + "/", "home-after-map", wait="domcontentloaded")
        cat = pg.get_attribute(".nav a", "href") or "/"
        _goto(pg, _abs(cat), "categorie", wait="domcontentloaded")
        media = pg.query_selector(".card-media")
        if media:
            bg = pg.eval_on_selector(".card-media", "el => getComputedStyle(el).backgroundColor")
            check(bg != INK, f".card-media background NU e negru pe live (masurat: {bg})")
        else:
            check(False, ".card-media exista pe pagina de categorie")
        pg.screenshot(path=f"{SHOT_DIR}/categorie.png")

        art = pg.get_attribute(".card-title a", "href")
        if art:
            _goto(pg, _abs(art), "articol")
            el = pg.query_selector(".article-art")
            if el:
                try:
                    pg.wait_for_function("() => { const el = document.querySelector('.article-art'); return !el || el.complete; }", timeout=15000)
                except Exception:
                    pass
                nat = pg.eval_on_selector(".article-art", "el => el.naturalWidth || 0")
                check(nat > 0, f"arta articolului se incarca real (naturalWidth={nat})")
            else:
                check(False, ".article-art exista pe pagina de articol")
            pg.screenshot(path=f"{SHOT_DIR}/articol.png")

        mob = br.new_page(viewport={"width": 390, "height": 844}, user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile Safari/604.1")
        _track(mob)
        _goto(mob, BASE + "/static/harta-stiri/", "mobil-harta-stiri", wait="domcontentloaded")
        check_map(mob, mobile=True)
        mob.screenshot(path=f"{SHOT_DIR}/mobil-harta-stiri.png", full_page=True)

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
