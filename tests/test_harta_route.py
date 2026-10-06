"""Regresie pentru ruta publică intuitivă a hărții știrilor."""
import json
from pathlib import Path

from slugify import slugify

from generator import geo


def _county_routes() -> list[tuple[str, str, str]]:
    data = json.loads(Path("static/harta-stiri/data/map.json").read_text(encoding="utf-8"))
    counties = (data.get("map") or {}).get("judete") or {}
    return [(code, slugify(geo.eticheta_judet(code)).strip("-").lower(), geo.eticheta_judet(code))
            for code in sorted(counties)]


def test_harta_route_redirects_to_public_page(output_randat):
    redirects = Path(output_randat, "_redirects")
    lines = redirects.read_text(encoding="utf-8").splitlines()
    assert "/harta-stiri /harta/ 301" in lines
    assert "/harta-stiri/ /harta/ 301" in lines
    assert "/zonal/* /judetean/:splat 301" in lines


def test_harta_source_page_and_dataset_exist():
    assert Path("static/harta-stiri/index.html").is_file()
    assert Path("static/harta-stiri/harta-stiri.js").is_file()
    assert Path("static/harta-stiri/data/map.json").is_file()


def test_harta_public_route_and_42_county_pages(output_randat):
    out = Path(output_randat)
    routes = _county_routes()
    assert len(routes) == 42
    assert (out / "harta" / "index.html").is_file()
    for _code, slug, _label in routes:
        assert (out / "harta" / slug / "index.html").is_file(), slug


def test_harta_county_pages_have_canonical_metadata_and_jsonld(output_randat):
    out = Path(output_randat)
    for code, slug, label in _county_routes():
        html = (out / "harta" / slug / "index.html").read_text(encoding="utf-8")
        canonical = f"https://izz.ro/harta/{slug}/"
        assert f"<title>Știri din {label} — Harta știrilor IZZ.ro</title>" in html
        assert f'<link rel="canonical" href="{canonical}">' in html
        assert f'<meta property="og:url" content="{canonical}">' in html
        assert f'<meta name="harta-county" content="{code}">' in html
        assert f"<h1>Știri din {label}</h1>" in html
        assert f'Harta știrilor din {label}' in html
        assert 'id="harta-jsonld" type="application/ld+json"' in html
        assert '"@type":"Dataset"' in html and label in html
        assert "/static/harta-stiri/harta-stiri.js" in html
        assert "/static/harta-stiri/vendor/maplibre/maplibre-gl.css" in html


def test_harta_routes_enter_sitemap(output_randat):
    sitemap = Path(output_randat, "sitemap.xml").read_text(encoding="utf-8")
    assert "https://izz.ro/harta/" in sitemap
    for _code, slug, _label in _county_routes():
        assert f"https://izz.ro/harta/{slug}/" in sitemap


def test_harta_js_uses_absolute_dataset_urls_for_public_routes():
    js = Path("static/harta-stiri/harta-stiri.js").read_text(encoding="utf-8")
    assert 'const DATA_URL = "/static/harta-stiri/data/map.json"' in js
    assert 'const PROJECTION_URL = "/static/harta-stiri/data/projection.json"' in js
    assert 'meta[name="harta-county"]' in js
