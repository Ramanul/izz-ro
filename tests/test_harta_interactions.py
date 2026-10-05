import json
from pathlib import Path


def test_map_has_single_canvas_creation_path():
    # ensureCanvas() e singurul loc care creeaza <canvas> -- reutilizeaza nodul existent
    # (state.canvas) cat timp e inca in DOM, ceea ce e fix-ul din e3832692 pentru
    # dedublarea vizuala pe scroll real (vezi STATE.md A2).
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert js.count('document.createElement("canvas")') == 1
    assert "if (state.canvas && host.contains(state.canvas)) return state.canvas;" in js
    assert "clearRect" in js


def test_map_deduplicates_locality_markers():
    # Doua grupuri cu aceleasi coordonate (SIRUTA diferit, punct identic) se combina intr-un
    # singur marker vizual prin `byCoordinate`, pastrand toate identitatile in `localities`
    # (fix A3 -- clickul pe un marker suprapus alegea mereu primul, nu cel mai apropiat).
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "byCoordinate" in js
    assert "existing.localities.push(group.locality)" in js


def test_map_rebuild_replaces_old_canvas():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "host.replaceChildren();" in js


def test_map_redraw_is_transform_safe():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "setTransform(1, 0, 0, 1, 0, 0)" in js
    assert "clearRect(0, 0" in js


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


def test_map_stats_use_visible_counts_and_the_general_map_total():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "const items = state.visible;" in js
    assert "state.data?.stats?.events" in js
    assert "state.data?.stats?.total" in js
    assert "din ${number(overallCount)} ${itemLabel()} pe hartă" in js
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    assert "totalul localizat al setului hărții" in html
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
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'fetch(`./data/uat/${encodeURIComponent(county)}.json`' in js
    assert "function drawUats(" in js
    assert "ctx.isPointInPath(unit.path2d" in js
    assert "ctx.fillText(String(uat.count)" in js
    assert "if (state.zoomCounty) {\n      const groups = new Map();" in js
    assert "state.localityMarkers = localityMarkers;" in js


def test_openfreemap_basemap_is_decorative_and_uses_published_projection():
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    css = Path("static/harta-stiri/harta-stiri.css").read_text(encoding="utf-8")
    assert "/static/harta-stiri/vendor/maplibre/maplibre-gl.css" in html
    assert 'import("./vendor/maplibre/maplibre-gl.mjs")' in js
    assert 'fetch(PROJECTION_URL' in js
    assert r'.trim().split(/\s+/).map(Number)' in js
    assert "interactive: false" in js
    assert "OpenMapTiles" in html
    assert "Data from" in html
    assert 'basemapContainer.setAttribute("aria-hidden", "true")' in js
    assert ".map-canvas{position:relative;z-index:1;background:transparent;}" in css
    assert "function failBasemap(error)" in js
    assert "state.basemapReady ? THEMATIC_FILL_ALPHA : 1" in js


def test_locality_markers_show_only_locality_references_and_explain_precision():
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'item.geo_level !== "local"' in js
    assert "item.x == null || item.y == null" in js
    assert "const haloRadius = 9 * markerScale" in js
    assert "precizia în metri nu este disponibilă" in js
    assert "nu locurile exacte ale evenimentelor" in html
    assert "Relatările fără coordonate nu primesc puncte inventate" in html
    assert "Localități România punct" in html


def test_openfreemap_csp_allows_only_needed_tile_host_and_worker_bootstrap():
    source = Path("generator/render.py").read_text(encoding="utf-8")
    csp = source.split("csp =", 1)[1].split("_write(", 1)[0]
    assert "img-src 'self' data: https://tiles.openfreemap.org" in csp
    assert "connect-src 'self' https://tiles.openfreemap.org" in csp
    assert "worker-src 'self' blob:" in csp


def test_legend_handles_deduplicated_thresholds_and_zero_results():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "if (low > high) continue;" in js
    assert 'const steps = [{ cls: "h0", label: "0" }];' in js
    assert "caption.textContent = max > 0" in js
    assert "Număr de ${mode}" in js
    assert "Culorile regiunilor editoriale" in js
    assert "updateLegend(praguri, maxCount, { show: true })" in js
    assert "nuanțele mai închise indică mai multe" in js


def test_uat_counts_tooltips_and_search_notes_match_the_active_list():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'uat.count = itemsForView(uat.items).length' in js
    assert 'titles = itemsForView(target.items).slice(0, 3)' in js
    assert 'all.filter((item) => matchesPlace(item, query)).length' in js
    assert 'norm(`${item.county} ${item.locality} ${item.region}`)' in js
    assert 'scope: "uat"' in js
    assert "if (state.selectedUat && state.uats.length && !state.uatLoading)" in js
    assert "=== state.selectedUat);" in js
    assert "String(uat.id || uat.name) === state.selectedUat" in js
    assert "updateStats();\n          announceState();" in js


def test_map_clears_uat_loading_state_on_cache_hit():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "if (cached) {\n      state.uatLoading = false;\n      state.uats = cached;" in js


def test_map_ignores_stale_uat_requests_after_reselection():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "uatRequestId" in js
    assert "state.uatRequestId !== requestId" in js
    assert "state.uatCounty === county && state.uatRequestId === requestId" in js


def test_map_visually_delimits_editorial_regions():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "const REGION_FILLS" in js
    assert 'state.level === "regional" ? regionFill' in js
    assert "ctx.fillText(region" in js


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


def test_uat_badge_radius_is_constrained_to_polygon_interior():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "function uatBadgePlacement" in js
    assert "uatContainsMapPoint" in js
    assert "placement.clearance * 0.72" in js


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
