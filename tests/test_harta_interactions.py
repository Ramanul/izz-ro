import json
from pathlib import Path


def test_map_has_single_stage_creation_path():
    # ensureStage() e singurul loc care construieste suprafata de desenare -- reutilizeaza nodul
    # existent (state.stage) cat timp e inca in DOM, ceea ce e fix-ul din e3832692 pentru
    # dedublarea vizuala pe scroll real (vezi STATE.md A2). Substratul e SVG din 2026-10-04
    # (F1 din notes/harta-revolutie-proposal-2026-10-04.md): nu exista canvas nicaieri.
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert js.count('svgNode("svg"') == 1
    assert 'document.createElement("canvas")' not in js
    assert "getContext(" not in js
    assert "if (state.stage && host.contains(state.stage)) return state.stage;" in js


def test_map_deduplicates_locality_markers():
    # Doua grupuri cu aceleasi coordonate (SIRUTA diferit, punct identic) se combina intr-un
    # singur marker vizual (cheie pe coordonate rotunjite), pastrand toate identitatile in
    # `localities` (fix A3 -- clickul pe un marker suprapus alegea mereu primul).
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "const groups = new Map();" in js
    assert "x.toFixed(4)" in js and "y.toFixed(4)" in js
    assert "if (!group.localities.includes(locality)) group.localities.push(locality);" in js


def test_map_rebuild_replaces_old_stage():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "host.replaceChildren();" in js
    assert 'stage.className = "map-stage";' in js


def test_map_redraw_is_transform_safe():
    # Randarea e DERIVATA din stare (viewBox scris din `state.view`), nu acumulata pe un context:
    # nu exista transformari imperative care sa se adune la fiecare cadru, nici hit-test pe
    # cai parsate manual -- clasa de buguri a canvasului (IZZ-0193/0194).
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'state.svg.setAttribute("viewBox"' in js
    assert "setTransform(" not in js
    # Cuvantul apare doar in comentariul care documenteaza ce s-a sters; interogarea, nu.
    assert ".isPointInPath(" not in js and ".isPointInStroke(" not in js
    assert "let node = byKey.get(key);" in js


def test_map_resize_observer_is_present():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "ResizeObserver" in js


def test_map_has_no_duplicate_static_canvas():
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    assert html.count("<canvas") == 0


def test_map_exposes_event_and_article_views_with_shareable_state():
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'data-view="events"' in html
    assert 'data-view="articles"' in html
    assert 'params.set("mod", state.viewMode)' in js
    assert 'viewMode: params.get("mod") === "articles" ? "articles" : "events"' in js
    assert "function itemsForView(items)" in js


def test_map_has_progressive_loading_and_accessible_status():
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'id="show-more"' in html
    assert 'id="map-status"' in html
    assert 'aria-live="polite"' in html
    assert "state.listLimit += 120" in js
    assert "function announceState()" in js


def test_map_stats_use_confirmed_localities_and_freshness_metadata():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert '.filter((item) => item.locality)' in js
    assert "state.data?.latest_article_at" in js
    assert "localități confirmate" in js


def test_map_has_bounded_loading_and_retry_state():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "AbortController" in js
    assert "controller.abort(), 12000" in js
    assert "Încearcă din nou" in js
    assert "Datele hărții nu sunt disponibile momentan" in js


def test_map_can_load_uat_boundaries_and_render_count_badges():
    # O singura cerere per judet (clip-path-ul a eliminat si siluetele vecinilor), UAT-urile ca
    # <path> native, cifra pe unitatile cu stiri, iar asignarea geometrica o face browserul.
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'fetch(`./data/uat/${encodeURIComponent(county)}.json`)' in js
    assert "function renderUats(" in js
    assert "node.isPointInFill(new DOMPoint(x, y))" in js
    assert "function countUatNews(" in js
    assert "function uatAtMapPoint(" in js
    assert "state.zoomCounty && !state.uats.length" in js


def test_map_clears_uat_loading_state_on_cache_hit():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "if (cached) {\n      state.uatLoading = false;\n      state.uats = cached;" in js


def test_map_ignores_stale_uat_requests_after_reselection():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "uatRequestId" in js
    assert "state.uatRequestId !== requestId" in js
    assert "state.uatCounty === county && state.uatRequestId === requestId" in js


def test_map_visually_delimits_editorial_regions():
    # Culorile regiunilor au trecut din canvas in CSS (`.map-stage.is-regional`): un singur loc
    # pentru toata paleta hartii; eticheta de regiune e agregata (o data per regiune, nu 14).
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    css = Path("static/harta-stiri/harta-stiri.css").read_text(encoding="utf-8")
    assert '.map-stage.is-regional .map-county[data-regiune="Transilvania"]' in css
    assert '"data-regiune": regionForCounty(county)' in js
    assert 'kind: "regiune"' in js


def test_timis_uat_geometry_is_published():
    data = Path("static/harta-stiri/data/uat/TIMIS.json").read_text(encoding="utf-8")
    assert '"county":"TIMIS"' in data
    assert '"uats":[' in data
    assert '"path":"M' in data


def test_uat_geometry_is_published_for_every_map_county():
    map_data = json.loads(Path("static/harta-stiri/data/map.json").read_text(encoding="utf-8"))
    expected = set((map_data.get("map") or {}).get("judete") or {})
    published = {path.stem for path in Path("static/harta-stiri/data/uat").glob("*.json")}
    assert published == expected
    for county in expected:
        payload = json.loads(Path(f"static/harta-stiri/data/uat/{county}.json").read_text(encoding="utf-8"))
        assert payload["county"] == county
        assert payload["uats"]
        assert all(unit["path"].startswith("M") for unit in payload["uats"])


def test_uat_picker_selects_in_panel_after_county_selection():
    # Audit harta, P0: click = selectare. Dialogul a fost ELIMINAT, nu doar neatinse -- panoul
    # lateral si adresa sunt singurele reprezentari ale selectiei de UAT (un singur mecanism,
    # nu doua: un dialog mort ar fi exact identificatorul care putrezeste, vezi IZZ-0177).
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'id="uat-dialog"' not in html
    assert 'role="dialog"' not in html
    assert "openUatDialog" not in js
    assert "button.dataset.uat" in js
    assert 'button.setAttribute("aria-pressed", state.selectedUat === uatKey ? "true" : "false")' in js


def test_uat_label_anchor_is_inside_the_polygon():
    # Pastila nu mai e cautata cu zeci de mii de point-in-polygon per cadru (uatBadgePlacement:
    # 79.831 interogari la TIMIS per redesenare): ancorarea vine din `center`-ul UAT-ului
    # (centroid de arie, calculat la build), e validata O SINGURA DATA cu isPointInFill pe o
    # grila 9x9 si tinuta minte in state.anchors.
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "function anchorFor(node, key, fallback)" in js
    assert "for (let row = 1; row <= 9; row += 1)" in js
    assert "state.anchors.set(key, point)" in js
    assert "anchorFor(node, `uat:${key}`, uat.center)" in js


def test_uat_selection_is_url_navigable_state():
    # Selectia de UAT e stare navigabila: intra in adresa (?judet=X&uat=Y), se citeste din
    # adresa, iar aplicarea asteapta asignarea geometrica (`pendingUat`).
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'params.set("uat", state.selectedUat)' in js
    assert 'uat: params.get("uat") || null' in js
    assert "state.pendingUat" in js
    # Asignarea UAT-urilor se face din rawVisible, nu din visible: selectia se filtreaza pe
    # baza asignarii, deci din visible s-ar auto-hrani (toate celelalte UAT-uri ar cadea pe 0).
    assert "for (const item of state.rawVisible) {" in js


def test_map_has_location_breadcrumb_and_plain_language():
    # Firul ierarhic = pozitie in IERARHIE (NN/g), nivelul curent text cu aria-current;
    # interfata vorbeste limba utilizatorului ("orase si comune"), nu jargon administrativ.
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'id="map-breadcrumb"' in html
    assert "function updateBreadcrumb(" in js
    assert 'aria-current", "location"' in js
    assert 'Orașe și comune cu știri în' in js
    assert 'UAT-uri cu știri în' not in js
    # Text unic de revenire (audit P2: trei texte diferite au devenit unul).
    assert 'state.backButton.textContent = "← Înapoi la România"' in js
def test_zoom_and_pan_are_keyboard_operable_and_documented():
    # Ghidurile de harti accesibile cer zoom+pan pe TOATE input-urile: sagețile deplaseaza
    # vederea pe grupul de controale, +/- schimba scara, iar nota de sub harta documenta
    # interactiunile (rotita, dublu-click, tragere, tastatura, gesturi).
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    assert 'zoomBox.addEventListener("keydown"' in js
    assert 'zoomBox.setAttribute("role", "group")' in js
    assert "function announceZoom(" in js
    assert "săgețile" in html
    assert "două degete" in html


def test_lista_harti_nu_linkuieste_inregistrarile_fara_slug():
    # Fara slug nu exista pagina de articol: linkul construit oricum ducea la `/local//`
    # — pagina de categorie Local, nu articolul (20 de inregistrari event fara URL in
    # map.json, masurat 2026-10-03). Titlul se randeaza ca <span>, nu ca ancora.
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'item.slug ? "a" : "span"' in js
    assert "a.href = articleUrl(item);" not in js


def test_map_substrate_has_no_third_party_scripts():
    # 0 lei si fara biblioteci: un singur script, al nostru; fara import-uri externe, fara
    # framework de harti. Contractul cere ≤ 70 KB gzip pe client (vezi propunerea, 4.7).
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert html.count("<script") == 1
    assert "/static/harta-stiri/harta-stiri.js" in html
    assert "from \"https://" not in js and "from 'https://" not in js
    assert "import(" not in js


def test_map_labels_are_real_text_with_minimum_pixel_sizes():
    # Pe telefon, textul desenat in unitati de viewBox ajungea la ~3 px (masurat 2026-10-03).
    # Acum etichetele sunt <text> in grupuri contrascarate (`.label-fit`), cu marimi in PIXELI
    # de ecran, iar liniile au latime de ecran indiferent de zoom (non-scaling-stroke).
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    css = Path("static/harta-stiri/harta-stiri.css").read_text(encoding="utf-8")
    assert "const LABEL_PX = { judet: 13, regiune: 14, uat: 11, cifra: 12 };" in js
    assert 'class: "label-fit"' in js
    assert ".label-fit" in css
    assert "vector-effect:non-scaling-stroke" in css


def test_map_polygons_are_keyboard_and_screen_reader_reachable():
    # Calea accesibila se PASTREAZA, nu se sacrifica pentru grafica: fiecare poligon e un
    # element focusabil cu rol de buton si stare, deci se poate naviga si fara mouse.
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'role: "button"' in js
    assert 'tabindex: "0"' in js
    assert '"aria-pressed", selected ? "true" : "false"' in js
    # Textul citit de cititorul de ecran vine din ACEEASI functie care da cifra de pe ecran
    # (inclusiv unitatea, in modul „pe locuitor"), deci vocea si harta nu pot spune altceva.
    assert "node.setAttribute(\"aria-label\", `${judetLabel(county)}: ${cifra.bucata}`)" in js
    assert "function cifraJudet(county)" in js
    assert "la 100.000 de locuitori" in js


def test_map_outline_lives_in_its_own_layer():
    # Conturul județului deschis NU are voie sa stea in stratul de UAT-uri: acela e golit la
    # revenirea la nivel național (`replaceChildren`), iar un <use> adaugat o singura data in
    # ensureStage ar disparea definitiv -- exact bugul prins de verificarea de DOM la scrierea
    # feliei (2026-10-04). Strat propriu = nici tăiat de clip-path, deci nu-si pierde jumatate
    # din grosime la marginea județului.
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    css = Path("static/harta-stiri/harta-stiri.css").read_text(encoding="utf-8")
    assert 'for (const name of ["counties", "uats", "outline", "points", "labels"])' in js
    assert 'class: "map-outline"' in js
    assert "state.layers.outline.hidden = !showUats;" in js
    assert ".map-outline{fill:none;stroke:var(--map-stroke)" in css
    # Silueta e un singur <path> in <defs>, referit de doua ori: de clip-path si de contur.
    assert 'id: "clip-judet-silueta"' in js
