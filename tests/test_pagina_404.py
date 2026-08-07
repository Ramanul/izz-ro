"""Pagina 404 nu e o categorie goala, e capatul unui link mort.

De ce merita test propriu: cel mai frecvent motiv pentru care cineva ajunge acolo NU e o
adresa gresita, ci un articol EXPIRAT — `ARTICLE_TTL_DAYS = 7`, masurat pe live 8/8 cu
control pozitiv si negativ (handoff/arhiva/2026-08-06-handoff-integral.md). Pana la
2026-08-07 pagina primea `articles=[]` si cadea pe starea goala a sablonului de categorie,
adica raspundea „Nicio stire in aceasta categorie deocamdata" — fals si derutant.

Testele astea prind exact regresia aia: cineva care simplifica apelul inapoi la `articles=[]`
readuce mesajul gresit, si tacut, fiindca pagina se randeaza in continuare fara eroare.
"""
import os
import re

MESAJ_GRESIT = "Nicio știre în această categorie"


def _html(output_randat):
    cale = os.path.join(output_randat, "404.html")
    assert os.path.isfile(cale), "404.html nu s-a randat"
    with open(cale, encoding="utf-8") as f:
        return f.read()


def test_404_nu_mai_spune_ca_e_o_categorie_goala(output_randat):
    assert MESAJ_GRESIT not in _html(output_randat)


def test_404_spune_ca_articolul_poate_fi_expirat(output_randat):
    """Formularea exacta poate evolua; ce nu are voie sa dispara e explicatia. Cerem cele
    doua cuvinte-cheie separat, ca testul sa nu pice la o rescriere de stil."""
    h = _html(output_randat)
    assert "expirat" in h, "pagina nu explica de ce lipseste articolul"
    assert re.search(r"Adresa nu exist|nu exist", h), "pagina nu acopera si adresa gresita"


def test_404_ofera_stiri_recente_in_loc_de_fundatura(output_randat):
    """Minimul e deliberat sub cele 12 randate: testul apara COMPORTAMENTUL (pagina duce
    undeva), nu o constanta. Cu `articles=[]` numarul e zero, deci regresia tot se prinde."""
    h = _html(output_randat)
    articole = re.findall(r'<article[^>]*class="[^"]*card', h)
    assert len(articole) >= 6, f"doar {len(articole)} carduri pe 404 — pagina e o fundatura"


def test_404_are_titlu_propriu_nu_de_categorie(output_randat):
    h = _html(output_randat)
    m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
    assert m, "404 nu are h1"
    assert "negăsită" in m.group(1)
