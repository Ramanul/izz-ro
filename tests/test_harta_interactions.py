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
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'fetch(`./data/uat/${encodeURIComponent(county)}.json`' in js
    assert "function drawUats(" in js
    assert "ctx.isPointInPath(unit.path2d" in js
    assert "ctx.fillText(String(uat.count)" in js
    assert "state.zoomCounty && !state.uats.length" in js


def test_map_clears_uat_loading_state_on_cache_hit():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "if (cached) {\n      state.uatLoading = false;\n      state.uats = cached;" in js


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


def test_uat_picker_and_dialog_are_exposed_after_county_selection():
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'id="uat-dialog"' in html
    assert 'role="dialog"' in html
    assert "function openUatDialog" in js
    assert "button.dataset.uat" in js
    assert 'button.setAttribute("aria-haspopup", "dialog")' in js


def test_uat_badge_radius_is_constrained_to_polygon_interior():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "function uatBadgePlacement" in js
    assert "uatContainsMapPoint" in js
    assert "placement.clearance * 0.72" in js
