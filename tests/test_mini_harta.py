"""Mini-harta puls + reading progress (Faze 2 si 5)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import render  # noqa: E402
from generator.mini_harta import install_hook  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Asigura hook-ul in mediu de test (home_fresh poate sa nu fi fost apelat inca)
install_hook()


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


def test_base_ctx_injecteaza_mini_harta_cand_are_zi():
    zi = {"stiri": 1, "surse": 1, "judete": 1, "pe_judet": {"CLUJ": 2}}
    ctx = render._base_ctx("/", zi=zi)
    assert "mini_harta" in ctx
    # None daca lipseste harta_judete.json in mediu izolat; altfel dict cu forme
    assert ctx["mini_harta"] is None or "forme" in ctx["mini_harta"]


def test_sablonul_are_blocul_puls():
    with open(os.path.join(ROOT, "templates", "index.html"), encoding="utf-8") as fh:
        html = fh.read()
    assert "mini_harta" in html and 'class="puls"' in html
    assert 'class="puls-map"' in html and "/harta/" in html


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
    assert "site.css" in html


def test_rampa_pulsului_este_identica_cu_rampa_hartii_mari():
    """Un singur sistem vizual: cele cinci trepte de pe homepage sunt EXACT cele de pe
    harta mare. Pagina hărții e standalone (nu incarca foaia site-ului), deci valorile sunt
    copiate deliberat -- testul e garda care impiedica divergenta tacuta (diagnostic
    4 oct 2026: patru harti in patru limbi)."""
    import re

    harta_css = open(os.path.join(ROOT, "static", "harta-stiri", "harta-stiri.css"),
                     encoding="utf-8").read()
    bloc = re.search(r":root \{(.*?)\}", harta_css, re.S).group(1)
    harta = []
    for i in range(5):
        m = re.search(r"--map-h" + str(i) + r":\s*(#[0-9a-fA-F]{6})", bloc)
        assert m, f"harta-stiri.css: lipseste --map-h{i}"
        harta.append(m.group(1).lower())

    faza2 = open(os.path.join(ROOT, "static", "faza2.css"), encoding="utf-8").read()
    puls = []
    for i in range(5):
        m = re.search(r"\.puls-map path\.h" + str(i) + r"\s*\{\s*fill:\s*(#[0-9a-fA-F]{6})", faza2)
        assert m, f"faza2.css: lipseste .puls-map path.h{i}"
        puls.append(m.group(1).lower())

    assert puls == harta, f"rampa pulsului {puls} difera de rampa hartii {harta}"
