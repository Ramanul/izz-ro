"""Reordonarea barei de rubrici nu are voie sa demonteze dropdownul „Mai multe secțiuni".

DE CE EXISTA (raportat de proprietar, 2026-09-09). `personalize.js::reorderNav()` sorteaza
rubricile dupa istoricul de lectura al cititorului. Varianta dinainte lua
`nav.querySelectorAll('a[href]')` — care prinde si linkul din `<summary>`, si pe cele patru
din `<details class="subnav-more">` — si le muta cu `nav.appendChild()`. Efectul, vizibil pe
live: dropdownul ramanea gol, „Mai multe secțiuni" ajungea in mijlocul randului ca element
fara continut, cele patru rubrici ascunse se revarsau in bara, iar bara capata scroll
orizontal. Adica exact „talmes-balmes cu rubricile" din sesizare.

De ce n-a prins-o nicio verificare de pana acum, si de ce testul e pe SURSA, nu pe DOM:
`reorderNav` se opreste devreme sub `MIN_INTERACTIONS` clicuri, deci orice browser fara
istoric — orice randare headless, orice vizitator nou — vede ordinea canonica si nimic
stricat. Repo-ul n-are runner de JS, deci garda mecanica pe care o putem avea aici e pe
proprietatile sintactice ale fisierului. Ea nu dovedeste comportamentul; dovedeste ca cele
doua greseli concrete care au produs simptomul nu se pot intoarce tacut.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sursa() -> str:
    with open(os.path.join(ROOT, "static", "personalize.js"), encoding="utf-8") as fh:
        return fh.read()


def _reorder_nav() -> str:
    """CODUL lui `reorderNav`, fara comentarii.

    Comentariile se taie deliberat: ele descriu tocmai greseala reparata (`appendChild`,
    `a[href]`), deci un test care citeste si proza ar pica pe explicatia fixului — adica ar
    interzice sa documentezi ce ai reparat. Verificat: prima versiune a acestui fisier chiar
    a picat asa.
    """
    s = _sursa()
    start = s.index("function reorderNav()")
    corp = s[start:s.index("\n  }", start)]
    return "\n".join(re.sub(r"//.*$", "", linie) for linie in corp.split("\n"))


def test_reordoneaza_doar_linkurile_de_pe_primul_nivel():
    corp = _reorder_nav()
    assert ":scope > a[data-cat]" in corp, (
        "selectorul trebuie sa fie ancorat pe primul nivel; altfel prinde si linkurile "
        "dinauntrul dropdownului si le scoate din el")


def test_NEGATIV_selectorul_lacom_nu_se_intoarce():
    """Cazul negativ: exact expresia care a produs simptomul pe live."""
    corp = _reorder_nav()
    assert "querySelectorAll('a[href]')" not in corp, (
        "`a[href]` neancorat prinde si `<summary> a` si `.subnav-more-list a`")


def test_dropdownul_ramane_ultimul():
    """Reasezarea se face INAINTEA lui `.subnav-more`, nu peste el."""
    corp = _reorder_nav()
    assert "insertBefore" in corp and "appendChild" not in corp, (
        "`appendChild` muta rubricile DUPA dropdown si il lasa in mijlocul randului")
    assert ".subnav-more" in corp, "reperul fata de care se insereaza trebuie sa fie explicit"


def test_sablonul_chiar_are_structura_pe_care_se_bazeaza_selectorul():
    """Garda pe LEGATURA: un selector corect pe un sablon schimbat e tot inutil."""
    with open(os.path.join(ROOT, "templates", "base.html"), encoding="utf-8") as fh:
        html = fh.read()
    subnav = html[html.index('<nav class="subnav"'):html.index("</nav>", html.index('<nav class="subnav"'))]
    assert 'data-cat="{{ cat }}"' in subnav, "linkurile de rubrica trebuie sa poarte data-cat"
    assert 'class="subnav-more"' in subnav, "dropdownul trebuie sa pastreze clasa dupa care e gasit"
    # linkul din <summary> NU are data-cat -- exact ce il tine in afara reordonarii
    summary = re.search(r"<summary>.*?</summary>", subnav, re.S)
    assert summary and "data-cat" not in summary.group(0), (
        "daca linkul din <summary> primeste data-cat, reordonarea il va muta din nou")
