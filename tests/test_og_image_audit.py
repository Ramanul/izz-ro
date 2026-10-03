"""Garda pentru unealta intrebarii 7: og:image FUNCTIONAL, nu doar prezent.

DE CE testele astea: felul in care o unealta de masura minte aici e sa numere taguri in loc
de previzualizari. Un `<meta property="og:image" content="/poza.jpg">` trece de orice grep si
nu produce niciun card social; la fel un URL catre un fisier care nu s-a scris. `IZZ-0275`
a costat o sesiune intreaga exact asa — o unealta necalibrata pe un caz cu raspuns cunoscut.
Aici cazurile cu raspuns cunoscut sunt construite deliberat, in `tmp_path`, plus unul real:
randarea din `output_randat` (esantion) nu are voie sa aiba nicio pagina fara og:image
functional.
"""
import subprocess
import sys
import struct
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from tools import og_image_audit as og

ORIGINE = "https://izz.ro"
ROOT = Path(__file__).resolve().parents[1]


def _png(lat: int, inalt: int) -> bytes:
    """Header PNG valid pentru dimensiuni — parserul citeste doar octetii 16..23."""
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", lat, inalt)


def _jpeg(lat: int, inalt: int) -> bytes:
    """SOF0 minim: [FF D8] [FF C0] [len] [prec] [h] [w] ..."""
    return (b"\xff\xd8\xff\xc0" + struct.pack(">H", 17) + b"\x08"
            + struct.pack(">HH", inalt, lat) + b"\x03\x00\x00\x00")


def _pagina(dirpath: Path, rel: str, continut: str) -> Path:
    cale = dirpath / rel
    cale.parent.mkdir(parents=True, exist_ok=True)
    cale.write_text(f"<!doctype html><html><head>{continut}</head><body></body></html>",
                    encoding="utf-8")
    return cale


@pytest.fixture
def output_fals(tmp_path):
    """Un output mic, cu cazurile cunoscute: 4 pagini bune si restul defecte cate unul."""
    (tmp_path / "static").mkdir()
    (tmp_path / "og").mkdir()
    (tmp_path / "articol").mkdir()
    (tmp_path / "static" / "og-image.png").write_bytes(_png(1200, 630))
    (tmp_path / "og" / "local.jpg").write_bytes(_jpeg(1200, 630))
    (tmp_path / "articol" / "cover.jpg").write_bytes(_jpeg(1200, 630))
    return tmp_path


def _meta(url: str, width: tuple | None = (1200, 630)) -> str:
    sufix = "" if width is None else (f'<meta property="og:image:width" content="{width[0]}">'
                                     f'<meta property="og:image:height" content="{width[1]}">')
    return f'<meta property="og:image" content="{url}">{sufix}'


def test_ordinea_atributelor_nu_conteaza(output_fals):
    """`content` inaintea lui `property` e valid si a scapat unui grep naiv la masurare."""
    p = _pagina(output_fals, "a/index.html",
                f'<meta content="{ORIGINE}/static/og-image.png" property="og:image">')
    assert og.analizeaza_pagina(p, output_fals, ORIGINE)["stare"] == "ok"


def test_url_relativ_si_origine_straina_sunt_defecte(output_fals):
    """Ambele arata bine la grep si nu produc nicio previzualizare pe Facebook/WhatsApp."""
    relativ = _pagina(output_fals, "b/index.html", _meta("/static/og-image.png"))
    strain = _pagina(output_fals, "c/index.html", _meta("https://cdn.example/poza.jpg"))
    assert og.analizeaza_pagina(relativ, output_fals, ORIGINE)["stare"] == "relativ"
    assert og.analizeaza_pagina(strain, output_fals, ORIGINE)["stare"] == "alta-origine"


def test_fisierul_lipsa_e_defect(output_fals):
    """Calea arata corect, dar randearea nu a scris-o — card gol, nu eroare."""
    p = _pagina(output_fals, "d/index.html", _meta(f"{ORIGINE}/articol/inexistent/cover.jpg"))
    assert og.analizeaza_pagina(p, output_fals, ORIGINE)["stare"] == "fisier-lipsa"


def test_nivelurile_de_imagine(output_fals):
    """Rolul imaginii se citeste din cale: propriu / categorie / generic / necunoscut."""
    cazuri = {
        f"{ORIGINE}/articol/cover.jpg": "propriu",
        f"{ORIGINE}/og/local.jpg": "categorie",
        f"{ORIGINE}/static/og-image.png": "generic",
        f"{ORIGINE}/altfel/poza.jpg": "necunoscut",
    }
    for i, (url, asteptat) in enumerate(cazuri.items()):
        if asteptat == "necunoscut":        # fisierul nu exista: aici conteaza doar nivelul
            _pagina(output_fals, f"e{i}/index.html", _meta(f"{ORIGINE}/altfel/poza.jpg"))
            (output_fals / "altfel").mkdir()
            (output_fals / "altfel" / "poza.jpg").write_bytes(_jpeg(1200, 630))
        else:
            _pagina(output_fals, f"e{i}/index.html", _meta(url))
        r = og.analizeaza_pagina(output_fals / f"e{i}" / "index.html", output_fals, ORIGINE)
        assert r["nivel"] == asteptat, url
        assert r["stare"] == "ok", url


def test_dimensiunile_declarate_gresit_sunt_avertisment(output_fals):
    """PNG-ul e 1200x630, meta declara altceva: previzualizarea se decupeaza, nu se pierde."""
    p = _pagina(output_fals, "f/index.html",
                _meta(f"{ORIGINE}/articol/cover.jpg", width=(800, 600)))
    r = og.analizeaza_pagina(p, output_fals, ORIGINE)
    assert r["stare"] == "ok" and r["dimensiuni_gresit"]


def test_png_si_jpeg_se_citesc_la_fel(output_fals):
    assert og.dimensiuni_fisier(output_fals / "static" / "og-image.png") == (1200, 630)
    assert og.dimensiuni_fisier(output_fals / "og" / "local.jpg") == (1200, 630)


def test_duplicat_si_twitter_diferit(output_fals):
    """Doua valori `og:image` diferite: prima ajunge pe Facebook, a doua pe Twitter."""
    p = _pagina(output_fals, "g/index.html",
                _meta(f"{ORIGINE}/og/local.jpg")
                + f'<meta property="og:image" content="{ORIGINE}/static/og-image.png">'
                + f'<meta name="twitter:image" content="{ORIGINE}/static/og-image.png">')
    r = og.analizeaza_pagina(p, output_fals, ORIGINE)
    assert r["duplicat"] and r["twitter_diferit"]


def test_masoara_agrega_si_numara_urlurile_distincte(output_fals):
    _pagina(output_fals, "ok1/index.html", _meta(f"{ORIGINE}/og/local.jpg"))
    _pagina(output_fals, "rau/index.html", _meta("/og/local.jpg"))
    r = og.masoara(output_fals, ORIGINE)
    assert r["pagini"] == 2 and r["blocante"] == 1 and r["stari"] == {"ok": 1, "relativ": 1}
    assert r["exemple"]["relativ"] == ["rau/index.html"]
    assert r["url_distincte"] == 1


def test_iesirea_e_non_zero_doar_cand_exista_defecte(output_fals):
    """Contractul pentru CI: cod 0 pe curat, 1 pe defect. Se testeaza pe proces real."""
    _pagina(output_fals, "ok/index.html", _meta(f"{ORIGINE}/static/og-image.png"))
    cmd = [sys.executable, str(ROOT / "tools" / "og_image_audit.py"),
           "--output-dir", str(output_fals), "--origine", ORIGINE]
    assert subprocess.run(cmd, capture_output=True, text=True).returncode == 0
    _pagina(output_fals, "rau/index.html", _meta("/static/og-image.png"))
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 1 and "rau/index.html" in r.stdout


def test_fallbackul_generic_are_dimensiunile_declarate_in_base_html():
    """Premisa fixului din `static/harta-stiri/index.html`: ultimul refugiu chiar exista."""
    assert og.dimensiuni_fisier(ROOT / "static" / "og-image.png") == (1200, 630)
    base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    assert 'property="og:image:width" content="1200"' in base
    assert 'property="og:image:height" content="630"' in base


def test_output_randat_nu_are_pagina_fara_og_image_functional(output_randat):
    """Cazul real: nicio pagina din randare nu are voie sa ramana fara card social.

    `output_randat` randeaza un ESANTION (IZZ_RENDER_ESANTION, implicit 200 de articole) —
    suficient: toate tipurile de pagina (homepage, categorie, paginare, subiect, ghid, legal,
    cautare, harta) se randeaza la fel, indiferent cate articole intra in ele.
    """
    r = og.masoara(ROOT / "output", "https://izz.ro", exemple_max=50)
    vinovati = [p for pagini in r["exemple"].values() for p in pagini]
    assert r["blocante"] == 0, f"{r['blocante']} pagini fara og:image functional: {vinovati}"
    assert r["niveluri"].get("propriu", 0) > 0, "nicio coperta proprie: masuratoarea e oarba"


def test_originea_implicita_vine_din_config():
    """Fara `--origine`, comparatia se face cu domeniul real, nu cu o constanta paralela."""
    sys.path.insert(0, str(ROOT))
    from generator import config
    assert urlsplit(config.SITE["url"]).netloc == "izz.ro"
