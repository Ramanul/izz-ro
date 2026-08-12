from pathlib import Path


def test_map_has_single_canvas_creation_path():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert js.count("document.createElement('canvas')") == 1
    assert "renderToken" in js
    assert "clearRect" in js


def test_map_deduplicates_locality_markers():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "markerMap" in js
    assert "localities" in js


def test_map_rebuild_replaces_old_canvas():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "canvas.remove()" in js
    assert "canvasWrap.replaceChildren()" in js or "replaceChildren" in js


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
