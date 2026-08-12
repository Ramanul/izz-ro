from pathlib import Path
import re


def test_visual_workflow_exercises_repeated_scroll_and_canvas_stability():
    workflow = Path(".github/workflows/visual.yml").read_text(encoding="utf-8")
    required = [
        "page.evaluate",
        "scrollTo",
        "ResizeObserver",
        "canvas",
        "requestAnimationFrame",
    ]
    for token in required:
        assert token in workflow, f"visual workflow must exercise {token}"


def test_visual_workflow_asserts_single_canvas_and_stable_marker_count():
    workflow = Path(".github/workflows/visual.yml").read_text(encoding="utf-8")
    assert "querySelectorAll('canvas')" in workflow or 'querySelectorAll("canvas")' in workflow
    assert "marker" in workflow.lower()
    assert re.search(r"scrollTo|scrollBy", workflow)
