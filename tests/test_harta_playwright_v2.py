from pathlib import Path


def test_visual_workflow_contains_real_interaction_regression():
    workflow = Path(".github/workflows/visual.yml").read_text(encoding="utf-8")
    for token in ("scrollTo", "querySelectorAll('canvas')", "requestAnimationFrame"):
        assert token in workflow, f"visual workflow missing interaction check: {token}"


def test_map_source_has_single_canvas_and_safe_redraw():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert js.count("document.createElement('canvas')") == 1
    assert "ResizeObserver" in js
    assert "setTransform(1, 0, 0, 1, 0, 0)" in js
    assert "clearRect(0, 0" in js
    assert "renderToken" in js


def test_map_source_deduplicates_markers():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert "markerMap" in js
    assert "localities" in js


def test_map_html_does_not_precreate_canvas():
    html = Path("static/harta-stiri/index.html").read_text(encoding="utf-8")
    assert html.count("<canvas") == 0
