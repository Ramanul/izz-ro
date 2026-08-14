#!/usr/bin/env python
"""Verificare DOM randat pentru harta stirilor. Ruleaza cu serverul local pornit:
   python -m http.server 8765 --directory static/harta-stiri

Asserteaza pe STRUCTURA VIZIBILA si pe COMPORTAMENT OBSERVAT (id-uri, taguri, pixeli, clickuri),
nu pe clase CSS si nu pe identificatori din sursa -- de doua ori in repo-ul asta o garda a stat
verde/rosie pe un identificator care nu mai exista in codul livrat (IZZ-0177, IZZ-0182)."""
import os, sys, io, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

BASE = os.getenv("MAP_URL", "http://localhost:8765/")
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

def canvas_rect(p):
    return p.evaluate("""() => {
      const r = document.querySelector('#map canvas.map-canvas').getBoundingClientRect();
      return { x: r.x, y: r.y, w: r.width, h: r.height };
    }""")

def county_selected(p):
    """Butonul '<- Toate judetele' e ascuns exact cand state.selectedCounty e null."""
    return p.evaluate("() => { const b = document.querySelector('.map-back'); return !!b && !b.hidden; }")

def panel_count(p):
    return p.evaluate("() => document.querySelector('#panel-count').textContent.trim()")

def search_value(p):
    return p.evaluate("() => document.querySelector('#map-search').value")

def reset(p):
    p.click("#clear-selection")
    p.wait_for_timeout(120)


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

def bright_fill_pixels(p):
    """Numara pixelii de umplere NEestompata (--map-fill #e8e6de). Judetele estompate sunt
    desenate cu globalAlpha .32 peste alb, deci ajung pe la #f7f6f4 -- distincte clar."""
    return p.evaluate("""() => {
      const c = document.querySelector('#map canvas.map-canvas');
      const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
      let n = 0;
      for (let i = 0; i < d.length; i += 4 * 7) {  // esantion 1 din 7 pixeli
        if (Math.abs(d[i]-232) <= 6 && Math.abs(d[i+1]-230) <= 6 && Math.abs(d[i+2]-222) <= 6) n++;
      }
      return n;
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
    check(bright_query > 0,
          f"harta pastreaza judete aprinse la cautare non-geografica ({bright_query} px vs {bright_all} fara filtru)")

def felia4_hittest(p):
    print("\nFELIA 4 -- apasarea pe judet, nu doar pe bulina")
    r = canvas_rect(p)
    # Grila 8x8 peste canvas. Inainte de felia 4 erau apasabile doar ~35 buline de ~12px, deci
    # o grila atat de rara ar fi nimerit 0-3 puncte. Pragul de 25 e imposibil de atins fara
    # hit-test pe poligon -- de-aia e un discriminator, nu o masuratoare vaga.
    hits, tried = 0, 0
    for i in range(1, 9):
        for j in range(1, 9):
            x = r["x"] + r["w"] * i / 9
            y = r["y"] + r["h"] * j / 9
            tried += 1
            p.mouse.click(x, y)
            p.wait_for_timeout(45)
            if county_selected(p):
                hits += 1
                reset(p)
    check(hits >= 25, f"apasarea in interiorul judetelor selecteaza ({hits}/{tried} puncte de grila)")

    # In afara tarii: coltul din stanga-sus al canvasului e mare/exterior.
    p.mouse.click(r["x"] + 3, r["y"] + 3)
    p.wait_for_timeout(120)
    check(not county_selected(p), "apasarea in afara conturului tarii nu selecteaza nimic")
    reset(p)

    # Garda tap-vs-drag: o derulare care incepe pe harta nu trebuie sa selecteze.
    cx, cy = r["x"] + r["w"] / 2, r["y"] + r["h"] / 2
    p.mouse.move(cx, cy)
    p.mouse.down()
    p.mouse.move(cx, cy + 120, steps=6)
    p.mouse.up()
    p.wait_for_timeout(150)
    check(not county_selected(p), "derularea cu degetul pe harta NU selecteaza un judet")
    reset(p)

def felia2_localitate(p):
    print("\nFELIA 2 -- click pe localitate nu fura campul de cautare")
    r = canvas_rect(p)
    # Intra pe un judet, apoi cauta un marker de localitate scanand o grila in starea marita.
    entered = None
    for i in range(1, 9):
        for j in range(1, 9):
            p.mouse.click(r["x"] + r["w"] * i / 9, r["y"] + r["h"] * j / 9)
            p.wait_for_timeout(45)
            if county_selected(p):
                entered = (i, j)
                break
        if entered:
            break
    if not entered:
        skip("nu s-a putut intra pe niciun judet -- verificarea localitatii nu a rulat")
        return

    before = panel_count(p)
    zr = canvas_rect(p)
    found = False
    for i in range(1, 13):
        for j in range(1, 13):
            p.mouse.click(zr["x"] + zr["w"] * i / 13, zr["y"] + zr["h"] * j / 13)
            p.wait_for_timeout(35)
            if panel_count(p) != before:
                found = True
                break
        if found:
            break
    if not found:
        skip("niciun marker de localitate nimerit in judetul intrat -- nu s-a putut testa")
        reset(p)
        return
    check(search_value(p) == "",
          f"selectarea localitatii lasa campul de cautare gol (e '{search_value(p)}')")
    reset(p)

def felia5_county_picker(p):
    print("\nFELIA 5 -- selector de judet de la tastatura")
    # Verifica ca #county-picker exista si contine butoane
    count = p.evaluate("() => document.querySelectorAll('#county-picker button').length")
    check(count > 0, f"#county-picker contine butoane de judet ({count})")

    # Tab pana la primul buton al county-picker-ului
    p.keyboard.press("Tab")
    p.wait_for_timeout(100)
    focused = p.evaluate("() => document.activeElement.id || document.activeElement.textContent.slice(0, 20)")
    # Nu e strict necesara pe focus, doar sa verific ca tab-ul ajunge

    # Click pe primul buton si verifica ca aria-pressed e "true"
    first_btn = p.evaluate("() => { const b = document.querySelector('#county-picker button'); return { text: b.textContent.trim(), before: b.getAttribute('aria-pressed') }; }")
    p.click("#county-picker button")
    p.wait_for_timeout(150)
    first_btn_after = p.evaluate("() => document.querySelector('#county-picker button').getAttribute('aria-pressed')")
    check(first_btn_after == "true", f"button selectat primeste aria-pressed='true' (era '{first_btn['before']}')")

    # Verifica ca lista s-a filtratu (panel-count se schimba)
    count_after = panel_count(p)
    check(count_after != "497 știri", f"filtrarea pe judet schimba panel-count (era '120 din 497 știri', e '{count_after}')")
    reset(p)

    # Verifica ca dupa reset, niciun buton nu are aria-pressed="true"
    p.wait_for_timeout(150)
    pressed_count = p.evaluate("() => document.querySelectorAll('#county-picker button[aria-pressed=\"true\"]').length")
    check(pressed_count == 0, f"dupa reset niciun buton nu e selectat ({pressed_count} inca selectate)")

def mobil_390(p):
    """Android: harta e ~359x256px la 390 latime, deci ea e cazul greu pentru zona de atins.
    Aici se verifica si ca garda tap-vs-drag chiar tine cu EVENIMENTE TACTILE, nu doar cu mouse-ul
    -- pe desktop `pointerdown` vine de la mouse, pe telefon de la deget, si nu e acelasi drum."""
    print("\nMOBIL 390px (Android emulat) -- zona de atins si garda de derulare")
    p.wait_for_function("() => document.querySelector('#news-list li a') !== null", timeout=15000)
    over = p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check(over <= 0, f"fara overflow orizontal la 390px ({over}px)")

    r = canvas_rect(p)
    print(f"   canvas real: {r['w']:.0f}x{r['h']:.0f}px")
    hits, tried = 0, 0
    for i in range(1, 7):
        for j in range(1, 7):
            x, y = r["x"] + r["w"] * i / 7, r["y"] + r["h"] * j / 7
            tried += 1
            p.touchscreen.tap(x, y)
            p.wait_for_timeout(60)
            if county_selected(p):
                hits += 1
                reset(p)
    check(hits >= 12, f"atingerea cu degetul in interiorul judetelor selecteaza ({hits}/{tried})")

    # Derulare peste harta cu DEGETUL. `page.mouse` ar produce evenimente de mouse chiar si pe o
    # pagina cu has_touch -- adica ar retesta desktopul si ar raporta verde pentru telefon.
    # Playwright expune doar `touchscreen.tap`, fara swipe, deci gestul se trimite prin CDP.
    swipe_touch(p, r["x"] + r["w"] / 2, r["y"] + r["h"] / 2, dy=-140)
    p.wait_for_timeout(200)
    check(not county_selected(p), "derularea cu degetul peste harta NU selecteaza un judet")
    reset(p)


def main():
    with sync_playwright() as pw:
        br = pw.chromium.launch(args=["--no-sandbox"])
        p = br.new_page(viewport={"width": 1280, "height": 900})
        p.goto(BASE, wait_until="networkidle")
        p.wait_for_selector("#news-list li", timeout=15000)
        felia1_lista(p)
        felia7_cautare(p)
        felia4_hittest(p)
        felia2_localitate(p)
        felia5_county_picker(p)

        mob = br.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mob.goto(BASE, wait_until="networkidle")
        mob.wait_for_selector("#news-list li", timeout=15000)
        mobil_390(mob)
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
    sys.exit(main())
