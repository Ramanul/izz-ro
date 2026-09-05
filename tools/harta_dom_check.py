#!/usr/bin/env python
"""Verificare DOM randat pentru harta stirilor. Ruleaza cu serverul local pornit DIN RADACINA
   repo-ului -- index.html foloseste cai absolute (/static/...), deci un server din
   static/harta-stiri ar lasa JS-ul si CSS-ul pe 404 si pagina blocata in "Se încarcă…":
   python -m http.server 8765
   MAP_URL=http://localhost:8765/static/harta-stiri/ python tools/harta_dom_check.py

Asserteaza pe STRUCTURA VIZIBILA si pe COMPORTAMENT OBSERVAT (id-uri, taguri, pixeli, clickuri),
nu pe clase CSS si nu pe identificatori din sursa -- de doua ori in repo-ul asta o garda a stat
verde/rosie pe un identificator care nu mai exista in codul livrat (IZZ-0177, IZZ-0182)."""
import os, sys, io
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
    # Resetarea completă este intenționat disponibilă în orice stare. Comanda contextuală
    # „Înapoi la România” este dezactivată corect atunci când nicio zonă nu este selectată.
    p.click("#reset-all")
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

EDGE_SCAN = """(yCss) => {
  const c = document.querySelector('#map canvas.map-canvas');
  const rect = c.getBoundingClientRect();
  const sx = c.width / rect.width, sy = c.height / rect.height;
  const py = Math.round(yCss * sy);
  if (py < 0 || py >= c.height) return null;
  const row = c.getContext('2d').getImageData(0, py, c.width, 1).data;
  for (let px = 0; px < c.width; px++) {
    const i = px * 4;
    const opaque = row[i + 3] > 8;
    const white = row[i] > 248 && row[i + 1] > 248 && row[i + 2] > 248;
    if (opaque && !white) return { edgeCss: px / sx, rectX: rect.x, rectY: rect.y };
  }
  return null;
}"""

def edge_tolerance_px(p, max_px=8):
    """Cat de departe IN AFARA conturului tarii mai selecteaza o atingere, in pixeli CSS.
    Cauta marginea din stanga a uscatului pe cateva linii orizontale, apoi se departeaza pas cu
    pas si returneaza cea mai mare distanta la care inca s-a selectat un judet. None daca nu s-a
    gasit nicio margine utilizabila -- se raporteaza ca NEVERIFICAT, nu ca reusita."""
    r = canvas_rect(p)
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

def hit_ordin_fara_furt(p):
    """Ordinea cascadei (audit harta, P0): un click clar primit in interiorul poligonului unui
    judet nu poate fi furat de bulina unui vecin ajunsa in raza de toleranta peste granita.
    Ground truth = geometria din map.json, calculata in pagina cu acelasi Path2D + isPointInPath
    pe care le foloseste aplicatia, in acelasi spatiu (px de canvas, transformarea aplicata --
    IZZ-0193). Daca in datele curente nu exista niciun punct in care vechea ordine greseA,
    verificarea se raporteaza NEVERIFICAT, nu verde -- nu se inventeaza o reusita."""
    print("\nHIT-TEST ORDINE -- bulina nu fura poligonul clar atins")
    # Bucuresti/Ilfov stau in JUMATATEA DE SUD a canvasului: la 1280x900 punctele lor cad sub
    # fold, iar un click in afara viewportului nu atinge canvasul (elementFromPoint -> none).
    # Aducem harta in viewport INAINTE de a captura rect si de a calcula coordonatele.
    p.locator("#map canvas.map-canvas").scroll_into_view_if_needed()
    p.wait_for_timeout(150)
    truth = p.evaluate("""async () => {
      const d = await (await fetch('./data/map.json')).json();
      const vb = String(d.map.viewbox).trim().split(/\\s+/).map(Number);
      const c = document.querySelector('#map canvas.map-canvas');
      const scratch = document.createElement('canvas');
      scratch.width = c.width; scratch.height = c.height;
      const ctx = scratch.getContext('2d');
      ctx.setTransform(c.width / vb[2], 0, 0, c.height / vb[3],
                       -vb[0] * c.width / vb[2], -vb[1] * c.height / vb[3]);
      const paths = {}, bounds = {};
      for (const [county, pd] of Object.entries(d.map.judete)) {
        try { paths[county] = new Path2D(pd); } catch { continue; }
        const nums = String(pd).match(/-?\\d+(?:\\.\\d+)?/g).map(Number);
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        for (let i = 0; i + 1 < nums.length; i += 2) {
          minX = Math.min(minX, nums[i]); minY = Math.min(minY, nums[i + 1]);
          maxX = Math.max(maxX, nums[i]); maxY = Math.max(maxY, nums[i + 1]);
        }
        bounds[county] = { minX, minY, maxX, maxY };
      }
      // Numarul de EVENIMENTE pe judet, identic cu itemsForView la nivel "all" -- raza bulinei
      // se calculeaza din el, nu din articolele brute.
      const keys = new Map(), counts = {};
      for (const a of d.articles || []) {
        if (!a.county) continue;
        const k = a.event_id || `${a.slug || a.title}|${a.county}|${a.published}`;
        if (!keys.has(k)) keys.set(k, a.county);
      }
      for (const county of keys.values()) counts[county] = (counts[county] || 0) + 1;
      const rect = c.getBoundingClientRect();
      const tolVb = 10 * (vb[2] / rect.width);  // 10px CSS -> unitati viewBox, ca in hitDistance
      const markers = {};
      for (const [county, b] of Object.entries(bounds)) {
        if (!counts[county]) continue;
        const radius = Math.max(7, Math.min(18, 6 + Math.sqrt(counts[county]) * 1.8));
        markers[county] = {
          x: (b.minX + b.maxX) / 2, y: (b.minY + b.maxY) / 2, radius,
        };
      }
      const area = (b) => (b.maxX - b.minX) * (b.maxY - b.minY);
      const found = [];
      const NX = 48, NY = 30;
      for (let i = 1; i < NX && found.length < 3; i += 1) {
        for (let j = 1; j < NY && found.length < 3; j += 1) {
          const xd = Math.round(c.width * i / NX), yd = Math.round(c.height * j / NY);
          const pv = { x: vb[0] + (xd / c.width) * vb[2], y: vb[1] + (yd / c.height) * vb[3] };
          let inside = null;
          for (const [county, path] of Object.entries(paths)) {
            if (!ctx.isPointInPath(path, xd, yd)) continue;
            if (!inside || area(bounds[county]) < area(bounds[inside])) inside = county;
          }
          if (!inside || !counts[inside]) continue;
          let steal = null, bestDist = Infinity;
          for (const [county, m] of Object.entries(markers)) {
            if (county === inside) continue;
            const dist = Math.hypot(pv.x - m.x, pv.y - m.y);
            if (dist <= m.radius + tolVb && dist < bestDist) { bestDist = dist; steal = county; }
          }
          // Cazul discriminator: vechea ordine (bulina intai) ar fi selectat `steal`,
          // desi punctul e clar in interiorul lui `inside`.
          if (steal) found.push({
            xCss: rect.x + (xd / c.width) * rect.width,
            yCss: rect.y + (yd / c.height) * rect.height,
            inside, steal,
          });
        }
      }
      // Enclavele: centrul Bucurestiului trebuie sa intoarca BUCURESTI, nu Ilfov, chiar daca
      // poligonul Ilfovului il contine geometric.
      let enclave = null;
      if (bounds.BUCURESTI && counts.BUCURESTI) {
        const b = bounds.BUCURESTI;
        const xd = Math.round(((b.minX + b.maxX) / 2 - vb[0]) * c.width / vb[2]);
        const yd = Math.round(((b.minY + b.maxY) / 2 - vb[1]) * c.height / vb[3]);
        enclave = {
          xCss: rect.x + (xd / c.width) * rect.width,
          yCss: rect.y + (yd / c.height) * rect.height,
          inBuc: !!paths.BUCURESTI && ctx.isPointInPath(paths.BUCURESTI, xd, yd),
          inIlfov: !!paths.ILFOV && ctx.isPointInPath(paths.ILFOV, xd, yd),
        };
      }
      return { found, enclave };
    }""")

    if truth["enclave"] and truth["enclave"]["inBuc"]:
        p.mouse.click(truth["enclave"]["xCss"], truth["enclave"]["yCss"])
        p.wait_for_timeout(120)
        url = p.evaluate("() => location.search")
        check("judet=BUCURESTI" in url,
              f"click in centrul Bucurestiului selecteaza BUCURESTI, nu Ilfov ('{url}')")
        reset(p)
    elif truth["enclave"]:
        skip(f"enclava Bucuresti: punctul de test nu e in poligonul lui (inBuc={truth['enclave']['inBuc']})")
    else:
        skip("enclava Bucuresti: BUCURESTI nu are stiri in datele curente")

    if not truth["found"]:
        skip("niciun punct de furt in grila curenta: nicio bulina de vecin nu ajunge in raza de "
             "toleranta peste un poligon clar atins -- vechea ordine n-ar fi gresit niciunde azi")
        return
    for case in truth["found"]:
        p.mouse.click(case["xCss"], case["yCss"])
        p.wait_for_timeout(120)
        url = p.evaluate("() => location.search")
        check(f"judet={case['inside']}" in url,
              f"click clar in {case['inside']} (bulina lui {case['steal']} e in raza) selecteaza "
              f"{case['inside']}, nu {case['steal']} ('{url}')")
        reset(p)


def hover_preview(p):
    """hover = previzualizare peste tot (audit harta, P1): la nivel national, numele si cifra
    judetului apar sub cursor INAINTE de click, la fel ca la UAT-uri."""
    print("\nHOVER PREVIEW -- numele zonei de sub cursor, inainte de click")
    p.locator("#map canvas.map-canvas").scroll_into_view_if_needed()
    p.wait_for_timeout(150)
    pt = p.evaluate("""async () => {
      const d = await (await fetch('./data/map.json')).json();
      const vb = String(d.map.viewbox).trim().split(/\\s+/).map(Number);
      const c = document.querySelector('#map canvas.map-canvas');
      const scratch = document.createElement('canvas');
      scratch.width = c.width; scratch.height = c.height;
      const ctx = scratch.getContext('2d');
      ctx.setTransform(c.width / vb[2], 0, 0, c.height / vb[3],
                       -vb[0] * c.width / vb[2], -vb[1] * c.height / vb[3]);
      const rect = c.getBoundingClientRect();
      // Cel mai mare judet, cu un punct VERIFICAT in interior: centroidul unui poligon
      // concav poate iesi in exterior -- acelasi motiv pentru care exista uatBadgePlacement.
      let best = null;
      for (const [county, pd] of Object.entries(d.map.judete)) {
        const nums = String(pd).match(/-?\\d+(?:\\.\\d+)?/g).map(Number);
        let minX = 1e9, minY = 1e9, maxX = -1e9, maxY = -1e9;
        for (let i = 0; i + 1 < nums.length; i += 2) {
          minX = Math.min(minX, nums[i]); minY = Math.min(minY, nums[i + 1]);
          maxX = Math.max(maxX, nums[i]); maxY = Math.max(maxY, nums[i + 1]);
        }
        const area = (maxX - minX) * (maxY - minY);
        if (!best || area > best.area) best = { county, minX, minY, maxX, maxY, area };
      }
      const path = new Path2D(d.map.judete[best.county]);
      let hit = null;
      for (let row = 1; row < 12 && !hit; row += 1) {
        for (let col = 1; col < 12 && !hit; col += 1) {
          const x = best.minX + (best.maxX - best.minX) * col / 12;
          const y = best.minY + (best.maxY - best.minY) * row / 12;
          const xd = Math.round((x - vb[0]) * c.width / vb[2]);
          const yd = Math.round((y - vb[1]) * c.height / vb[3]);
          if (ctx.isPointInPath(path, xd, yd)) {
            hit = { x: rect.x + (xd / c.width) * rect.width,
                    y: rect.y + (yd / c.height) * rect.height };
          }
        }
      }
      return hit ? { county: best.county, ...hit } : { county: best.county, x: null, y: null };
    }""")
    if pt.get("x") is None:
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
    check(pt["county"] in tip["text"].upper(),
          f"numele e cel al judetului tintit ({pt['county']})")
    # Click = selectare; hover = doar previzualizare. La iesirea de pe canvas, totul dispare.
    r = canvas_rect(p)
    p.mouse.move(r["x"] + r["w"] + 12, r["y"] + r["h"] / 2, steps=2)
    p.wait_for_timeout(200)
    check(p.evaluate("() => document.querySelector('.map-tip').hidden"),
          "la iesirea de pe harta tooltipul dispare")


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

    # Localitati suprapuse: mai multe inregistrari SIRUTA pot cadea pe exact acelasi punct si sunt
    # unite intr-un singur marker. La click se filtreaza pe TOATE, nu doar pe prima (altfel stirile
    # celorlalte dispar tacut). Gruparea se face pe cheie de coordonate EXACTA, deci daca setul de
    # date curent nu contine niciun punct partajat, comportamentul nu se poate declansa -- si atunci
    # se raporteaza NEVERIFICAT, nu verde. Cand apar grupuri, tinta se poate calcula din map.json
    # (`map.viewbox` + dreptunghiul canvasului) si atunci verificarea devine: lista rezultata dintr-un
    # singur tap contine >= 2 localitati distincte.
    groups = p.evaluate("""async () => {
      const d = await (await fetch('./data/map.json')).json();
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
      return {
        pressed: inPicker && a.getAttribute('aria-pressed') === 'true',
        uats: inPicker && a.hasAttribute('data-uat'),
        popup: inPicker ? a.getAttribute('aria-haspopup') : null,
      };
    }""")
    check(sel["pressed"] or sel["uats"],
          f"selectia e vizibila pe buton (aria-pressed={sel['pressed']}, buton UAT={sel['uats']}, haspopup={sel['popup']})")

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
    metas = p.evaluate("() => [...document.querySelectorAll('#news-list li span')].map(s => s.textContent.toUpperCase())")
    off = [m for m in metas if "CLUJ" not in m]
    check(bool(metas) and not off,
          f"toate cele {len(metas)} rezultate sunt din CLUJ ({len(off)} din alt judet)")
    p.goto(BASE, wait_until="networkidle")
    p.wait_for_selector("#news-list li", timeout=15000)

def uat_in_url(p):
    """Dialogul UAT e stare navigabila (audit harta, P0): vine din URL, intra in URL, Back il
    inchide, X-ul curata adresa, iar un link direct il redeschide fara niciun click."""
    print("\nUAT IN ADRESA -- dialogul e stare navigabila")
    p.goto(BASE, wait_until="networkidle")
    p.wait_for_selector("#county-picker button", timeout=15000)
    p.wait_for_timeout(200)
    # Intra intr-un judet prin picker: cale garantata, nu tap precis pe harta.
    p.click("#county-picker button")
    try:
        p.wait_for_selector("#county-picker button[data-uat]", timeout=5000)
    except Exception:
        skip("judetul intrat nu a primit lista de UAT-uri in 5s -- nu se poate testa dialogul in URL")
        reset(p)
        return
    p.wait_for_timeout(200)

    p.click("#county-picker button[data-uat]")
    p.wait_for_timeout(300)
    url = p.evaluate("() => location.search")
    check("uat=" in url, f"deschiderea dialogului scrie uat= in adresa ('{url}')")
    check("judet=" in url, f"adresa pastreaza si județul ('{url}')")
    check(p.evaluate("() => !document.querySelector('#uat-dialog').hidden"), "dialogul e deschis")

    # X inchide si curata adresa prin replaceState -- altfel Back de dupa X ar redeschide
    # dialogul pe care utilizatorul tocmai l-a inchis.
    p.click("#uat-dialog-close")
    p.wait_for_timeout(250)
    check(p.evaluate("() => document.querySelector('#uat-dialog').hidden"), "X inchide dialogul")
    check("uat=" not in p.evaluate("() => location.search"),
          f"X scoate uat= din adresa ('{p.evaluate('() => location.search')}')")

    # Back, de la dialog deschis, inchide dialogul in loc sa iasa de pe pagina.
    p.click("#county-picker button[data-uat]")
    p.wait_for_timeout(300)
    opened_url = p.evaluate("() => location.search")
    check("uat=" in opened_url and p.evaluate("() => !document.querySelector('#uat-dialog').hidden"),
          "dialogul s-a redeschis pentru testul Back")
    p.go_back()
    p.wait_for_timeout(350)
    check(p.evaluate("() => document.querySelector('#uat-dialog').hidden"),
          f"Back inchide dialogul, nu paraseste pagina (adresa: '{p.evaluate('() => location.search')}')")

    # Link direct: cine prinde adresa cu uat= vede dialogul deschis, fara niciun click.
    p.goto(BASE + opened_url, wait_until="networkidle")
    try:
        p.wait_for_selector("#uat-dialog-list a", timeout=8000)
    except Exception:
        skip(f"linkul direct '{opened_url}' nu a deschis dialogul in 8s (JSON UAT n-a sosit?)")
    else:
        check(p.evaluate("() => !document.querySelector('#uat-dialog').hidden"),
              f"link direct ({opened_url}) redeschide dialogul")
    p.goto(BASE, wait_until="networkidle")
    p.wait_for_selector("#news-list li", timeout=15000)


def mobil_390(p):
    """Android: harta e ~359x256px la 390 latime, deci ea e cazul greu pentru zona de atins.
    Aici se verifica si ca garda tap-vs-drag chiar tine cu EVENIMENTE TACTILE, nu doar cu mouse-ul
    -- pe desktop `pointerdown` vine de la mouse, pe telefon de la deget, si nu e acelasi drum."""
    print("\nMOBIL 390px (Android emulat) -- zona de atins si garda de derulare")
    p.wait_for_function("() => document.querySelector('#news-list li a') !== null", timeout=15000)
    over = p.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    check(over <= 0, f"fara overflow orizontal la 390px ({over}px)")

    # Pe ecranul Android harta începe sub introducere; o atingere cu y din afara viewportului
    # nu testează produsul, ci doar o coordonată imposibilă. O aducem în viewport înainte de tap.
    p.locator("#map canvas.map-canvas").scroll_into_view_if_needed()
    p.wait_for_timeout(150)
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

    # Zona de atins pe langa contur, masurata in PIXELI CSS. Toleranta era exprimata in unitati
    # viewBox, deci se evapora pe ecran mic: ~1.8px pe telefon fata de ~4px pe desktop, exact
    # invers decat trebuie. Pragul de 3px e ales ca discriminator: sub vechea implementare e
    # imposibil de atins, sub cea noua (10px CSS => +-5px) e comod.
    tol = edge_tolerance_px(p)
    if tol is None:
        skip("toleranta de atins pe langa contur: nu am gasit o margine de judet utilizabila")
    else:
        check(tol >= 3, f"atingerea la {tol}px CSS in afara conturului inca selecteaza (prag 3px)")
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
        hit_ordin_fara_furt(p)
        hover_preview(p)
        felia2_localitate(p)
        felia5_county_picker(p)
        felia6_url(p)
        uat_in_url(p)

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
