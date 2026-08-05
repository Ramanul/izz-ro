"""Eticheta copertei nu poate fi None, oricat de stricat ar veni articolul.

Regresie raportata de CodeRabbit pe PR #139 si ramasa neaplicata: `_eticheta` folosea
`a.get("category", "stiri")`, care intoarce default-ul DOAR cand cheia lipseste. Cu
`category: None` in dict intorcea None, iar `_subtitlu` face `.strip()` pe rezultat —
deci AttributeError la generarea copertei.

Masurat pe 2026-08-05: 9950 de articole din `data/` au toate `category` valid, deci era
risc latent, nu incident. O sursa noua sau un parser schimbat il activa. `htmlart.py` nu
avea niciun test — de-aia a supravietuit findingul.
"""
import pytest

from generator import htmlart


@pytest.mark.parametrize("articol", [
    {},                                    # cheia lipseste
    {"category": None},                    # cheia exista, valoarea e None  <- cazul raportat
    {"category": ""},                      # sir gol
    {"category": "   "},                   # doar spatii
])
def test_eticheta_intoarce_mereu_text(articol):
    """Fara judet si fara categorie utilizabila, eticheta cade pe „stiri", nu pe None."""
    eticheta = htmlart._eticheta(articol)
    assert isinstance(eticheta, str)
    assert eticheta.strip(), f"eticheta goala pentru {articol!r}"


@pytest.mark.parametrize("articol", [
    {},
    {"category": None},
    {"category": ""},
])
def test_subtitlu_nu_crapa_pe_categorie_lipsa(articol):
    """`_subtitlu` apeleaza `_eticheta(a).strip()` — cu None acolo, crapa cu AttributeError."""
    assert htmlart._subtitlu(articol) == ""


def test_categoria_valida_ramane_eticheta():
    """Comportamentul normal nu se schimba: fara judet, eticheta E categoria."""
    assert htmlart._eticheta({"category": "sport"}) == "sport"
