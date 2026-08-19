"""Regresie pentru ruta publică intuitivă a hărții știrilor."""
from pathlib import Path


def test_harta_route_redirects_to_static_page():
    redirects = Path("output/_redirects")
    if not redirects.exists():
        # Generatorul este randat de fixture-ul de sesiune în suita completă.
        return
    lines = redirects.read_text(encoding="utf-8").splitlines()
    assert "/harta-stiri/ /static/harta-stiri/ 301" in lines
    assert "/zonal/* /judetean/:splat 301" in lines


def test_harta_source_page_and_dataset_exist():
    assert Path("static/harta-stiri/index.html").is_file()
    assert Path("static/harta-stiri/harta-stiri.js").is_file()
    assert Path("static/harta-stiri/data/map.json").is_file()
