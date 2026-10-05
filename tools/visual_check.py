#!/usr/bin/env python
"""Verificare vizuala live + regresie SVG/scroll/redraw.

Adaptat la substratul SVG/DOM (2026-10-04, F1 din notes/harta-revolutie-proposal-2026-10-04.md):
harta nu mai are canvas, deci "imaginea randata" se citeste din DOM (semnatura structurii si a
stilurilor calculate), nu din pixeli. Ce acoperea verificarea inainte si se pastreaza:
  * o SINGURA suprafata de desenare, refolosita la scroll (dedublarea vizuala, e3832692);
  * scrollul nu modifica vederea (semnatura identica inainte/dupa);
  * fiecare pas de resize lasa o scena valida, cu dimensiuni nenule;
  * pe mobil nu apare overflow orizontal.

Ce NU mai acopera (si de ce e ok): pixelii exacti ai umpluturilor. In lumea SVG ei sunt dati
de CSS-ul declarat, iar garda de culoare e `tools/harta_contrast.py` -- determinist, fara
browser. Aici ramane intrebarea "se randeaza ceva si ramane stabil?", nu "ce nuanta are pixelul".
"""
import os, sys
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
        p.goto(u, wait_until=wait)
    except Exception as e:
        print(f"  FAIL navigare {label}: {e}")
        raise


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
        p = br.new_page(viewport={'width': 1280, 'height': 900})
        goto(p, BASE + '/harta/', 'harta', 'domcontentloaded')
        check_map(p)
        p.screenshot(path=f'{SHOT_DIR}/harta-regression.png', full_page=True)
        mob = br.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
        goto(mob, BASE + '/harta/', 'mobile', 'domcontentloaded')
        # screenshot must come BEFORE check_map(), which contains a resize loop that leaves viewport at 1024px
        mob.screenshot(path=f'{SHOT_DIR}/harta-mobile-regression.png', full_page=True)
        check_map(mob, True)
        mob.close()
        br.close()
    if fails:
        print('\nFAIL')
        [print(' -', x) for x in fails]
        return 1
    print('\nOK: regresia SVG/scroll/resize a trecut.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
