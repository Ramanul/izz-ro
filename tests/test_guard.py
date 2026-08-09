"""Teste pentru garda de continut ostil (`generator/guard.py`).

Incidentul care le-a cerut: 2026-08-09, feedul primariei Rovinari (WordPress compromis) a
publicat 8 pagini de warez pe izz.ro. Detaliu: `specs/securitate-ingestie.md`.

Testele astea sunt duble ca rol: verifica garda SI verifica autotestul care pazeste garda.
"""
import pytest

from generator import guard
from generator.util import clean_html


# --- corpusul real de atac ---------------------------------------------------------------

@pytest.mark.parametrize("titlu,corp", guard._CORPUS_OSTIL)
def test_corpusul_ostil_e_respins(titlu, corp):
    assert guard.verdict(titlu, corp) is not None, f"a scapat: {titlu!r}"


@pytest.mark.parametrize("titlu,corp", guard._CORPUS_CURAT)
def test_corpusul_curat_trece(titlu, corp):
    assert guard.verdict(titlu, corp) is None, \
        f"fals-pozitiv pe {titlu!r}: {guard.verdict(titlu, corp)}"


def test_autotest_trece_si_numara():
    """Dead man's switch-ul insusi: daca nu ruleaza cazuri, e dezactivat din greseala."""
    n = guard.autotest()
    assert n == len(guard._CORPUS_OSTIL) + len(guard._CORPUS_CURAT)
    assert n >= 10


def test_autotest_arunca_daca_garda_e_stricata(monkeypatch):
    """Simuleaza un regex stricat: autotestul TREBUIE sa opreasca build-ul, nu sa taca."""
    monkeypatch.setattr(guard, "e_curat", lambda t, c="": True)
    with pytest.raises(guard.GardaStricata):
        guard.autotest()


# --- straturile, unul cate unul -----------------------------------------------------------

def test_markup_supravietuitor():
    assert guard.verdict("Anunt", '<img src="x" onload=alert(1)>') == "markup in text dupa curatare"
    assert guard.verdict("Anunt", "&lt;script&gt;") == "markup in text dupa curatare"


def test_payload_fara_taguri():
    """Payload ramas dupa ce tagurile au fost taiate corect — tot trebuie prins."""
    assert guard.verdict("Anunt", "window.location = evil") is not None
    assert guard.verdict("Anunt", "String.fromCharCode(88,83,83)") is not None


def test_homoglife_matematice():
    # „To𝚛rent" — U+1D69B MATHEMATICAL MONOSPACE SMALL R
    assert guard.verdict("Office 2021 Free Download To\U0001d69brent") is not None


def test_homoglife_chirilice_in_acelasi_cuvant():
    # „Frее" cu doi „е" chirilici (U+0435)
    assert guard.verdict("Frее Download Software") is not None


def test_chirilic_ca_token_separat_e_permis():
    """Un nume rusesc scris chirilic, ca CUVANT intreg, e continut legitim de stire."""
    assert guard.verdict("Declarația lui Владимир Путин despre acord") is None


def test_titlu_gunoi():
    assert guard.verdict("ki0esb8vxpjuiwknjx") is not None


def test_cuvant_romanesc_lung_nu_e_gunoi():
    """Fara cifre in el, un token lung ramane titlu valid — vezi `_e_titlu_gunoi`."""
    assert guard.verdict("Responsabilitate") is None
    assert guard.verdict("Contravenționalizarea") is None


def test_diacriticele_nu_declanseaza_homoglife():
    assert guard.verdict("Ședință de îndată la Primăria Târgu Jiu, cu șapte puncte") is None


# --- cauza-radacina: ordinea din clean_html -----------------------------------------------

def test_clean_html_scoate_markup_dublu_codat():
    """Pana pe 2026-08-09 se taiau tagurile INAINTE de decodare, deci asta trecea intreg."""
    murdar = 'Anunt &lt;img src="data:image/gif;base64,R0lGOD" onload=window.genC&gt; final'
    curat = clean_html(murdar)
    assert "<img" not in curat and "onload" not in curat
    assert "Anunt" in curat and "final" in curat


def test_clean_html_nu_strica_textul_normal():
    assert clean_html("Temperaturi de &lt; 0 grade") == "Temperaturi de < 0 grade"
    assert clean_html("Anunț &amp; convocator") == "Anunț & convocator"
    assert clean_html("<p>Text simplu</p>") == "Text simplu"
