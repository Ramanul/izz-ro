"""Rute statice canonice pentru harta mare și paginile județene."""
import json
import re
from pathlib import Path

from generator import render


def test_harta_route_redirects_and_source_assets_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    render._write_redirects()
    lines = (tmp_path / "_redirects").read_text(encoding="utf-8").splitlines()
    assert "/harta-stiri /harta/ 301" in lines
    assert "/harta-stiri/ /harta/ 301" in lines
    assert "/zonal/* /judetean/:splat 301" in lines
    assert Path("static/harta-stiri/index.html").is_file()
    assert Path("static/harta-stiri/harta-stiri.js").is_file()
    assert Path("static/harta-stiri/data/map.json").is_file()


def test_generator_emits_one_canonical_static_route_per_county(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    before = render._PAGES_WRITTEN.copy()
    try:
        render._write_harta_pages()
        routes = render._harta_rute_judetene()
        assert len(routes) == 42
        assert len({slug for _, slug, _ in routes}) == 42
        expected = {slug for _, slug, _ in routes}
        actual = {p.name for p in (tmp_path / "harta").iterdir() if p.is_dir()}
        assert actual == expected
        published = set(render._editorial_paths())
        assert "/harta/" in published
        assert all(f"/harta/{slug}/" in published for slug in expected)
        for code, slug, label in routes:
            route_html = (tmp_path / "harta" / slug / "index.html").read_text(encoding="utf-8")
            assert f'<meta name="harta-county" content="{code}">' in route_html
            assert f'<link rel="canonical" href="https://izz.ro/harta/{slug}/">' in route_html
            assert f"<h1>Știri din {label}</h1>" in route_html

        root = (tmp_path / "harta" / "index.html").read_text(encoding="utf-8")
        assert '<link rel="canonical" href="https://izz.ro/harta/">' in root
        assert '<meta name="harta-county" content="">' in root
        assert '<title>Harta știrilor — IZZ.ro</title>' in root
        assert "<!-- HARTA_JSONLD -->" not in root

        code, slug, label = next(row for row in routes if row[0] == "TIMIS")
        page_path = tmp_path / "harta" / slug / "index.html"
        page = page_path.read_text(encoding="utf-8")
        canonical = f"https://izz.ro/harta/{slug}/"
        assert f'<title>Știri din {label} — Harta știrilor IZZ.ro</title>' in page
        assert f'<link rel="canonical" href="{canonical}">' in page
        assert f'<meta property="og:url" content="{canonical}">' in page
        assert f'<meta name="harta-county" content="{code}">' in page
        assert f"<h1>Știri din {label}</h1>" in page
        assert 'content="/static/harta-stiri/data"' in page
        assert "/static/harta-stiri/harta-stiri.js" in page
        assert "/static/harta-stiri/harta-stiri.css" in page
        match = re.search(r'<script id="harta-jsonld" type="application/ld\+json">(.*?)</script>', page)
        assert match
        graph = json.loads(match.group(1))["@graph"]
        dataset = next(node for node in graph if node.get("@type") == "Dataset")
        place = next(node for node in graph if node.get("@type") == "AdministrativeArea")
        assert dataset["url"] == canonical
        assert dataset["spatialCoverage"]["@id"] == place["@id"]
        assert place["name"] == label
        assert place["containedInPlace"]["name"] == "România"
    finally:
        render._PAGES_WRITTEN.clear()
        render._PAGES_WRITTEN.update(before)


def test_site_navigation_uses_the_canonical_map_path():
    base = Path("templates/base.html").read_text(encoding="utf-8")
    home = Path("templates/index.html").read_text(encoding="utf-8")
    assert '{{ base }}/harta/' in base
    assert '{{ base }}/harta/' in home


def test_all_county_routes_use_editorial_labels_and_slug_codes():
    routes = render._harta_rute_judetene()
    by_code = {code: (slug, label) for code, slug, label in routes}
    assert by_code["TIMIS"] == ("timis", "Timiș")
    assert by_code["BISTRITA-NASAUD"] == ("bistrita-nasaud", "Bistrița-Năsăud")
    assert by_code["SATU MARE"] == ("satu-mare", "Satu Mare")
    assert by_code["BUCURESTI"] == ("bucuresti", "București")
