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
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from generator import render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


@pytest.fixture(scope="module")
def sitemap_locs():
    path = os.path.join(ROOT, "output", "sitemap.xml")
    if not os.path.isfile(path):
        r = subprocess.run([sys.executable, "-m", "generator.main", "--render-only"],
                           cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, f"randarea a esuat:\n{r.stdout}\n{r.stderr}"
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


def test_caile_editoriale_se_citesc_de_pe_disc():
    """Direct pe functie: daca directorul exista pe disc, calea apare — nicio lista scrisa
    de mana intre ghidul nou si sitemap."""
    paths = render._editorial_paths()
    assert "/ghiduri/" in paths
    assert any(p.startswith("/ghiduri/") and p != "/ghiduri/" for p in paths)
    assert not any(p.startswith("/subiect/") for p in paths)
