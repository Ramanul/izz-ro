from pathlib import Path

from generator.process import _repair_synthesis_title

ROOT = Path(__file__).resolve().parents[1]


def test_sinteza_nu_confunda_identitatea_falsa_cu_perceptia():
    title = "Doi bărbați arestați după ce au simțit polițiști antidrog"
    context = "Suspecții au pretins că sunt lucrători antidrog și s-au dat drept polițiști."
    assert _repair_synthesis_title(title, context) == (
        "Doi bărbați arestați după ce s-au dat drept polițiști antidrog"
    )


def test_mai_multe_sectiuni_are_destinatie_si_link():
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    render = (ROOT / "generator" / "render.py").read_text(encoding="utf-8")
    assert 'href="{{ base }}/sectiuni/"' in base
    assert 'os.path.join(OUT_DIR, "sectiuni", "index.html")' in render
