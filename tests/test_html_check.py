"""Poarta de HTML trebuie sa POATA pica, nu doar sa treaca.

Rulat pe `output/` real, `tools/html_check.py` raporteaza 0 probleme — exact rezultatul pe care
l-ar da si un checker stricat. Testele de aici sunt teste de MUTATIE: construiesc un `output/`
minimal in tmp, injecteaza cate un defect si verifica exit code 1. Fara ele, poarta ar putea
putrezi tacut si am crede in continuare ca site-ul e curat.

(Verificat si pe output-ul real, prin patru mutatii pe `index.html`: toate patru prinse, exit=1
de fiecare data, exit=0 dupa restaurare. Aici se repeta ieftin, ca sa ramana verificat.)
"""
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
html_check = importlib.import_module("tools.html_check")

CURAT = """<!DOCTYPE html><html><head>
<link rel="stylesheet" href="/static/styles.css">
</head><body>
<a href="/despre/">Despre</a>
<a href="/#sus">Sus</a>
<img src="/static/x.png" alt="ceva">
<div id="sus"></div>
</body></html>"""


@pytest.fixture
def sit(tmp_path, monkeypatch):
    """Un `output/` minimal si VALID; testele il strica punctual."""
    out = tmp_path / "output"
    (out / "static").mkdir(parents=True)
    (out / "static" / "styles.css").write_text("body{}", encoding="utf-8")
    (out / "static" / "x.png").write_bytes(b"\x89PNG")
    (out / "despre").mkdir()
    (out / "despre" / "index.html").write_text(CURAT, encoding="utf-8")
    (out / "index.html").write_text(CURAT, encoding="utf-8")
    monkeypatch.setattr(html_check, "OUT", str(out))
    monkeypatch.setattr(sys, "argv", ["html_check.py"])
    return out


def test_output_valid_trece(sit):
    assert html_check.main() == 0


def test_legatura_interna_moarta_pica(sit):
    (sit / "index.html").write_text(
        CURAT.replace('href="/despre/"', 'href="/nu-exista/"'), encoding="utf-8")
    assert html_check.main() == 1


def test_activ_lipsa_pica(sit):
    (sit / "index.html").write_text(
        CURAT.replace("/static/styles.css", "/static/lipsa.css"), encoding="utf-8")
    assert html_check.main() == 1


def test_ancora_inexistenta_pica(sit):
    (sit / "index.html").write_text(
        CURAT.replace('href="/#sus"', 'href="/#nu-exista"'), encoding="utf-8")
    assert html_check.main() == 1


def test_img_fara_alt_pica(sit):
    (sit / "index.html").write_text(
        CURAT.replace(' alt="ceva"', ""), encoding="utf-8")
    assert html_check.main() == 1


def test_alt_gol_e_acceptat(sit):
    """`alt=""` pe o imagine decorativa e CORECT (cardurile sunt `aria-hidden`), deci poarta
    verifica absenta atributului, nu valoarea lui. Altfel ar cere text alternativ pentru
    pictograme pur ornamentale — si l-ar primi, ceea ce e mai rau pentru cititoarele de ecran."""
    (sit / "index.html").write_text(CURAT.replace('alt="ceva"', 'alt=""'), encoding="utf-8")
    assert html_check.main() == 0


def test_legaturile_externe_nu_sunt_cerute_pe_disc(sit):
    """Nu verificam reteaua: un link extern nu are voie sa pice poarta."""
    (sit / "index.html").write_text(
        CURAT.replace('href="/despre/"', 'href="https://exemplu.ro/orice"'), encoding="utf-8")
    assert html_check.main() == 0


def test_mailto_si_tel_sunt_ignorate(sit):
    (sit / "index.html").write_text(
        CURAT.replace('href="/despre/"', 'href="mailto:contact@izz.ro"'), encoding="utf-8")
    assert html_check.main() == 0


def test_url_absolut_catre_propriul_site_e_verificat_ca_intern(sit):
    """`https://izz.ro/nu-exista/` e tot o legatura interna — daca ar fi tratata ca externa,
    jumatate din legaturile noastre (JSON-LD, feed, canonical) ar scapa neverificate."""
    (sit / "index.html").write_text(
        CURAT.replace('href="/despre/"', 'href="https://izz.ro/nu-exista/"'), encoding="utf-8")
    assert html_check.main() == 1
