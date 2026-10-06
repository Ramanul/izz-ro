#!/usr/bin/env python
"""Verificare vizuala live + regresie SVG/scroll/redraw.

Adaptat la substratul SVG/DOM (2026-10-04, F1 din notes/harta-revolutie-proposal-2026-10-04.md):
harta nu mai are canvas, deci "imaginea randata" se citeste din DOM (semnatura structurii si a
stilurilor calculate), nu din pixeli. Ce acoperea verificarea inainte si se pastreaza:
  * o SINGURA suprafata de desenare, refolosita la scroll (dedublarea vizuala, e3832692);
  * scrollul nu modifica vederea (semnatura identica inainte/dupa);
  * fiecare pas de resize lasa o scena valida, cu dimensiuni nenule;
  * pe mobil nu apare overflow orizontal.
  * parcursul vizitatorului real: homepage -> articol -> sursa externa, desktop + mobil
    (portat din #443, rebazat pe substratul SVG post-#445; selectorii verificati pe
    template-urile actuale: lead-feature h2 a / .body / .official-note / .sources-box).

Ce NU mai acopera (si de ce e ok): pixelii exacti ai umpluturilor. In lumea SVG ei sunt dati
de CSS-ul declarat, iar garda de culoare e `tools/harta_contrast.py` -- determinist, fara
browser. Aici ramane intrebarea "se randeaza ceva si ramane stabil?", nu "ce nuanta are pixelul".
"""
import os
import re
import sys
from urllib.parse import urljoin, urlsplit, urlunsplit

from playwright.sync_api import sync_playwright

BASE = os.getenv("BASE_URL", "https://izz.ro").rstrip("/")
SHOT_DIR = os.getenv("SHOT_DIR", "shots")
fails = []


def check(c, r):
    print(f"  {'ok ' if c else 'FAIL'} {r}")
    if not c:
        fails.append(r)


def goto(p, u, label, wait="load"):
    try:
        return p.goto(u, wait_until=wait)
    except Exception as e:
        print(f"  FAIL navigare {label}: {e}")
        raise


def _is_site_host(host, base_host):
    host = (host or "").lower()
    base_host = (base_host or "").lower()
    return bool(host) and (
        host == base_host or host == "izz.ro" or host.endswith(".izz.ro")
    )


def _rewrite_site_origin(route, base_parts):
    """Trimite linkurile canonice izz.ro prin originea de test (de ex. workers.dev).

    Originea workers.dev evita challenge-ul WAF, dar homepage-ul poate avea linkuri
    absolute spre izz.ro. Rescriem doar hostname-urile proprii; sursele externe raman intacte.
    """
    requested = urlsplit(route.request.url)
    if (_is_site_host(requested.hostname, base_parts.hostname)
            and requested.hostname != base_parts.hostname):
        target = urlunsplit((
            base_parts.scheme, base_parts.netloc, requested.path, requested.query, ""
        ))
        route.continue_(url=target)
    else:
        route.continue_()


def _check_mobile_overflow(page, label):
    overflow = page.evaluate(
        "Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) "
        "- document.documentElement.clientWidth"
    )
    check(overflow <= 0, f"{label}: fara overflow orizontal ({overflow}px)")


def check_visitor_journey(browser, mobile=False):
    """Deschide o stire din homepage si verifica pagina, provenienta si layoutul mobil."""
    label = "mobil" if mobile else "desktop"
    viewport = {"width": 390, "height": 844} if mobile else {"width": 1280, "height": 900}
    context = browser.new_context(
        viewport=viewport, is_mobile=mobile, has_touch=mobile, service_workers="block"
    )
    page = context.new_page()
    base_parts = urlsplit(BASE)
    try:
        try:
            home_response = goto(page, f"{BASE}/", f"homepage {label}")
        except Exception as exc:
            check(False, f"{label}: homepage se deschide ({exc})")
            return
        status = home_response.status if home_response else "fara raspuns"
        check(home_response is not None and home_response.ok,
              f"{label}: homepage raspunde cu succes (HTTP {status})")
        if home_response is None or not home_response.ok:
            return

        story_selector = "main article h2 a[href]"
        try:
            page.wait_for_selector(story_selector, state="visible", timeout=15000)
        except Exception as exc:
            check(False, f"{label}: homepage expune un link de articol ({exc})")
            return

        story_links = page.locator(story_selector)
        story_link = story_links.first
        story_title = re.sub(r"\s+", " ", story_link.inner_text()).strip()
        story_href = story_link.get_attribute("href") or ""
        story_url = urljoin(f"{BASE}/", story_href)
        story_parts = urlsplit(story_url)
        story_is_internal = _is_site_host(story_parts.hostname, base_parts.hostname)
        story_segments = [part for part in story_parts.path.split("/") if part]
        check(bool(story_title), f"{label}: primul articol are titlu")
        check(story_is_internal and len(story_segments) >= 2,
              f"{label}: primul articol duce la o ruta interna ({story_url})")
        if not story_title or not story_is_internal or len(story_segments) < 2:
            return

        if mobile:
            _check_mobile_overflow(page, "homepage mobil")
            page.screenshot(path=f"{SHOT_DIR}/visitor-mobile-home.png")

        # Pe originea de test evitam redirectul catre domeniul protejat de WAF, pastrand
        # ruta exacta aleasa din homepage si toate cererile catre assete pe aceeasi origine.
        page.route("**/*", lambda route: _rewrite_site_origin(route, base_parts))
        try:
            with page.expect_navigation(wait_until="domcontentloaded",
                                        timeout=15000) as nav:
                if mobile:
                    story_link.tap(timeout=15000)
                else:
                    story_link.click(timeout=15000)
            article_response = nav.value
        except Exception as exc:
            check(False, f"{label}: deschiderea articolului reuseste ({exc})")
            return

        status = article_response.status if article_response else "fara raspuns"
        check(article_response is not None and article_response.ok,
              f"{label}: pagina articolului raspunde cu succes (HTTP {status})")
        if article_response is None or not article_response.ok:
            return

        actual_parts = urlsplit(page.url)
        actual_path = actual_parts.path.rstrip("/")
        expected_path = story_parts.path.rstrip("/")
        check(_is_site_host(actual_parts.hostname, base_parts.hostname)
              and actual_path == expected_path,
              f"{label}: navigarea ajunge la articolul selectat ({page.url})")

        h1 = page.locator("main article h1")
        try:
            h1.wait_for(state="visible", timeout=15000)
        except Exception as exc:
            check(False, f"{label}: articolul are un titlu principal ({exc})")
            return
        article_title = re.sub(r"\s+", " ", h1.inner_text()).strip()
        check(bool(article_title), f"{label}: titlul articolului este vizibil")
        check(article_title == story_title,
              f"{label}: articolul deschis corespunde titlului ales de pe homepage")
        content_blocks = page.locator(
            "main article .body, main article .official-note").count()
        check(content_blocks == 1,
              f"{label}: articolul prezinta rezumatul sau nota oficiala ({content_blocks})")
        if mobile:
            _check_mobile_overflow(page, "pagina articolului pe mobil")

        source_boxes = page.locator("main article .sources-box")
        source_box_count = source_boxes.count()
        check(source_box_count == 1,
              f"{label}: articolul are exact un bloc de surse ({source_box_count})")
        if source_box_count != 1:
            return

        source_links = source_boxes.first.locator("a[href]")
        source_count = source_links.count()
        check(source_count > 0, f"{label}: blocul de surse contine cel putin un link")
        if source_count == 0:
            return

        source = source_links.first
        source_label = re.sub(r"\s+", " ", source.inner_text()).strip()
        source_href = source.get_attribute("href") or ""
        source_parts = urlsplit(urljoin(page.url, source_href))
        source_is_external = (
            source_parts.scheme in {"http", "https"}
            and bool(source_parts.hostname)
            and not _is_site_host(source_parts.hostname, base_parts.hostname)
        )
        check(bool(source_label) and source_is_external,
              f"{label}: sursa are nume si destinatie externa ({source_href})")
        rel = set((source.get_attribute("rel") or "").lower().split())
        check(source.get_attribute("target") == "_blank"
              and {"noopener", "noreferrer"}.issubset(rel),
              f"{label}: linkul extern este protejat pentru deschidere in fila noua")

        source_boxes.first.scroll_into_view_if_needed()
        if mobile:
            page.screenshot(path=f"{SHOT_DIR}/visitor-mobile-article.png")
    finally:
        context.close()


def map_state(p):
    return p.evaluate("""() => {
      const s = document.querySelector('#map svg.map-svg');
      const stage = document.querySelector('#map .map-stage');
      const rect = s ? s.getBoundingClientRect() : null;
      return {
        svg: document.querySelectorAll('#map svg.map-svg').length,
        stages: document.querySelectorAll('#map .map-stage').length,
        viewBox: s ? s.getAttribute('viewBox') : null,
        cssW: rect ? Math.round(rect.width) : 0,
        cssH: rect ? Math.round(rect.height) : 0,
        aspect: stage ? getComputedStyle(stage).aspectRatio : '',
        counties: document.querySelectorAll('#map svg.map-svg .layer-counties path').length,
      };
    }""")


def map_signature(p):
    # Semnatura structurii randate: FNV-1a peste outerHTML-ul scenei. Prinde orice redesenare
    # care schimba ceva vizibil (noduri, clase, viewBox, transformari de etichete).
    return p.evaluate("""() => {
      const s = document.querySelector('#map svg.map-svg');
      if (!s) return null;
      const html = s.outerHTML;
      let h = 2166136261;
      for (let i = 0; i < html.length; i += 3) {
        h ^= html.charCodeAt(i);
        h = Math.imul(h, 16777619);
      }
      return h >>> 0;
    }""")


# Selectorii de aici tintesc STRUCTURA vizibila utilizatorului (`#news-list li a` = lista are
# articole pe care se poate da click), nu clase CSS interne. Motivul e masurat, nu stilistic:
# `.news-item` a disparut din `renderList()` pe 2026-08-12 (80b79b6a), iar garda a ramas rosie
# pana pe 2026-08-14 fara ca site-ul sa aiba nimic. Al treilea caz din acelasi tipar in repo
# (vezi STATE.md, cele 8 teste de harta care asertau pe identificatori inexistenti). Un id din
# index.html si un tag HTML se schimba rar; o clasa se rescrie la orice refactorizare de stil.
def check_map(p, mobile=False):
    p.wait_for_selector('#map svg.map-svg', timeout=15000)
    p.wait_for_selector('#news-list li a', timeout=15000)
    s0 = map_state(p)
    sig0 = map_signature(p)
    check(s0['svg'] == 1 and s0['stages'] == 1, f"o singura scena SVG initial ({s0['svg']} svg / {s0['stages']} stage)")
    check(s0['cssW'] > 0 and s0['cssH'] > 0, f"scena are dimensiuni valide ({s0['cssW']}x{s0['cssH']})")
    check(bool(s0['viewBox']) and len((s0['viewBox'] or '').split()) == 4, f"viewBox scris de JS ({s0['viewBox']})")
    check(s0['counties'] == 42, f"42 de judete randate ({s0['counties']})")
    n_art = p.locator('#news-list li a').count()
    check(n_art > 0, f"lista are articole ({n_art})")
    # Reproduce bugul: scroll repetat. Scena si structura randata trebuie sa ramana stabile.
    for _ in range(12):
        p.mouse.wheel(0, 900)
        p.wait_for_timeout(60)
        p.mouse.wheel(0, -900)
        p.wait_for_timeout(60)
    s1 = map_state(p)
    sig1 = map_signature(p)
    check(s1['svg'] == 1 and s1['stages'] == 1, f"scroll repetat pastreaza o singura scena ({s1['svg']} svg)")
    check(s1['viewBox'] == s0['viewBox'], "scrollul nu modifica vederea (viewBox identic)")
    check(sig1 == sig0, f"randarea SVG ramane identica dupa scroll ({sig0} -> {sig1})")
    # Resize/repaint repetat; fiecare stare trebuie sa aiba exact o scena valida.
    for w in [1100, 900, 700, 390, 1280, 1024]:
        p.set_viewport_size({'width': w, 'height': 844 if w < 600 else 900})
        p.wait_for_timeout(150)
        st = map_state(p)
        check(st['svg'] == 1 and st['stages'] == 1, f"resize {w}px pastreaza o scena SVG")
        check(st['cssW'] > 0 and st['cssH'] > 0, f"resize {w}px pastreaza scena randabila")
        check(st['counties'] == 42, f"resize {w}px pastreaza toate judetele")
    if mobile:
        over = p.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
        check(over <= 0, f"mobil fara overflow orizontal ({over}px)")


def main():
    os.makedirs(SHOT_DIR, exist_ok=True)
    with sync_playwright() as pw:
        br = pw.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage'])
        check_visitor_journey(br, mobile=False)
        check_visitor_journey(br, mobile=True)
        p = br.new_page(viewport={'width': 1280, 'height': 900})
        goto(p, BASE + '/static/harta-stiri/', 'harta', 'domcontentloaded')
        check_map(p)
        p.screenshot(path=f'{SHOT_DIR}/harta-regression.png', full_page=True)
        mob = br.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        goto(mob, BASE + '/static/harta-stiri/', 'mobile', 'domcontentloaded')
        # screenshot must come BEFORE check_map(), which contains a resize loop that leaves viewport at 1024px
        mob.screenshot(path=f'{SHOT_DIR}/harta-mobile-regression.png', full_page=True)
        check_map(mob, True)
        mob.close()
        br.close()
    if fails:
        print('\nFAIL')
        [print(' -', x) for x in fails]
        return 1
    print('\nOK: parcurs vizitator + regresia SVG/scroll/resize au trecut.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
