"""Sitemap-ul trebuie sa contina si paginile editoriale, nu doar stirile.

Context masurat 2026-08-02 pe sitemap-ul LIVE: 1256 de URL-uri, toate `/`, categorii si
articole. Fiecare ghid, calculatorul, calendarul, catalogul de surse si toate paginile
legale lipseau — pagini vii, linkate din navigatie, invizibile pentru crawler. Cauza:
`_write_sitemap` construia lista din `config.CATEGORIES` + articole si atat.

Testele apara doua lucruri: ca sectiunile sunt acolo, si ca lista se citeste de pe disc —
altfel un ghid nou ar cere si o editare de lista ca sa fie descoperit, iar exact tipul asta
de pas uitat a lasat golul de mai sus.
"""
import os
import xml.etree.ElementTree as ET

import pytest

from generator import render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


@pytest.fixture(scope="module")
def sitemap_locs(output_randat):
    # Randarea vine din `output_randat` (tests/conftest.py), neconditionat. Varianta veche
    # — „randeaza doar daca sitemap.xml lipseste" — valida artefactul gasit pe disc, deci
    # raporta despre alt cod decat cel testat; masuratoarea e in docstring-ul lui conftest.
    path = os.path.join(output_randat, "sitemap.xml")
    assert os.path.isfile(path), "sitemap.xml lipseste si dupa randare"
    return [e.text for e in ET.parse(path).getroot().iter(NS + "loc")]


def test_sitemapul_e_xml_valid_si_fara_duplicate(sitemap_locs):
    assert len(sitemap_locs) == len(set(sitemap_locs)), "URL-uri duplicate in sitemap"
    assert all(u.endswith("/") for u in sitemap_locs), "URL fara slash final"


@pytest.mark.parametrize("cale", [
    "/ghiduri/", "/instrumente/", "/instrumente/calculator-salariu/",
    "/calendar/", "/surse/", "/legal/privacy/", "/despre/",
])
def test_paginile_editoriale_sunt_in_sitemap(sitemap_locs, cale):
    from generator import config
    assert config.SITE["url"] + cale in sitemap_locs, f"{cale} lipseste din sitemap"


def test_fiecare_ghid_randat_apare_in_sitemap(sitemap_locs):
    """Citit de pe disc: un ghid nou intra automat, fara editat vreo lista."""
    from generator import config
    ghiduri = os.path.join(ROOT, "output", "ghiduri")
    ids = [d for d in os.listdir(ghiduri) if os.path.isdir(os.path.join(ghiduri, d))]
    assert len(ids) >= 3, "prea putine ghiduri randate ca testul sa insemne ceva"
    for eid in ids:
        assert f"{config.SITE['url']}/ghiduri/{eid}/" in sitemap_locs, f"{eid} lipseste"


def test_paginile_de_infrastructura_raman_afara(sitemap_locs):
    """`/cauta/` e o unealta, `subiect/` sunt ~300 de pagini de agregare subtiri (decizie de
    proprietar), iar `static/`/`data/` nu sunt continut."""
    interzise = ("/cauta/", "/subiect/", "/static/", "/data/", "/leads/", "/portraits/")
    gasite = [u for u in sitemap_locs if any(seg in u for seg in interzise)]
    assert not gasite, f"pagini care n-ar trebui indexate: {gasite[:5]}"


def test_paginile_vin_din_ce_s_a_scris_nu_din_ce_e_pe_disc(tmp_path, monkeypatch):
    """Gaura gasita la review: `output/` nu se curata intre randari, deci un director ramas
    de la alta ramura — `/utile/`, calea moarta din 17 iulie — intra in sitemap ca pagina vie.
    Reprodus inainte de reparare: `_editorial_paths()` chiar intorcea `/utile/`.
    Acum lista vine din ce a scris rularea, deci un director orfan nu are cum sa apara."""
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    monkeypatch.setattr(render, "_PAGES_WRITTEN", set())

    # un director orfan pe disc, pe care nimic nu-l randeaza
    orfan = tmp_path / "utile" / "salariul-minim"
    orfan.mkdir(parents=True)
    (orfan / "index.html").write_text("x", encoding="utf-8")
    (tmp_path / "utile" / "index.html").write_text("x", encoding="utf-8")

    assert render._editorial_paths() == [], "un director orfan a intrat in sitemap"

    # ce scrie rularea chiar intra, fara nicio lista de editat
    render._write(str(tmp_path / "ghiduri" / "ghid-nou" / "index.html"), "x")
    render._write(str(tmp_path / "subiect" / "ceva" / "index.html"), "x")
    paths = render._editorial_paths()
    assert "/ghiduri/ghid-nou/" in paths
    assert not any(p.startswith("/subiect/") for p in paths)
    assert not any(p.startswith("/utile/") for p in paths)


def test_paginile_de_sine_statatoare_vin_din_sursa_lor():
    """`/despre/` e recunoscuta fiindca `content/pages/despre.md` exista — nu fiindca a
    supravietuit unei liste de excluderi scrise de mana."""
    assert "despre" in render._content_page_slugs()
