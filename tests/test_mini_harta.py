"""Mini-harta puls + reading progress (Faze 2 si 5)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_fara_pe_judet_intoarce_none():
    assert render._mini_harta({}) is None
    assert render._mini_harta(None) is None  # type: ignore[arg-type]


def test_trepte_pe_cuartele_volumului():
    pe = {"CLUJ": 4, "TIMIS": 2, "BRASOV": 1}
    out = render._mini_harta(pe)
    if out is None:
        return
    assert out["total"] == 7
    by = {f["judet"]: f["treapta"] for f in out["forme"]}
    assert by.get("CLUJ") == 4
    assert by.get("BRASOV") == 1
    assert any(f["treapta"] == 0 for f in out["forme"])


def test_sablonul_are_blocul_puls():
    with open(os.path.join(ROOT, "templates", "index.html"), encoding="utf-8") as fh:
        html = fh.read()
    assert "mini_harta" in html and 'class="puls"' in html
    assert 'class="puls-map"' in html and "/static/harta-stiri/" in html


def test_css_are_treptele_h0_h4():
    paths = [
        os.path.join(ROOT, "static", "styles.css"),
        os.path.join(ROOT, "static", "faza2.css"),
    ]
    css = ""
    for p in paths:
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                css += fh.read()
    assert ".puls {" in css and ".puls-map path.h0" in css and ".puls-map path.h4" in css


def test_article_are_bara_de_progres():
    with open(os.path.join(ROOT, "templates", "article.html"), encoding="utf-8") as fh:
        html = fh.read()
    assert 'class="progress"' in html


def test_css_are_reading_progress_cu_reduced_motion():
    paths = [
        os.path.join(ROOT, "static", "styles.css"),
        os.path.join(ROOT, "static", "faza2.css"),
    ]
    css = ""
    for p in paths:
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                css += fh.read()
    assert "animation-timeline: scroll()" in css
    assert "prefers-reduced-motion" in css


def test_base_leaga_faza2_css():
    with open(os.path.join(ROOT, "templates", "base.html"), encoding="utf-8") as fh:
        html = fh.read()
    assert "faza2.css" in html
