#!/usr/bin/env python
"""Verificare DOM randat pentru harta stirilor. Ruleaza cu serverul local pornit DIN RADACINA
   repo-ului -- index.html foloseste cai absolute (/static/...), deci un server din
   static/harta-stiri ar lasa JS-ul si CSS-ul pe 404 si pagina blocata in "Se încarcă…":
   python -m http.server 8765
   python -m generator.main --render-only
   python -m http.server 8765 --directory output
   MAP_URL=http://localhost:8765/harta/ python tools/harta_dom_check.py

Asserteaza pe STRUCTURA VIZIBILA si pe COMPORTAMENT OBSERVAT (id-uri, taguri, clickuri, geometrie),
nu pe clase CSS si nu pe identificatori din sursa -- de doua ori in repo-ul asta o garda a stat
verde/rosie pe un identificator care nu mai exista in codul livrat (IZZ-0177, IZZ-0182).

ADAPTAT LA SUBSTRATUL SVG/DOM (2026-10-04, F1 din notes/harta-revolutie-proposal-2026-10-04.md):
harta nu mai are canvas, deci verificarea nu mai citeste pixeli si nu mai reface transformarea
manual. Geometria o da chiar elementul (`getBBox`, `isPointInFill`, `getScreenCTM`), iar hit-testul
il confirma browserul (`elementFromPoint`) -- deci nu mai exista o a doua implementare care poate
diverga de cea livrata. Verificarile pastreaza aceleasi INTREBARI ca inainte: se poate atinge un
judet, clickul nu fura selectia, hoverul previzualizeaza, zoomul mareste si panul misca scena.
[NEVERIFICAT LA SCRIERE]: fisierul cere Playwright/Chromium, care nu exista in mediul in care s-a
facut adaptarea; prima rulare reala se face de pe masina cu browser si poate cere ajustari de
tolerante (nu de logica)."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

BASE = os.getenv("MAP_URL", "http://localhost:8765/harta/")
fails = []
skipped = []

def check(cond, label):
    print(f"  {'ok  ' if cond else 'FAIL'} {label}")
    if not cond:
        fails.append(label)

def skip(label):
    print(f"  ??   NEVERIFICAT: {label}")
    skipped.append(label)

# --- ajutoare de interactiune -------------------------------------------------

def stage_rect(p):
    return p.evaluate("""() => {
      const r = document.querySelector('#map svg.map-svg').getBoundingClientRect();
      return { x: r.x, y: r.y, w: r.width, h: r.height };
    }""")

INTERIOR_POINT = """async (mode) => {
  const d = await (await fetch('/static/harta-stiri/data/map.json')).json();
  const svg = document.querySelector('#map svg.map-svg');
  if (!svg) return null;
  const withNews = new Set((d.articles || []).map((a) => a.county).filter(Boolean));
  const nodes = new Map([...svg.querySelectorAll('.layer-counties path')].map((n) => [n.dataset.judet, n]));
  const box = (n) => { const b = n.getBBox(); return b.width * b.height; };
  let keys = Object.keys(d.map.judete);
  if (mode === 'empty') keys = keys.filter((k) => !withNews.has(k));
  else if (mode === 'news') keys = keys.filter((k) => withNews.has(k));
  keys = keys.filter((k) => nodes.has(k)).sort((a, b) => box(nodes.get(b)) - box(nodes.get(a)));
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  for (const key of keys) {
    const node = nodes.get(key);
    const b = node.getBBox();
    for (let row = 1; row < 12; row += 1) {
      for (let col = 1; col < 12; col += 1) {
        const local = new DOMPoint(b.x + b.width * col / 12, b.y + b.height * row / 12);
        if (!node.isPointInFill(local)) continue;
        const screen = local.matrixTransform(ctm);
        const at = document.elementFromPoint(screen.x, screen.y);
        const hit = at && at.closest('[data-judet]');
        if (!hit || hit.dataset.judet !== key) continue;
        return { county: key, x: screen.x, y: screen.y };
      }
    }
  }
  return null;
}"""

def interior_point(p, mode="news"):
    """Un punct de ECRAN verificat in interiorul unui judet (mode: 'news' / 'empty' / 'any').

    Inlocuieste replica manuala de transformare + Path2D din era canvas: geometria o da chiar
    elementul SVG (`getBBox` + `isPointInFill`), iar punctul e acceptat doar daca si hit-testul
    browserului (`elementFromPoint`) confirma ACELASI judet -- altfel testul ar rula pe o harta
    imaginara, nu pe cea livrata.
    """
    return p.evaluate(INTERIOR_POINT, mode)

def county_label(p, code):
    """Eticheta afisata a unui judet, din tabelul paginii (nu din codul brut)."""
    return p.evaluate("""(code) => {
      const el = document.querySelector('#judete-etichete');
      const table = JSON.parse((el && el.dataset.etichete) || '{}');
      return table[code] || code;
    }""", code)

def _vb(p):
    """viewBox-ul scenei ca [x, y, w, h], asteptand randarea: renderMap poate rescrie
    svg-ul asincron dupa reset/zoom, iar citirea oarba prinde un svg fara viewBox.
    Despartirea se face in Python — String.split() fara separator in JS intoarce tot
    sirul, nu fragmentele (capcana prinsa live la aceasta garda)."""
    p.wait_for_function(
        "() => { const s = document.querySelector('#map svg.map-svg');"
        " return s && s.getAttribute('viewBox'); }", timeout=5000)
    raw = p.evaluate(
        "() => { const s = document.querySelector('#map svg.map-svg');"
        " return s ? s.getAttribute('viewBox') : ''; }")
    return [float(v) for v in str(raw).split()]


def county_selected(p):
    """Butonul '<- Toate judetele' e ascuns exact cand state.selectedCounty e null."""
    return p.evaluate("() => { const b = document.querySelector('.map-back'); return !!b && !b.hidden; }")

def panel_count(p):
    return p.evaluate("() => document.querySelector('#panel-count').textContent.trim()")

def search_value(p):
    return p.evaluate("() => document.querySelector('#map-search').value")

def reset(p):
    # Resetarea completă este intenționat disponibilă în orice stare. Comanda contextuală
    # „Înapoi la România” este dezactivată corect atunci când nicio zonă nu este selectată.
    p.click("#reset-all")
    p.wait_for_timeout(120)


def county_route_targets(p):
    """Țintele SVG pentru angajarea pe județ: centru, rută și dimensiune în pixeli CSS."""
    return p.evaluate("""() => {
      const svg = document.querySelector('#map svg.map-svg');
      const ctm = svg && svg.getScreenCTM();
      if (!svg || !ctm) return [];
      return [...svg.querySelectorAll('.layer-targets .map-county-hit')].map((n) => {
        const local = new DOMPoint(Number(n.getAttribute('cx')), Number(n.getAttribute('cy')));
        const screen = local.matrixTransform(ctm);
        const b = n.getBoundingClientRect();
        return { county: n.dataset.judet, href: n.dataset.href,
                 x: screen.x, y: screen.y, width: b.width, height: b.height };
      }).sort((a, b) => a.county.localeCompare(b.county));
    }""")


def goto_base(p):
    # felia 2 #448: clickul pe harta poate porni o navigatie catre o ruta de judet cateva
    # zeci de ms DUPA actiune, deci goto-ul spre baza poate fi intrerupt. Reincercam:
    # lasam navigatia in curs sa se termine si reluam goto-ul, de pana la 3 ori.
    for _ in range(3):
        try:
            p.goto(BASE, wait_until="networkidle")
            break
        except Exception:
            try:
                p.wait_for_load_state("load", timeout=8000)
            except Exception:
                p.wait_for_timeout(250)
    else:
        p.goto(BASE, wait_until="networkidle")
    p.wait_for_selector("#map svg.map-svg .layer-counties path", timeout=15000)
    p.wait_for_timeout(150)


def swipe_touch(p, x, y, dy, steps=8):
    """Derulare cu un deget real (touchStart/touchMove/touchEnd prin CDP). Playwright nu are
    swipe tactil; `mouse.down/move/up` ar trimite evenimente de mouse, care pe telefon nu exista."""
    cdp = p.context.new_cdp_session(p)
    send = lambda t, pts: cdp.send("Input.dispatchTouchEvent", {"type": t, "touchPoints": pts})
    send("touchStart", [{"x": x, "y": y}])
    for i in range(1, steps + 1):
        send("touchMove", [{"x": x, "y": y + dy * i / steps}])
        p.wait_for_timeout(16)
    send("touchEnd", [])
    cdp.detach()

EDGE_SCAN = """(offsetY) => {
  const svg = document.querySelector('#map svg.map-svg');
  const rect = svg.getBoundingClientRect();
  const y = rect.top + offsetY;
  if (y < rect.top || y > rect.bottom) return null;
  for (let x = Math.floor(rect.left); x < rect.right; x += 1) {
    const at = document.elementFromPoint(x, y);
    const hit = at && at.closest('[data-judet]');
    if (hit) {
      return { edgeCss: x - rect.left, rectX: rect.left, rectY: rect.top };
    }
  }
  return null;
}"""

def edge_tolerance_px(p, max_px=8):
    """Cat de departe IN AFARA conturului tarii mai selecteaza o atingere, in pixeli CSS.
    Cauta marginea din stanga a uscatului pe cateva linii orizontale, apoi se departeaza pas cu
    pas si returneaza cea mai mare distanta la care inca s-a selectat un judet. None daca nu s-a
    gasit nicio margine utilizabila -- se raporteaza ca NEVERIFICAT, nu ca reusita."""
    r = stage_rect(p)
    best = None
    for frac in (0.40, 0.50, 0.60):
        hit = p.evaluate(EDGE_SCAN, r["h"] * frac)
        if not hit or hit["edgeCss"] < max_px + 2:
            continue
        y = r["y"] + r["h"] * frac
        for d in range(1, max_px + 1):
            p.touchscreen.tap(r["x"] + hit["edgeCss"] - d, y)
            p.wait_for_timeout(60)
            if county_selected(p):
                best = max(best or 0, d)
                reset(p)
            else:
                break
    return best

def bright_fill_pixels(p):
    """Cate judete sunt APRINSE (fara estompare). In era canvas se numarau pixelii de umplere
    neestompata; acum estomparea e o clasa (`is-dim`, opacity .28), deci se numara direct
    nodurile -- aceeasi intrebare („harta nu se contrazice cu lista?"), fara pixeli."""
    return p.evaluate("""() => {
      const nodes = [...document.querySelectorAll('#map svg.map-svg .layer-counties path')];
      return nodes.filter((n) => Number(getComputedStyle(n).opacity) > 0.99).length;
    }""")

# --- verificari ---------------------------------------------------------------

def felia1_lista(p):
    print("\nFELIA 1 -- lista de rezultate")
    p.wait_for_function("() => document.querySelector('#news-list li a') !== null", timeout=15000)
    box = p.evaluate("""() => {
      const li = document.querySelector('#news-list li');
      const a = li && li.querySelector('a'), s = li && li.querySelector('span');
      if (!a || !s) return { error: 'missing a or span' };
      const ra = a.getBoundingClientRect(), rs = s.getBoundingClientRect();
      return {
        tag: document.querySelector('#news-list').tagName,
        aDisplay: getComputedStyle(a).display,
        sDisplay: getComputedStyle(s).display,
        sameLine: Math.abs(ra.top - rs.top) < 2,
        gap: rs.top - ra.bottom,
        count: document.querySelector('#panel-count').textContent.trim(),
      };
    }""")
    check(box.get("tag") == "UL", f"#news-list este <ul> (e {box.get('tag')})")
    check(box.get("aDisplay") == "block", f"titlul e bloc ({box.get('aDisplay')})")
    check(box.get("sDisplay") == "block", f"meta e bloc ({box.get('sDisplay')})")
    check(not box.get("sameLine"), "titlul si meta NU sunt pe acelasi rand")
    check(box.get("gap", 0) >= 3, f"spatiu vertical intre titlu si meta ({box.get('gap', 0):.1f}px)")
    check(" din " in box.get("count", ""), f"panel-count arata totalul ('{box.get('count')}')")

def felia7_cautare(p):
    print("\nFELIA 7 -- ce cauta lupa de pe harta")
    # (a) cautare de loc: potrivirile de loc urca primele, iar antetul spune cate sunt
    p.fill("#map-search", "Cluj")
    p.wait_for_timeout(250)
    res = p.evaluate("""() => {
      const rows = [...document.querySelectorAll('#news-list li')].map(li => ({
        meta: (li.querySelector('span') || {}).textContent || '',
      }));
      return { count: document.querySelector('#panel-count').textContent.trim(), rows, n: rows.length };
    }""")
    place = [i for i, r in enumerate(res["rows"]) if "CLUJ" in r["meta"].upper()]
    other = [i for i, r in enumerate(res["rows"]) if "CLUJ" not in r["meta"].upper()]
    check(res["n"] > 0, f"'Cluj' intoarce rezultate ({res['n']})")
    check("potriviri de loc" in res["count"], f"antetul explica potrivirile ('{res['count']}')")
    check(bool(place), f"exista potriviri de loc ({len(place)})")
    if place and other:
        check(max(place) < min(other),
              f"potrivirile de loc sunt PRIMELE (ultima de loc: {max(place)}, prima de titlu: {min(other)})")
    else:
        skip("ordinea loc-inainte-de-titlu: setul nu contine ambele feluri de potrivire")

    # (b) anti-regresie: un cuvant care NU e loc trebuie sa intoarca in continuare rezultate.
    # 'ACCIDENT' apare in 15 titluri si in 0 nume de loc (masurat pe map.json, 14 aug 2026).
    p.fill("#map-search", "accident")
    p.wait_for_timeout(250)
    n = p.evaluate("() => document.querySelectorAll('#news-list li a').length")
    check(n > 0, f"'accident' (cuvant care nu e loc) intoarce rezultate, nu zero ({n})")

    # (c) harta si lista nu se contrazic: judetele care au rezultate raman aprinse
    bright_query = bright_fill_pixels(p)
    reset(p)
    p.wait_for_timeout(150)
    bright_all = bright_fill_pixels(p)
    check(0 < bright_query <= bright_all,
          f"harta pastreaza judete aprinse la cautare non-geografica ({bright_query} judete vs {bright_all} fara filtru)")

def felia4_hittest(p):
    print("\nFELIA 2 #448 -- click/tap pe județ deschide ruta statică")
    goto_base(p)
    targets = county_route_targets(p)
    check(len(targets) == 42, f"există câte o țintă tactilă pentru toate cele 42 de județe ({len(targets)})")
    mici = [t for t in targets if t.get("width", 0) < 24 or t.get("height", 0) < 24]
    check(not mici, "toate țintele de atingere au cel puțin 24×24px" if not mici
          else f"ținte sub 24px: {[(t['county'], round(t.get('width', 0), 1), round(t.get('height', 0), 1)) for t in mici[:5]]}")

    # Click real pe centrul țintei fiecărui județ. Validăm ruta și HTTP 200, nu doar faptul că
    # un handler a rulat local. Asta apără exact contractul „previzualizare -> angajare”.
    for target in targets:
        goto_base(p)
        fresh = [t for t in county_route_targets(p) if t["county"] == target["county"]][0]
        with p.expect_navigation(wait_until="networkidle", timeout=8000) as nav:
            p.mouse.click(fresh["x"], fresh["y"])
        response = nav.value
        path = p.evaluate("() => location.pathname")
        check(path == fresh["href"] and response and response.status == 200,
              f"click pe {fresh['county']} -> {path} (status {response.status if response else 'fără răspuns'})")

    # Tastatura: poligonul însuși rămâne focusabil; Enter/Space activează aceeași rută.
    for county, key in (("TIMIS", "Enter"), ("BUCURESTI", "Space")):
        goto_base(p)
        href = p.evaluate("""(county) => {
          const n = document.querySelector(`.layer-counties path[data-judet="${county}"]`);
          n && n.focus();
          return n ? n.dataset.href : null;
        }""", county)
        with p.expect_navigation(wait_until="networkidle", timeout=8000) as nav:
            p.keyboard.press(key)
        response = nav.value
        path = p.evaluate("() => location.pathname")
        check(path == href and response and response.status == 200,
              f"tastatura {key!r} pe {county} -> {path} (status {response.status if response else 'fără răspuns'})")

    # În afara țării: un punct clar din colțul scenei nu are voie să navigheze.
    goto_base(p)
    r = stage_rect(p)
    before = p.evaluate("() => location.pathname")
    p.mouse.click(r["x"] + 3, r["y"] + 3)
    p.wait_for_timeout(250)
    check(p.evaluate("() => location.pathname") == before,
          "apasarea departe de conturul țării nu deschide nicio rută")

    # Garda tap-vs-drag: o derulare care începe pe hartă nu trebuie să angajeze județul.
    cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
    p.mouse.move(cx, cy)
    p.mouse.down()
    p.mouse.move(cx, cy + 120, steps=6)
    p.mouse.up()
    p.wait_for_timeout(250)
    check(p.evaluate("() => location.pathname") == before,
          "derularea/tragerea pe hartă NU deschide ruta unui județ")

def hit_ordin_fara_furt(p):
    """Hit-testul e EXACT, iar geometria si browserul sunt de acord (audit harta, P0).

    In era canvas exista o cascada proprie de candidati (poligonul, apoi bulinele din raza de
    toleranta", iar bugul era ca bulina unui vecin putea fura un click clar in interiorul altui
    judet. Acum tinta clickului e chiar elementul de sub cursor, deci cascada nu mai exista in
    cod -- ce ramane de verificat e ca elementul returnat de browser (`elementFromPoint`) e exact
    poligonul care contine punctul (`isPointInFill`), pe o grila de puncte, si ca enclava
    Bucuresti nu e inghitita de Ilfov. Daca verificarea nu se poate face, se raporteaza
    NEVERIFICAT, nu verde.
    """
    print("\nHIT-TEST EXACT -- elementul de sub cursor = poligonul care contine punctul")
    p.locator("#map svg.map-svg").scroll_into_view_if_needed()
    p.wait_for_timeout(150)
    out = p.evaluate("""() => {
      const svg = document.querySelector('#map svg.map-svg');
      const r = svg.getBoundingClientRect();
      const ctm = svg.getScreenCTM();
      if (!ctm) return null;
      const inv = ctm.inverse();
      const paths = [...svg.querySelectorAll('.layer-counties path')];
      // owner = poligonul cu aria-bbox minima care contine exact punctul (enclava bate invelisul).
      const ownerAt = (sx, sy) => {
        const local = new DOMPoint(sx, sy).matrixTransform(inv);
        let owner = null, ownerArea = Infinity;
        for (const cand of paths) {
          if (!cand.isPointInFill(local)) continue;
          const b = cand.getBBox();
          const area = b.width * b.height;
          if (area < ownerArea) { ownerArea = area; owner = cand; }
        }
        return owner;
      };
      let checked = 0, agree = 0, frontiera = 0;
      const bad = [], frontBad = [];
      for (let i = 1; i < 10; i += 1) {
        for (let j = 1; j < 10; j += 1) {
          const x = r.left + r.width * i / 10, y = r.top + r.height * j / 10;
          const stack = document.elementsFromPoint(x, y);
          const node = stack.find((el) => el.matches && el.matches('.layer-counties path[data-judet]')) || null;
          const owner = ownerAt(x, y);
          checked += 1;
          if (node === owner) { agree += 1; continue; }
          // Frontiera ambigua (issue #454, verdict Arena — sonde/arena-raspuns-454.txt): pe
          // pixelul de granita, pictura browserului si geometria exacta se contrazic legitim.
          // Vecinatatea 3x3 px explica punctul, dar NU-l transforma in PASS — o fâșie de județ
          // sau o exclavă la 1px ar masca un bug real. Se raporteaza ca numar separat; esecul
          // ramane esec, cu diferentele reale separate de cele explicabile.
          let vecinAgree = false;
          if (node) {
            for (let dx = -1; dx <= 1 && !vecinAgree; dx += 1) {
              for (let dy = -1; dy <= 1 && !vecinAgree; dy += 1) {
                if (!dx && !dy) continue;
                if (ownerAt(x + dx, y + dy) === node) vecinAgree = true;
              }
            }
          }
          if (vecinAgree) {
            frontiera += 1;
            if (frontBad.length < 5) {
              frontBad.push({ x: Math.round(x), y: Math.round(y),
                             tinta: node.dataset.judet,
                             geometrie: owner ? owner.dataset.judet : null });
            }
            continue;
          }
          bad.push({ x: Math.round(x), y: Math.round(y),
                     tinta: node ? node.dataset.judet : null,
                     geometrie: owner ? owner.dataset.judet : null });
        }
      }
      return { checked, agree, frontiera, frontBad, bad: bad.slice(0, 5) };
    }""")
    if out is None:
        skip("hit-test exact: scena nu are CTM (nu se poate converti punctul in spatiul hartii)")
    elif out["agree"] != out["checked"]:
        extra = f"; {out['frontiera']} frontiera ambigua {out['frontBad']}" if out["frontiera"] else ""
        check(False, f"hit-testul si geometria sunt de acord ({out['agree']}/{out['checked']}{extra}; "
                     f"diferente reale: {out['bad']})")
    else:
        check(True, f"hit-testul si geometria sunt de acord pe toata grila ({out['agree']}/{out['checked']})")

    enclave = p.evaluate("""() => {
      const svg = document.querySelector('#map svg.map-svg');
      const buc = svg.querySelector('[data-judet=\"BUCURESTI\"]');
      if (!buc) return null;
      const ctm = svg.getScreenCTM();
      const b = buc.getBBox();
      for (let row = 1; row < 12; row += 1) {
        for (let col = 1; col < 12; col += 1) {
          const local = new DOMPoint(b.x + b.width * col / 12, b.y + b.height * row / 12);
          if (!buc.isPointInFill(local)) continue;
          const screen = local.matrixTransform(ctm);
          const stack = document.elementsFromPoint(screen.x, screen.y);
          const node = stack.find((el) => el.matches && el.matches('.layer-counties path[data-judet]')) || null;
          return { hit: node ? node.dataset.judet : null };
        }
      }
      return null;
    }""")
    if enclave is None:
        skip("enclava Bucuresti: poligonul nu are niciun punct interior verificabil in vedere")
    else:
        check(enclave["hit"] == "BUCURESTI",
              f"centrul Bucurestiului loveste BUCURESTI, nu Ilfov (a lovit {enclave['hit']})")
    reset(p)


def ilfov_click_geometric(p):
    """Punctul de ancorare ILFOV cade si in poligonul BUCURESTI (desenat deasupra).
    Clickul trebuie rezolvat dupa geometria formelor, nu doar dupa elementFromPoint.
    Cu felia 2 #448, angajarea ILFOV deschide ruta /harta/ilfov/ (navigare)."""
    print("\nILFOV / BUCURESTI -- click geometric pe ancora suprapusa")
    p.goto(BASE, wait_until="networkidle")
    p.wait_for_selector("#map svg.map-svg .layer-counties path[data-judet='ILFOV']", timeout=15000)
    p.locator("#map svg.map-svg").scroll_into_view_if_needed()
    p.wait_for_timeout(100)
    pt = p.evaluate("""() => {
      const svg = document.querySelector('#map svg.map-svg');
      const ilfov = svg.querySelector('[data-judet="ILFOV"]');
      const bucuresti = svg.querySelector('[data-judet="BUCURESTI"]');
      if (!ilfov || !bucuresti) return null;
      const b = ilfov.getBBox();
      const local = new DOMPoint(b.x + b.width / 2, b.y + b.height / 2);
      const ctm = ilfov.getScreenCTM();
      if (!ctm) return null;
      const screen = local.matrixTransform(ctm);
      const inBucuresti = new DOMPoint(screen.x, screen.y)
        .matrixTransform(bucuresti.getScreenCTM().inverse());
      const at = document.elementFromPoint(screen.x, screen.y);
      const top = at && at.closest('[data-judet]');
      return {
        x: screen.x, y: screen.y,
        inIlfov: ilfov.isPointInFill(local),
        inBucuresti: bucuresti.isPointInFill(inBucuresti),
        top: top ? top.dataset.judet : null,
      };
    }""")
    if not pt or not pt["inIlfov"] or not pt["inBucuresti"]:
        skip("ancora ILFOV nu este simultan in ambele poligoane in randarea curenta")
        return
    check(pt["top"] == "BUCURESTI",
          f"punctul ILFOV este acoperit de hit-testul DOM Bucuresti ({pt['top']})")
    with p.expect_navigation(wait_until="networkidle", timeout=8000) as nav:
        p.mouse.click(pt["x"], pt["y"])
    response = nav.value
    path = p.evaluate("() => location.pathname")
    check(path == "/harta/ilfov/" and response and response.status == 200,
          f"clickul pe ancora ILFOV angajeaza /harta/ilfov/ (a ajuns pe {path}, status {response.status if response else 'fara raspuns'})")


def hover_preview(p):
    """hover = previzualizare peste tot (audit harta, P1): la nivel national, numele si cifra
    judetului apar sub cursor INAINTE de click, la fel ca la UAT-uri."""
    print("\nHOVER PREVIEW -- numele zonei de sub cursor, inainte de click")
    p.locator("#map svg.map-svg").scroll_into_view_if_needed()
    p.wait_for_timeout(150)
    pt = interior_point(p, "news")
    if not pt or pt.get("x") is None:
        skip("nu am gasit un punct interior verificat -- hoverul nu a putut fi testat")
        return
    p.mouse.move(pt["x"], pt["y"], steps=3)
    p.wait_for_timeout(250)
    tip = p.evaluate("""() => {
      const t = document.querySelector('.map-tip');
      return { hidden: t ? t.hidden : null, text: t ? t.textContent.trim() : '' };
    }""")
    check(bool(tip["text"]) and not tip["hidden"],
          f"tooltipul arata zona de sub cursor inainte de click ('{tip['text']}')")
    label = county_label(p, pt["county"])
    check(label in tip["text"],
          f"numele e cel al judetului tintit ({label}, cod {pt['county']})")
    # Click = selectare; hover = doar previzualizare. La iesirea de pe scena, totul dispare.
    r = stage_rect(p)
    p.mouse.move(r["x"] + r["w"] + 12, r["y"] + r["h"] / 2, steps=2)
    p.wait_for_timeout(200)
    check(p.evaluate("() => document.querySelector('.map-tip').hidden"),
          "la iesirea de pe harta tooltipul dispare")


def click_zona_fara_stiri(p):
    """Județele fără știri nu sunt click mort: angajarea lor deschide pagina județului,
    unde starea inițială arată mesajul de gol dacă filtrul curent nu are articole."""
    print("\nCLICK PE ZONA FARA STIRI -- deschide ruta județului, nu moare")
    goto_base(p)
    target = interior_point(p, "empty")
    if not target:
        skip("toate judetele au stiri in datele curente -- scenariul nu se poate declansa")
        return
    href = p.evaluate("""(county) => document.querySelector(`.layer-counties path[data-judet="${county}"]`)?.dataset.href""",
                      target["county"])
    with p.expect_navigation(wait_until="networkidle", timeout=8000) as nav:
        p.mouse.click(target["x"], target["y"])
    response = nav.value
    path = p.evaluate("() => location.pathname")
    check(path == href and response and response.status == 200,
          f"județul fără știri ({target['county']}) deschide {path} (status {response.status if response else 'fără răspuns'})")
    empty_text = p.evaluate("() => document.querySelector('#news-list li.empty')?.textContent || ''")
    check("Nu există știri localizate" in empty_text,
          f"panoul rutei răspunde cu mesaj explicit de gol ('{empty_text[:80]}')")
    goto_base(p)
    p.wait_for_timeout(150)

def scara_si_numitor(p):
    """Aceeași culoare = același număr, în AMBELE scări (F3).

    Verificarea nu are încredere în ce spune pagina despre ea însăși: ia pragurile din legendă,
    numerele din `aria-label` (adică exact cifra citită și de cititorul de ecran) și clasa de
    culoare de pe fiecare nod, apoi le pune față în față. În modul „pe locuitor" recalculează
    independent raportul din `populatie.json` + `map.json`, deci o rotunjire greșită sau un
    numitor nepotrivit iese la iveală.
    """
    print("\nSCARA SI NUMITOR -- aceeasi culoare = acelasi numar, in ambele scari")
    p.wait_for_selector("#map svg.map-svg .layer-counties path", timeout=15000)

    def praguri(nume):
        return p.evaluate("""(nume) => {
          const at = nume === 'locuitori' ? 'praguriLocuitor' : 'praguri';
          const raw = document.querySelector('#map-legend').dataset[at] || '';
          return raw.split(',').map(Number).filter((n) => n > 0);
        }""", nume)

    def verifica(nume, toleranta=1e-9):
        return p.evaluate("""({praguri, toleranta}) => {
          const node = (v) => {
            if (!v) return 'h0';
            return 'h' + Math.min(4, praguri.filter((q) => v >= q).length);
          };
          const rele = [];
          let n = 0;
          for (const el of document.querySelectorAll('#map svg.map-svg .layer-counties path')) {
            const aria = el.getAttribute('aria-label') || '';
            const m = aria.match(/:(\\s*)(\\d+(?:[.,]\\d)?)/);
            if (!m) continue;
            const valoare = Number(m[2].replace(',', '.'));
            const clase = [...el.classList].filter((c) => /^h\\d$/.test(c));
            n++;
            if (clase.length !== 1 || clase[0] !== node(valoare)) {
              rele.push(el.dataset.judet + '=' + valoare + '->' + clase.join('/'));
            }
          }
          return { n, rele: rele.slice(0, 5), releCount: rele.length };
        }""", {"praguri": praguri(nume), "toleranta": toleranta})

    # (a) modul implicit: volum
    volum = verifica("volum")
    check(volum["n"] >= 40, f"scara de volum: cifra si culoarea coincid pe {volum['n']} județe")
    if volum["releCount"]:
        check(False, f"scara de volum: {volum['releCount']} județe cu culoarea nepotrivita ({volum['rele']})")

    # (b) comutarea pe „pe locuitor": o singura cerere de numitor
    cereri = []
    p.on("request", lambda r: cereri.append(r.url) if "populatie.json" in r.url else None)
    p.click('.segmented [data-scale="locuitori"]')
    p.wait_for_timeout(600)
    check(len(cereri) == 1, f"numitorul se cere o singura data ({len(cereri)} cereri)")
    rate = verifica("locuitori")
    check(rate["n"] >= 40, f"scara pe locuitor: cifra si culoarea coincid pe {rate['n']} județe")
    if rate["releCount"]:
        check(False, f"scara pe locuitor: {rate['releCount']} județe cu culoarea nepotrivita ({rate['rele']})")

    # (c) cifra afisata = raportul recalculat din date (independent de JS-ul paginii)
    abateri = p.evaluate("""async () => {
      const pop = (await (await fetch('/static/harta-stiri/data/populatie.json')).json()).judete;
      const date = await (await fetch('/static/harta-stiri/data/map.json')).json();
      const peEveniment = new Map();
      for (const a of date.articles || []) {
        if (!a.county) continue;
        const k = a.event_id || a.slug || a.title;
        if (!peEveniment.has(k)) peEveniment.set(k, a.county);
      }
      const counts = {};
      for (const c of peEveniment.values()) counts[c] = (counts[c] || 0) + 1;
      const rele = [];
      for (const el of document.querySelectorAll('#map svg.map-svg .layer-counties path')) {
        const code = el.dataset.judet;
        if (!pop[code]) continue;
        const asteptat = Math.round((counts[code] || 0) / pop[code] * 100000 * 10) / 10;
        const m = (el.getAttribute('aria-label') || '').match(/:(\\s*)(\\d+(?:[.,]\\d)?)/);
        if (!m) continue;
        if (Math.abs(Number(m[2].replace(',', '.')) - asteptat) > 0.001) {
          rele.push(code + ': ' + m[2] + ' vs ' + asteptat);
        }
      }
      return rele.slice(0, 5);
    }""")
    check(not abateri, f"cifra afisata = numarator/numitor recalculat din date ({abateri})")

    # (d) legenda: titlul si benzile modului, fara text rupt
    stare = p.evaluate("""() => {
      const l = document.querySelector('#map-legend');
      return {
        titlu: (l.querySelector('[data-title=\"locuitori\"]') || {}).hidden,
        benzi: (l.querySelector('[data-bands=\"locuitori\"]') || {}).hidden,
        text: l.textContent.replace(/\\s+/g, ' ').trim(),
        vizibila: !l.hidden,
      };
    }""")
    check(stare["vizibila"] and stare["titlu"] is False and stare["benzi"] is False,
          "legenda arata benzile de rate cand scara e pe locuitor")
    check("NaN" not in stare["text"] and "undefined" not in stare["text"],
          f"legenda nu contine text rupt ('{stare['text'][:70]}')")

    # (e) revenirea e curata
    p.click('.segmented [data-scale="volum"]')
    p.wait_for_timeout(400)
    revenit = verifica("volum")
    check(revenit["releCount"] == 0 and revenit["n"] >= 40, "revenirea pe volum pastreaza invariant")
    check("scara=" not in (p.evaluate("() => location.search") or ""),
          "adresa nu mai contine modul dupa revenire")


def felia2_localitate(p):
    print("\nFELIA 2 -- click pe localitate nu fura campul de cautare")
    goto_base(p)
    # Intrarea în județ se face prin selectorul HTML: clickul pe poligon angajează acum ruta
    # statică, deci nu mai este calea de filtrare în același document.
    p.click("#county-picker button[data-county]")
    p.wait_for_timeout(45)
    if not county_selected(p):
        skip("nu s-a putut intra pe niciun judet din picker -- verificarea localitatii nu a rulat")
        return

    before = panel_count(p)
    zr = stage_rect(p)
    found = False
    for i in range(1, 13):
        for j in range(1, 13):
            p.mouse.click(zr["x"] + zr["w"] * i / 13, zr["y"] + zr["h"] * j / 13)
            p.wait_for_timeout(35)
            try:
                path_now = p.evaluate("() => location.pathname")
            except Exception:
                path_now = None  # navigatie in curs (felie 2): tratam ca iesire din document
            if path_now != "/harta/":
                # felia 2 #448: un click din grila a nimerit un judet vecin vizibil si a angajat
                # ruta; lasam navigatia sa se termine, revenim pe nationala si reluam cautarea.
                try:
                    p.wait_for_load_state("load", timeout=8000)
                except Exception:
                    pass
                goto_base(p)
                p.click("#county-picker button[data-county]")
                p.wait_for_timeout(45)
                before = panel_count(p)
                zr = stage_rect(p)
                continue
            try:
                if panel_count(p) != before:
                    found = True
                    break
            except Exception:
                try:
                    p.wait_for_load_state("load", timeout=8000)
                    path_now = p.evaluate("() => location.pathname")
                except Exception:
                    path_now = None
                if path_now != "/harta/":
                    goto_base(p)
                    p.click("#county-picker button[data-county]")
                    p.wait_for_timeout(45)
                    before = panel_count(p)
                    zr = stage_rect(p)
                continue
        if found:
            break
    if not found:
        skip("niciun marker de localitate nimerit in judetul intrat -- nu s-a putut testa")
        reset(p)
        return
    check(search_value(p) == "",
          f"selectarea localitatii lasa campul de cautare gol (e '{search_value(p)}')")
    reset(p)

    # Localitati suprapuse: mai multe inregistrari SIRUTA pot cadea pe exact acelasi punct si sunt
    # unite intr-un singur marker. La click se filtreaza pe TOATE, nu doar pe prima (altfel stirile
    # celorlalte dispar tacut). Gruparea se face pe cheie de coordonate EXACTA, deci daca setul de
    # date curent nu contine niciun punct partajat, comportamentul nu se poate declansa -- si atunci
    # se raporteaza NEVERIFICAT, nu verde. Cand apar grupuri, tinta se poate calcula din map.json
    # (`map.viewbox` + geometria elementelor) si atunci verificarea devine: lista rezultata dintr-un
    # singur tap contine >= 2 localitati distincte.
    groups = p.evaluate("""async () => {
      const d = await (await fetch('/static/harta-stiri/data/map.json')).json();
      const byPoint = new Map();
      for (const a of d.articles || []) {
        if (a.x == null || a.y == null) continue;
        const k = a.x.toFixed(2) + ',' + a.y.toFixed(2);
        if (!byPoint.has(k)) byPoint.set(k, new Set());
        byPoint.get(k).add((a.locality || '').trim());
      }
      return [...byPoint.values()].filter((s) => s.size > 1).length;
    }""")
    if groups:
        skip(f"localitati suprapuse: exista {groups} puncte partajate, dar tintirea lor nu e inca implementata")
    else:
        skip("localitati suprapuse: 0 puncte partajate in datele curente, comportamentul nu se poate declansa")

def felia5_county_picker(p):
    """Scopul feliei e ca harta sa fie folosibila FARA MOUSE. Deci verificarea trebuie sa treaca
    prin tastatura de la cap la coada: daca butoanele ar fi <div>-uri nefocusabile, un test care
    face `p.click()` ar ramane verde si ar rata exact defectul pentru care exista felia."""
    print("\nFELIA 5 -- selector de judet de la tastatura")
    count = p.evaluate("() => document.querySelectorAll('#county-picker button').length")
    check(count > 0, f"#county-picker contine butoane de judet ({count})")
    if not count:
        skip("restul feliei 5: nu exista butoane de judet, nu am ce naviga")
        return

    # Tab pana cand focusul CHIAR ajunge pe un buton din picker. Fara aserttia asta nu stim
    # daca elementele sunt focusabile -- adica exact intrebarea feliei.
    p.evaluate("() => document.body.focus()")
    landed = None
    for _ in range(60):
        p.keyboard.press("Tab")
        info = p.evaluate("""() => {
          const a = document.activeElement;
          return { inPicker: !!(a && a.closest && a.closest('#county-picker')),
                   tag: a ? a.tagName : null, text: a ? (a.textContent || '').trim().slice(0, 24) : '' };
        }""")
        if info["inPicker"]:
            landed = info
            break
    check(landed is not None,
          f"focusul ajunge pe un buton de judet doar din Tab ({landed['tag'] + ' ' + landed['text'] if landed else 'niciodata'})")
    if landed is None:
        skip("selectarea cu Enter: focusul nu a ajuns niciodata pe picker")
        return

    before = panel_count(p)
    buttons_before = p.evaluate("() => document.querySelectorAll('#county-picker button').length")
    # ENTER, nu click: click-ul ar testa mouse-ul, adica fix ce felia asta NU rezolva.
    p.keyboard.press("Enter")
    p.wait_for_timeout(200)
    after = panel_count(p)
    check(after != before, f"Enter pe buton filtreaza lista ('{before}' -> '{after}')")
    # Starea vizibila de selectie are doua forme legitime: butonul de judet cu aria-pressed
    # (daca UAT-urile județului nu s-au incarcat inca) sau pickerul deja trecut pe lista de
    # UAT-uri (comportament proaspat implementat -- butoanele UAT au aria-haspopup, nu
    # aria-pressed). Incarcarea UAT e asincrona, deci intre cele doua e o cursa care nu tine
    # de felia 5; aserțiunea accepta ambele, nu o singura fereastra de timp norocoasa.
    sel = p.evaluate("""() => {
      const a = document.activeElement;
      const inPicker = !!(a && a.closest && a.closest('#county-picker'));
      const picker = document.querySelector('#county-picker');
      return {
        pressed: inPicker && a.getAttribute('aria-pressed') === 'true',
        uats: inPicker && a.hasAttribute('data-uat'),
        popup: inPicker ? a.getAttribute('aria-haspopup') : null,
        label: picker ? (picker.getAttribute('aria-label') || '') : '',
      };
    }""")
    # A treia forma legitima: dupa Enter pickerul se reconstruieste pe lista UAT a judetului
    # si focusul se pierde in replaceChildren; eticheta pickerului („Orașe și comune din X")
    # este dovada stabila a selectiei in fereastra aceea de cursa.
    check(sel["pressed"] or sel["uats"] or sel["label"].startswith("Orașe și comune din"),
          f"selectia e vizibila pe buton sau in eticheta pickerului (aria-pressed={sel['pressed']}, buton UAT={sel['uats']}, haspopup={sel['popup']}, label='{sel['label']}')")

    # Capcana de blocare: picker-ul se reconstruieste din stirile VIZIBILE, iar dupa selectie
    # vizibile sunt doar ale judetului ales. Daca ar ramane un singur buton, utilizatorul de
    # tastatura nu mai poate trece la alt judet -- acelasi mod de esec ca harta "blocata" pe
    # judet raportata pe 12 aug, doar pe alta cale.
    buttons_after = p.evaluate("() => document.querySelectorAll('#county-picker button').length")
    check(buttons_after >= 2,
          f"dupa selectie raman butoane pentru alte judete ({buttons_before} -> {buttons_after})")

    reset(p)
    p.wait_for_timeout(150)
    pressed = p.evaluate("() => document.querySelectorAll('#county-picker button[aria-pressed=\"true\"]').length")
    check(pressed == 0, f"dupa reset niciun buton nu e selectat ({pressed} inca selectate)")

def felia6_url(p):
    """Starea in adresa. Se verifica in ambele sensuri -- stare -> adresa SI adresa -> stare --
    fiindca o singura directie poate fi corecta izolat: un link care se scrie dar nu se citeste
    arata bine in bara de adrese si duce pe harta nefiltrata cand il deschide altcineva."""
    print("\nFELIA 6 -- starea in adresa paginii")
    p.goto(BASE, wait_until="networkidle")
    p.wait_for_selector("#county-picker button", timeout=15000)
    p.wait_for_timeout(200)
    start_count = panel_count(p)

    # (a) stare -> adresa
    p.click("#county-picker button")
    p.wait_for_timeout(250)
    search = p.evaluate("() => location.search")
    check("judet=" in search, f"selectia de judet ajunge in adresa ('{search}')")
    check(panel_count(p) != start_count, f"selectia chiar a filtrat lista ('{panel_count(p)}')")

    # (b) Back anuleaza selectia in loc sa iasa de pe pagina
    p.go_back()
    p.wait_for_timeout(350)
    check(not county_selected(p) and p.evaluate("() => location.search") != search,
          f"Back anuleaza selectia, nu paraseste pagina (adresa: '{p.evaluate('() => location.search')}')")

    # (c) adresa -> stare, fara niciun click. Fara asta un link partajat duce pe harta goala.
    p.goto(BASE + "?judet=CLUJ&nivel=local", wait_until="networkidle")
    p.wait_for_selector("#news-list li", timeout=15000)
    p.wait_for_timeout(350)
    direct = panel_count(p)
    check(county_selected(p), "link direct cu ?judet= arata judetul deja selectat")
    check(direct != start_count, f"link direct cu ?judet= arata lista filtrata ('{direct}')")
    # Filtrat NU e acelasi lucru cu filtrat pe judetul CERUT: un cod care citeste parametrul si
    # apoi aplica altceva ar trece un test care se uita doar la numarul de rezultate.
    # Doar span-urile de META, nu si cele de context-eveniment ("N relatări · M surse"),
    # care nu contin judet prin constructie. Pe datele vechi cele doua selectoare coincideau;
    # din 5 sep 2026, 2 evenimente CLUJ au relatări multiple si le dezvaluie (falsa alarma).
    metas = p.evaluate("() => [...document.querySelectorAll('#news-list li span:not(.event-context)')].map(s => s.textContent.toUpperCase())")
    off = [m for m in metas if "CLUJ" not in m]
    check(bool(metas) and not off,
          f"toate cele {len(metas)} rezultate sunt din CLUJ ({len(off)} din alt judet)")
    p.goto(BASE, wait_until="networkidle")
    p.wait_for_selector("#news-list li", timeout=15000)

def uat_selectie(p):
    """Click pe UAT = selectare (audit harta, P0): panoul filtreaza, adresa primeste uat=,
    Back anuleaza, clickul repetat deselecteaza, iar un link direct restabileste selectia.
    Dialogul a fost ELIMINAT prin unificare -- o aserțiune pe el ar verifica un mort."""
    print("\nSELECTIE UAT -- click = filtrare in panou, starea in adresa")
    p.goto(BASE, wait_until="networkidle")
    p.wait_for_selector("#county-picker button", timeout=15000)
    p.wait_for_timeout(200)
    # Intra intr-un judet prin picker: cale garantata, nu tap precis pe harta.
    p.click("#county-picker button")
    try:
        p.wait_for_selector("#county-picker button[data-uat]", timeout=5000)
    except Exception:
        skip("judetul intrat nu a primit lista de UAT-uri in 5s -- nu se poate testa selectia")
        reset(p)
        return
    p.wait_for_timeout(200)
    before = panel_count(p)

    p.click("#county-picker button[data-uat]")
    p.wait_for_timeout(350)
    url = p.evaluate("() => location.search")
    check("uat=" in url, f"selectia de UAT ajunge in adresa ('{url}')")
    check("judet=" in url, f"adresa pastreaza si județul ('{url}')")
    after = panel_count(p)
    check(after != before, f"panoul filtreaza la selectia de UAT ('{before}' -> '{after}')")
    pressed = p.evaluate(
        "() => document.querySelector('#county-picker button[data-uat][aria-pressed=\"true\"]')?.textContent || ''")
    check(bool(pressed), f"butonul UAT selectat primeste aria-pressed ('{pressed}')")

    # Click repetat pe acelasi UAT deselecteaza (toggle, ca aria-pressed sa minta pe nimeni).
    p.click("#county-picker button[data-uat]")
    p.wait_for_timeout(300)
    check("uat=" not in p.evaluate("() => location.search"),
          f"clickul repetat deselecteaza ('{p.evaluate('() => location.search')}')")
    check(panel_count(p) == before, f"panoul revine la lista judetului ('{panel_count(p)}' vs '{before}')")

    # Back, de la selectie activa, anuleaza selectia in loc sa iasa de pe pagina.
    p.click("#county-picker button[data-uat]")
    p.wait_for_timeout(350)
    opened_url = p.evaluate("() => location.search")
    check("uat=" in opened_url, "selectia s-a refacut pentru testul Back")
    p.go_back()
    p.wait_for_timeout(350)
    check("uat=" not in p.evaluate("() => location.search"),
          f"Back anuleaza selectia de UAT ('{p.evaluate('() => location.search')}')")

    # Link direct: cine prinde adresa cu uat= vede UAT-ul deja selectat, fara niciun click.
    p.goto(BASE + opened_url, wait_until="networkidle")
    try:
        p.wait_for_selector("#county-picker button[data-uat][aria-pressed=\"true\"]", timeout=8000)
    except Exception:
        skip(f"linkul direct '{opened_url}' nu a restabilit selectia in 8s (JSON UAT n-a sosit?)")
    else:
        check("uat=" in p.evaluate("() => location.search"),
              f"link direct ({opened_url}) restabileste selectia")
    p.goto(BASE, wait_until="networkidle")
    p.wait_for_selector("#news-list li", timeout=15000)


def context_national_si_nume_uat(p):
    """Selectia la nivel judetean pastreaza harta nationala si vecinii neestompati;
    la zoom local, toate UAT-urile raman in selector, iar numele vizibile sunt collision-aware."""
    print("\nCONTEXT NATIONAL + NUME UAT -- vecini vizibili, lista completa, etichete fara coliziuni")
    p.goto(BASE + "?nivel=judetean&judet=TIMIS", wait_until="networkidle")
    p.wait_for_selector("#map svg.map-svg .layer-counties path[data-judet='TIMIS']", timeout=15000)
    national = p.evaluate("""async () => {
      const svg = document.querySelector('#map svg.map-svg');
      const data = await (await fetch('/static/harta-stiri/data/map.json')).json();
      const expected = data.map.viewbox.trim().split(/\s+/).map(Number);
      const actual = svg.getAttribute('viewBox').trim().split(/\s+/).map(Number);
      const counties = [...svg.querySelectorAll('.layer-counties path')];
      const neighbors = counties.filter((n) => n.dataset.judet !== 'TIMIS');
      return {
        fullFrame: actual.length === 4 && actual.every((v, i) => Math.abs(v - expected[i]) < 0.02),
        selected: counties.some((n) => n.dataset.judet === 'TIMIS' && n.classList.contains('is-selected')),
        neighbors: neighbors.length,
        dimmed: neighbors.filter((n) => getComputedStyle(n).opacity !== '1').length,
      };
    }""")
    check(national["fullFrame"] and national["selected"],
          f"nivelul județean păstrează cadrul național cu TIMIȘ selectat ({national})")
    check(national["neighbors"] > 0 and national["dimmed"] == 0,
          f"toți vecinii rămân vizibili/neestompați în cadrul național ({national})")

    p.goto(BASE + "?judet=TIMIS", wait_until="networkidle")
    p.wait_for_function("() => document.querySelectorAll('#map svg.map-svg .layer-uats path').length > 0",
                        timeout=15000)
    uats = p.evaluate("""() => {
      const paths = [...document.querySelectorAll('#map svg.map-svg .layer-uats path')];
      const buttons = [...document.querySelectorAll('#county-picker button[data-uat]')];
      const names = [...document.querySelectorAll('#map svg.map-svg .label-name')]
        .map((n) => n.textContent.trim()).filter(Boolean);
      const pickerNames = new Set(buttons.map((b) => b.textContent.split(' · ')[0].trim()));
      const boxes = [...document.querySelectorAll('#map svg.map-svg .map-label.label-uat')]
        .map((n) => n.getBoundingClientRect());
      let overlaps = 0;
      for (let i = 0; i < boxes.length; i += 1) {
        for (let j = i + 1; j < boxes.length; j += 1) {
          const dx = Math.min(boxes[i].right, boxes[j].right) - Math.max(boxes[i].left, boxes[j].left);
          const dy = Math.min(boxes[i].bottom, boxes[j].bottom) - Math.max(boxes[i].top, boxes[j].top);
          if (dx > 2 && dy > 2) overlaps += 1;
        }
      }
      return {
        paths: paths.length,
        buttons: buttons.length,
        names,
        matchedNames: names.filter((name) => pickerNames.has(name)).length,
        overlaps,
      };
    }""")
    check(uats["paths"] > 0 and uats["buttons"] == uats["paths"],
          f"selectorul oferă toate UAT-urile geometrice, inclusiv cele cu 0 rezultate ({uats['buttons']}/{uats['paths']})")
    check(uats["matchedNames"] > 0 and uats["overlaps"] == 0,
          f"etichetele UAT vizibile se potrivesc cu pickerul și nu se suprapun (nume={uats['matchedNames']}/{len(uats['names'])}, coliziuni={uats['overlaps']})")
    p.goto(BASE, wait_until="networkidle")


def nume_uat_mobil(p):
    """La 390px, zoomul local păstrează textul real pentru etichetele care trec culling-ul;
    numele ascunse prin coliziune rămân în selectorul complet."""
    print("\nNUME UAT PE MOBIL -- etichete SVG cu culling, selector accesibil")
    p.goto(BASE + "?judet=TIMIS", wait_until="networkidle")
    p.wait_for_function("() => document.querySelectorAll('#map svg.map-svg .layer-uats path').length > 0",
                        timeout=15000)
    p.wait_for_timeout(100)
    uats = p.evaluate("""() => {
      const names = [...document.querySelectorAll('#map svg.map-svg .label-name')]
        .map((n) => n.textContent.trim()).filter(Boolean);
      const buttons = [...document.querySelectorAll('#county-picker button[data-uat]')];
      const pickerNames = new Set(buttons.map((b) => b.textContent.split(' · ')[0].trim()));
      const boxes = [...document.querySelectorAll('#map svg.map-svg .map-label.label-uat')]
        .map((n) => n.getBoundingClientRect());
      let overlaps = 0;
      for (let i = 0; i < boxes.length; i += 1) {
        for (let j = i + 1; j < boxes.length; j += 1) {
          const dx = Math.min(boxes[i].right, boxes[j].right) - Math.max(boxes[i].left, boxes[j].left);
          const dy = Math.min(boxes[i].bottom, boxes[j].bottom) - Math.max(boxes[i].top, boxes[j].top);
          if (dx > 2 && dy > 2) overlaps += 1;
        }
      }
      return { visible: names.length, matched: names.filter((name) => pickerNames.has(name)).length,
               picker: buttons.length, overlaps };
    }""")
    check(uats["visible"] > 0 and uats["matched"] > 0 and uats["overlaps"] == 0,
          f"pe mobil apar nume UAT SVG fără coliziuni și corespondente în lista completă ({uats})")
    p.goto(BASE, wait_until="networkidle")


def breadcrumb(p):
    """Firul ierarhic (NN/g 'Breadcrumbs': pozitie in IERARHIE, nu istoric; nivelul curent e
    text simplu, nu link; toti stramosii clickabili) + limbaj de utilizator, nu jargon
    administrativ, in etichetele vizibile."""
    print("\nBREADCRUMB -- ierarhie vizibila, parinti clickabili, fara jargon")
    p.goto(BASE, wait_until="networkidle")
    p.wait_for_selector("#map-breadcrumb .crumb-current", timeout=15000)
    crumb0 = p.evaluate("() => document.querySelector('#map-breadcrumb .crumb-current')?.textContent?.trim()")
    check(crumb0 == "România", f"la start firul arata România ca pozitie ('{crumb0}')")

    p.click("#county-picker button")
    try:
        p.wait_for_selector("#county-picker button[data-uat]", timeout=5000)
    except Exception:
        skip("judetul intrat nu a primit lista de unitati -- firul partial netestat")
        reset(p)
        return
    county = p.evaluate("() => new URLSearchParams(location.search).get('judet')")
    current1 = p.evaluate("() => document.querySelector('#map-breadcrumb .crumb-current')?.textContent?.trim()")
    buttons1 = p.evaluate("() => [...document.querySelectorAll('#map-breadcrumb button')].map(b => b.textContent.trim())")
    # URL-ul poarta cheia canonica (ALBA), firul eticheta umana (Alba) — comparatie
    # key->label, nu key->key (G3, plan de remediere Arena 6 oct).
    eticheta = county_label(p, county) if county else None
    check(bool(county) and current1 == eticheta and "România" in buttons1,
          f"firul arata traseul: România clickabil, judetul e pozitia curenta (butone={buttons1}, curent='{current1}')")

    p.click("#county-picker button[data-uat]")
    p.wait_for_timeout(350)
    current = p.evaluate("() => document.querySelector('#map-breadcrumb .crumb-current')?.textContent?.trim()")
    check(bool(current) and "România" not in (current or ""),
          f"nivelul curent (unitatea) e text, nu link ('{current}')")
    # Stramosul clickabil duce EXACT la nivelul lui: unitatea dispare, judetul ramane.
    p.evaluate("() => [...document.querySelectorAll('#map-breadcrumb button')].pop().click()")
    p.wait_for_timeout(300)
    search = p.evaluate("() => location.search")
    check("uat=" not in search and "judet=" in search,
          f"click pe nivelul judet din fir anuleaza unitatea, pastreaza judetul ('{search}')")
    # Nivelul curent revine la judet, iar România e din nou buton clickabil.
    current2 = p.evaluate("() => document.querySelector('#map-breadcrumb .crumb-current')?.textContent?.trim()")
    check(current2 == county_label(p, county),
          f"firul revine pe judet ca pozitie curenta ('{current2}')")
    # Limbaj de utilizator in etichete, nu jargon administrativ (audit harta, P2).
    picker_label = p.evaluate("() => document.querySelector('#county-picker')?.getAttribute('aria-label') || ''")
    check("UAT" not in picker_label, f"eticheta selectorului nu mai foloseste jargonul ('{picker_label}')")
    reset(p)
    p.wait_for_timeout(150)


def gold_pixels(p):
    """Aria VIZIBILA a hartii in pixeli patrati de ecran + centroidul ei -- inlocuieste
    numaratoarea de px² de harta din era canvas. Se insumeaza cutiile judetelor proiectate in
    spatiul ecranului, limitate la fereastra scenei: la zoom aceleasi forme ocupa mai mult, la
    pan centrul de masa se muta. Exact ce masura inainte numaratoarea de pixeli, dar fara
    dependenta de nuanta (garda de culoare e `tools/harta_contrast.py`)."""
    return p.evaluate("""() => {
      const svg = document.querySelector('#map svg.map-svg');
      const r = svg.getBoundingClientRect();
      const ctm = svg.getScreenCTM();
      if (!ctm) return { n: 0, cx: 0, cy: 0 };
      let n = 0, sx = 0, sy = 0;
      for (const node of svg.querySelectorAll('.layer-counties path')) {
        const b = node.getBBox();
        if (!b.width || !b.height) continue;
        const a = new DOMPoint(b.x, b.y).matrixTransform(ctm);
        const c = new DOMPoint(b.x + b.width, b.y + b.height).matrixTransform(ctm);
        const x0 = Math.max(Math.min(a.x, c.x), r.left), x1 = Math.min(Math.max(a.x, c.x), r.right);
        const y0 = Math.max(Math.min(a.y, c.y), r.top), y1 = Math.min(Math.max(a.y, c.y), r.bottom);
        const w = Math.max(0, x1 - x0), h = Math.max(0, y1 - y0);
        if (!w || !h) continue;
        const area = w * h;
        n += area;
        sx += area * (x0 + w / 2);
        sy += area * (y0 + h / 2);
      }
      if (!n) return { n: 0, cx: 0, cy: 0 };
      return { n: Math.round(n / 1000), cx: sx / n, cy: sy / n };
    }""")


def zoom_interactiv(p):
    """Zoom/pan pe hartă (cerere proprietar 5 sep 2026: „nu se poate face niciun fel de zoom,
    e penibil"). Verifica: rotita mareste, dublu-click mareste, butoanele +/− si reset,
    starea dezactivata expusa, pan-ul prin tragere la zoom, fara selectie accidentala."""
    print("\nZOOM/PAN -- harta interactiva")
    r = stage_rect(p)
    cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
    p.wait_for_function("() => document.querySelector('#news-list li a') !== null", timeout=15000)
    before = gold_pixels(p)

    # (a) rotita mareste
    p.mouse.move(cx, cy)
    p.mouse.wheel(0, -480)
    p.wait_for_timeout(300)
    zoomed = gold_pixels(p)
    check(zoomed["n"] >= before["n"] * 1.5,
          f"rotita mareste harta ({before['n']} -> {zoomed['n']} px² de harta)")

    # (b) pan prin tragere misca vederea (viewBox), fara sa selecteze nimic. La zoom aproape
    # de 1:1 clamp-ul limiteaza legal deplasarea, deci masuram viewBox (unitati hartă), nu
    # pixeli de ecran cu fereastra de zgomot — garda veche astepta 15-95px indiferent de
    # zoom (G1, plan de remediere Arena 6 oct).
    vb0 = _vb(p)
    p.mouse.move(cx, cy)
    p.mouse.down()
    p.mouse.move(cx - 48, cy - 24, steps=6)
    p.mouse.up()
    p.wait_for_timeout(300)
    vb1 = _vb(p)
    misca = abs(vb1[0] - vb0[0]) + abs(vb1[1] - vb0[1])
    check(misca > 0.5,
          f"pan-ul misca vederea la zoom (viewBox x+y mutat cu {misca:.1f} unitati la drag)")
    check(not county_selected(p), "pan-ul prin tragere NU selecteaza un judet")

    # (c) butonul reset revine la scara de baza
    check(p.evaluate("() => !document.querySelector('.map-zoom button[aria-label=\"Resetează zoom-ul hărții\"]').hidden"),
          "butonul de reset zoom apare cand harta e marita")
    p.click(".map-zoom button[aria-label=\"Resetează zoom-ul hărții\"]")
    p.wait_for_timeout(300)
    reset_zoom = gold_pixels(p)
    check(abs(reset_zoom["n"] - before["n"]) <= before["n"] * 0.25,
          f"resetul revine la scara de baza ({zoomed['n']} -> {reset_zoom['n']} vs {before['n']})")
    check(p.evaluate("() => document.querySelector('.map-zoom button[aria-label=\"Resetează zoom-ul hărții\"]').hidden"),
          "resetul dispare la scara 1:1")

    # (d) dublu-click mareste; butonul minus scade. Masura: latimea viewBox-ului —
    # gold_pixels artefacteaza la zoom extrem (barele judetelor ies/limiteaza la fereastra
    # scenei), viewBox-ul e metrica obiectiva (G2, plan de remediere Arena 6 oct).
    w0 = _vb(p)[2]
    # felia 2 #448: dublu-clickul pe harta nationala nu mai ajunge la zoom -- primul click
    # angajeaza ruta judetului, deci masuram marirea pe butonul plus (aceeasi intrebare:
    # scena poate fi marita de utilizator).
    p.click(".map-zoom button[aria-label=\"Apropie harta\"]")
    p.wait_for_timeout(300)
    w1 = _vb(p)[2]
    check(w1 < w0 * 0.9, f"butonul plus mareste (viewBox latime {w0:.0f} -> {w1:.0f})")
    p.click(".map-zoom button[aria-label=\"Îndepărtează harta\"]")
    p.wait_for_timeout(300)
    w2 = _vb(p)[2]
    check(w2 > w1 * 1.05, f"butonul minus micsoreaza zoom-ul (viewBox latime {w1:.0f} -> {w2:.0f})")

    # (e) starea dezactivata e expusa programatic: minus la scara 1:1. Dupa pasul plus+minus
    # hartaa poate fi deja la scara 1:1 (resetul ascuns), deci nu mai clickuim un buton disparut.
    if not p.evaluate("() => document.querySelector('.map-zoom button[aria-label=\"Resetează zoom-ul hărții\"]').hidden"):
        p.click(".map-zoom button[aria-label=\"Resetează zoom-ul hărții\"]")
        p.wait_for_timeout(250)
    out = p.evaluate("""() => {
      const b = document.querySelector('.map-zoom button[aria-label=\"Îndepărtează harta\"]');
      return { disabled: b.disabled, aria: b.getAttribute('aria-disabled') };
    }""")
    check(out["disabled"] and out["aria"] == "true",
          f"butonul minus e dezactivat la scara 1:1 (disabled={out['disabled']}, aria={out['aria']})")

    # (f) la zoom, clickul inca selecteaza judetul corect (hit-test prin transformare)
    p.mouse.move(cx, cy)
    p.mouse.wheel(0, -720)
    p.wait_for_timeout(300)
    p.mouse.click(cx, cy)
    p.wait_for_timeout(250)
    check(county_selected(p), "clickul la harta marita selecteaza judetul de sub cursor")
    reset(p)
    p.wait_for_timeout(150)


def tastatura_pan_zoom(p):
    """Pan/zoom si din TASTATURA (ghidurile de harti accesibile cer zoom+pan pe toate
    input-urile): +/- schimba scara (anuntate in regiunea aria-live), sagețile deplaseaza
    vederea. Deplasarea se verifica COMPORTAMENTAL: sub acelasi cursor, dupa pan, apare o
    ALTA zona -- centroidul de pixeli e o metrica slaba la zoom, pentru ca zone aurii care
    ies din cadru sunt inlocuite de altele si centrul de masa ramane aproape fix (masurat)."""
    print("\nTASTATURA -- pan cu sagețile, zoom cu +/-, anunt aria-live")
    plus = p.locator('.map-zoom button[aria-label="Apropie harta"]')
    plus.focus()
    plus.click()
    plus.click()
    p.wait_for_timeout(300)
    status = p.evaluate("() => document.querySelector('#map-status')?.textContent || ''")
    check("mărită" in status, f"schimbarea de scara e anuntata aria-live ('{status}')")

    # Punct interior intr-un judet (oricare cu stiri), in coordonate de ecran.
    pt = interior_point(p, "news")
    if not pt:
        skip("nu am gasit punct interior pentru testul de pan din tastatura")
        return
    p.mouse.move(pt["x"], pt["y"], steps=2)
    p.wait_for_timeout(200)
    tip_before = p.evaluate("() => document.querySelector('.map-tip')?.textContent || ''")
    label_pt = county_label(p, pt["county"])
    check(label_pt in tip_before,
          f"cursorul porneste peste {label_pt} (tooltip: '{tip_before}')")

    # Sageata dreapta = vederea spre est; 6 apasari x ~39 unitati ≈ 232 -- mai mult decat
    # latimea oricarui judet, deci sub cursor NU poate ramane aceeasi zona.
    p.keyboard.press("ArrowRight")
    for _ in range(5):
        p.keyboard.press("ArrowRight")
        p.wait_for_timeout(100)
    p.wait_for_timeout(350)
    p.mouse.move(pt["x"], pt["y"], steps=2)
    p.wait_for_timeout(250)
    tip_after = p.evaluate("() => document.querySelector('.map-tip')?.textContent || ''")
    check(tip_after != tip_before,
          f"dupa sageți sub acelasi cursor a ajuns o alta zona ('{tip_before}' -> '{tip_after or 'fara tooltip'}')")

    minus = p.locator('.map-zoom button[aria-label="Îndepărtează harta"]')
    minus.focus()
    for _ in range(5):
        p.keyboard.press("-")
        p.wait_for_timeout(120)
    p.wait_for_timeout(250)
    status2 = p.evaluate("() => document.querySelector('#map-status')?.textContent || ''")
    check("normală" in status2, f"revenirea la scara 1:1 e anuntata ('{status2}')")
    reset(p)
    p.wait_for_timeout(150)


def mobil_390(p):
    """Android: la 390px verificăm overflow-ul, țintele de 24px și tap-vs-drag tactil."""
    print("\nMOBIL 390px (Android emulat) -- zona de atins si garda de derulare")
    p.wait_for_function("() => document.querySelector('#news-list li a') !== null", timeout=15000)
    over = p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check(over <= 0, f"fara overflow orizontal la 390px ({over}px)")

    p.locator("#map svg.map-svg").scroll_into_view_if_needed()
    p.wait_for_timeout(150)
    r = stage_rect(p)
    print(f"   scena reala: {r['w']:.0f}x{r['h']:.0f}px")
    targets = county_route_targets(p)
    mici = [t for t in targets if t.get("width", 0) < 24 or t.get("height", 0) < 24]
    check(len(targets) == 42 and not mici,
          "toate cele 42 de ținte tactile rămân >=24px pe 390px" if not mici
          else f"ținte mobile sub 24px: {[(t['county'], round(t.get('width', 0), 1), round(t.get('height', 0), 1)) for t in mici[:5]]}")

    buc = next((t for t in targets if t["county"] == "BUCURESTI"), targets[0] if targets else None)
    if not buc:
        skip("tap mobil pe județ: nu există ținte de județ")
    else:
        with p.expect_navigation(wait_until="networkidle", timeout=8000) as nav:
            p.touchscreen.tap(buc["x"], buc["y"])
        response = nav.value
        path = p.evaluate("() => location.pathname")
        check(path == buc["href"] and response and response.status == 200,
              f"tap pe ținta mobilă {buc['county']} -> {path} (status {response.status if response else 'fără răspuns'})")

    goto_base(p)
    p.locator("#map svg.map-svg").scroll_into_view_if_needed()
    p.wait_for_timeout(150)
    r = stage_rect(p)
    before = p.evaluate("() => location.pathname")
    # Derulare peste harta cu DEGETUL. `page.mouse` ar produce evenimente de mouse chiar si pe o
    # pagina cu has_touch -- adica ar retesta desktopul si ar raporta verde pentru telefon.
    swipe_touch(p, r["x"] + r["w"] / 2, r["y"] + r["h"] / 2, dy=-140)
    p.wait_for_timeout(250)
    check(p.evaluate("() => location.pathname") == before,
          "derularea cu degetul peste harta NU deschide ruta unui județ")

def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(args=["--no-sandbox"])
        p = br.new_page(viewport={"width": 1280, "height": 1200})
        p.goto(BASE, wait_until="networkidle")
        p.wait_for_selector("#news-list li", timeout=15000)
        felia1_lista(p)
        felia7_cautare(p)
        felia4_hittest(p)
        # felia 2 #448: clickul pe poligon angajează ruta județului, deci orice secțiune care
        # clipează harta poate schimba documentul. Fiecare secțiune pornește deci de pe harta
        # națională; navigarea intenționată (felia 2, click_zona) are goto_base propriu la final.
        for sec in (hit_ordin_fara_furt, ilfov_click_geometric, hover_preview, click_zona_fara_stiri, scara_si_numitor,
                    felia2_localitate, felia5_county_picker, felia6_url, zoom_interactiv,
                    tastatura_pan_zoom, uat_selectie, context_national_si_nume_uat,
                    breadcrumb):
            goto_base(p)
            sec(p)

        mob = br.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mob.goto(BASE, wait_until="networkidle")
        mob.wait_for_selector("#news-list li", timeout=15000)
        mobil_390(mob)
        nume_uat_mobil(mob)
        br.close()
    print("")
    if fails:
        print("FAIL:")
        for f in fails:
            print(" -", f)
    if skipped:
        print("NEVERIFICAT (nu se raporteaza ca reusita):")
        for s in skipped:
            print(" -", s)
    if fails:
        return 1
    print("OK" + (" (cu verificari neefectuate, vezi mai sus)" if skipped else ""))
    return 0

if __name__ == "__main__":
    import sys
    # Windows: cp1252 nu are „ș"/„ț", deci un `print` cu diacritice arunca
    # UnicodeEncodeError si scriptul iese cu 1 — indistingibil de un esec real de
    # continut. Masurat 2026-08-20: `qa_check.py` iesea cu 1 pe date valide, iar cu
    # PYTHONIOENCODING=utf-8 cu 0. In CI (Linux, UTF-8) nu se vede. Acelasi idiom ca
    # in `scan_homepages.py`, extins la toate punctele de intrare cu diacritice.
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
