"""Partile pure ale masuratorii de gazde — cele care se verifica fara retea.

Aceeasi regula ca peste tot in repo: fiecare garda are perechea ei negativa.
"""
from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("masoara_gazde", ROOT / "tools" / "masoara_gazde.py")
mg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mg)


# --- extragerea gazdelor din corpul BRUT ---------------------------------------------

def test_extrage_gazdele_din_href():
    html = '<p>text</p><a href="https://t.me/Hack_0xTeam">aici</a> si <a href="http://WWW.Exemplu.RO/x">x</a>'
    assert mg.gazde_din_html(html) == ["t.me", "exemplu.ro"]


def test_cazul_cajvana_verbatim():
    """Cazul care a motivat toata felia: doua linkuri de Telegram in corpul unui articol
    de primarie, cu titlu care a trecut prin toate cele cinci straturi din guard.verdict."""
    html = '<a href="https://t.me/Hack_0xTeam">1</a><a href="https://t.me/Hello_root">2</a>'
    gazde = mg.gazde_din_html(html)
    assert gazde == ["t.me", "t.me"]
    assert all(mg.clasifica(g, "cajvana.ro") == "mesagerie" for g in gazde)


def test_html_fara_linkuri_nu_inventeaza_gazde():
    assert mg.gazde_din_html("<p>Consiliul local a aprobat bugetul.</p>") == []
    assert mg.gazde_din_html("") == [] and mg.gazde_din_html(None) == []


def test_entitatile_html_sunt_decodate():
    """`&amp;` in href e frecvent in feeduri; fara `unescape` gazda tot iese corect,
    dar testul tine comportamentul explicit."""
    assert mg.gazde_din_html('<a href="https://exemplu.ro/a?x=1&amp;y=2">l</a>') == ["exemplu.ro"]


def test_un_href_stricat_nu_opreste_restul():
    html = '<a href="http://[">rupt</a><a href="https://bun.ro/x">bun</a>'
    assert "bun.ro" in mg.gazde_din_html(html)


# --- clasificarea --------------------------------------------------------------------

def test_domeniul_propriu_e_cazul_normal_nu_o_anomalie():
    for gazda in ("primaria.ro", "www.primaria.ro", "static.primaria.ro"):
        assert mg.clasifica(gazda, "primaria.ro") == "proprie"


def test_clasele_sensibile_sunt_recunoscute():
    assert mg.clasifica("t.me", "x.ro") == "mesagerie"
    assert mg.clasifica("mega.nz", "x.ro") == "file-locker"
    assert mg.clasifica("bit.ly", "x.ro") == "scurtatura"
    assert mg.clasifica("pastebin.com", "x.ro") == "paste"
    assert mg.clasifica("facebook.com", "x.ro") == "retea-sociala"


def test_o_gazda_obisnuita_nu_e_incadrata_fortat():
    """Testul negativ al clasificarii: fara el, orice gazda ar putea cadea intr-o clasa
    'sensibila' si masuratoarea ar produce cifre umflate, care ar duce la o lista gresita."""
    assert mg.clasifica("digi24.ro", "primaria.ro") == "alta"
    assert mg.clasifica("gov.ro", "primaria.ro") == "alta"


def test_sursele_locale_sunt_populatia_sensibila():
    assert mg.e_local("pl_suceava_cajvana") and mg.e_local("cj_botosani")
    assert not mg.e_local("digi24") and not mg.e_local("g4media")


# --- raportul ------------------------------------------------------------------------

def test_raportul_arata_procentele_pe_grup():
    linii = mg.raport({"local": Counter({"proprie": 3, "mesagerie": 1}), "national": Counter()},
                      {"local": 2, "national": 0})
    text = "\n".join(linii)
    assert "LOCAL — 2 articole, 4 linkuri" in text
    assert "mesagerie" in text and "25.0%" in text
    assert "(niciun link)" in text        # grupul national, gol


def test_raportul_nu_imparte_la_zero():
    linii = mg.raport({"local": Counter(), "national": Counter()}, {"local": 0, "national": 0})
    assert all("%" not in linie for linie in linii)
