"""Paginarea categoriilor: fara linkuri moarte, fara pagini orfane.

Context masurat pe randarea din 2026-08-03, inainte de fixul asta. Sablonul scria fix
`1 2 3` si numai pe pagina 1:

* trei linkuri MOARTE — `general/3`, `politic/3`, `tech/3` (categorii cu exact 2 pagini);
* din 79 de pagini de listare randate, **35 accesibile si 44 orfane**; `zonal` randa 20 de
  pagini si oprea navigatia la 3;
* orfanele nu erau nici in `sitemap.xml` (`_write_sitemap` nu pune paginare deloc), deci
  nu exista nicio a doua cale spre ele.

Nimic din tests/ nu atingea paginarea (`grep -rl "pagination|page_num|/2/" tests/` -> nimic),
de asta a putut trai. Testele de mai jos apara invariantul, nu forma: fiecare link duce
undeva randat, si fiecare pagina randata se atinge din pagina 1 prin parcurgere.
"""
import os
import re
import subprocess
import sys

import pytest

from generator import config, render

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")

_NAV_RE = re.compile(r'<nav class="pagination".*?</nav>', re.S)
_HREF_RE = re.compile(r'href="([^"]+)"')


# --------------------------------------------------------------- unitar ---

def test_o_singura_pagina_nu_are_navigatie():
    assert render._pagination("sport", 1, 1) is None


def test_pagina_1_sta_pe_radacina_categoriei():
    assert render._cat_page_path("sport", 1) == "/sport/"
    assert render._cat_page_path("sport", 2) == "/sport/2/"


def test_doua_pagini_nu_linkeaza_a_treia():
    """Cazul exact al linkurilor moarte general/3, politic/3, tech/3."""
    p = render._pagination("general", 1, 2)
    assert [i["n"] for i in p["pages"]] == [1, 2]
    assert p["next"] == "/general/2/"
    assert p["prev"] is None


def test_ultima_pagina_nu_are_urmatoarea():
    p = render._pagination("general", 2, 2)
    assert p["next"] is None
    assert p["prev"] == "/general/"
    assert p["pages"][-1]["path"] is None      # 2 e curenta, deci nu e link


def test_pagina_curenta_nu_e_link():
    p = render._pagination("zonal", 5, 20)
    curent = [i for i in p["pages"] if i and i["n"] == 5]
    assert curent and curent[0]["path"] is None


def test_fereastra_arata_capetele_si_vecinii():
    p = render._pagination("zonal", 10, 20)
    numere = [i["n"] for i in p["pages"] if i]
    assert numere == [1, 8, 9, 10, 11, 12, 20]
    assert None in p["pages"]                  # saltul e marcat, nu ascuns


def test_orice_pagina_e_atinsa_prin_parcurgere():
    """Invariantul care lipsea: din 1 se ajunge oriunde urmand doar linkurile randate."""
    total = 20
    vazute, de_vizitat = {1}, [1]
    while de_vizitat:
        n = de_vizitat.pop()
        p = render._pagination("zonal", n, total)
        vecini = {i["n"] for i in p["pages"] if i}
        for v in vecini - vazute:
            vazute.add(v)
            de_vizitat.append(v)
    assert vazute == set(range(1, total + 1))


# ---------------------------------------------------------- pe randare ---

@pytest.fixture(scope="module")
def randat():
    """Randeaza NECONDITIONAT. Fixturile vechi randeaza doar cand `output/` lipseste, iar un
    `output/` ramas de pe alta ramura le face sa raporteze despre alt cod decat cel testat —
    a picat exact asa de doua ori in ziua in care s-a scris fisierul asta. 30 de secunde in
    plus per rulare sunt mai ieftine decat un verdict despre randarea altcuiva."""
    r = subprocess.run([sys.executable, "-m", "generator.main", "--render-only"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, f"randarea a esuat:\n{r.stdout}\n{r.stderr}"
    assert os.path.isdir(OUT), "output/ lipseste si dupa randare"
    return OUT


def _pagini_randate(cat: str) -> set:
    """Numerele paginilor de listare existente pe disc pentru o categorie."""
    d = os.path.join(OUT, cat)
    if not os.path.isfile(os.path.join(d, "index.html")):
        return set()
    numere = {1}
    for nume in os.listdir(d):
        if nume.isdigit() and os.path.isfile(os.path.join(d, nume, "index.html")):
            numere.add(int(nume))
    return numere


def _linkuri_paginare(cat: str, n: int) -> set:
    p = os.path.join(OUT, cat, "index.html") if n == 1 else os.path.join(OUT, cat, str(n), "index.html")
    html = open(p, encoding="utf-8").read()
    nav = _NAV_RE.search(html)
    return set(_HREF_RE.findall(nav.group(0))) if nav else set()


def _numar_din_cale(cat: str, href: str) -> int | None:
    # Sablonul prefixeaza fiecare href cu `base` = SITE_BASE (gol implicit, dar setat cand
    # site-ul e servit dintr-un subdirector). Fara taierea lui, testele ar raporta „link in
    # afara categoriei" pentru linkuri perfect corecte.
    baza = os.getenv("SITE_BASE", "").rstrip("/")
    if baza and href.startswith(baza):
        href = href[len(baza):]
    m = re.fullmatch(rf"/{re.escape(cat)}/(\d+)/", href)
    if m:
        return int(m.group(1))
    return 1 if href == f"/{cat}/" else None


def test_niciun_link_de_paginare_nu_e_mort(randat):
    morti = []
    for cat in config.CATEGORIES:
        randate = _pagini_randate(cat)
        for n in randate:
            for href in _linkuri_paginare(cat, n):
                tinta = _numar_din_cale(cat, href)
                assert tinta is not None, f"link de paginare in afara categoriei: {href}"
                if tinta not in randate:
                    morti.append(f"{cat}/{n} -> {href}")
    assert not morti, "linkuri spre pagini care nu exista pe disc: " + ", ".join(morti)


def test_nicio_pagina_randata_nu_e_orfana(randat):
    orfane = {}
    for cat in config.CATEGORIES:
        randate = _pagini_randate(cat)
        if not randate:
            continue
        vazute, de_vizitat = {1}, [1]
        while de_vizitat:
            n = de_vizitat.pop()
            for href in _linkuri_paginare(cat, n):
                t = _numar_din_cale(cat, href)
                if t in randate and t not in vazute:
                    vazute.add(t)
                    de_vizitat.append(t)
        lipsa = randate - vazute
        if lipsa:
            orfane[cat] = sorted(lipsa)
    assert not orfane, f"pagini randate dar de neatins din pagina 1: {orfane}"


def test_paginile_2_plus_au_si_ele_navigatie(randat):
    """Regresia veche: `show_pagination` era True doar pe pagina 1, deci pagina 2 era o fundatura."""
    fara = [f"{cat}/{n}" for cat in config.CATEGORIES
            for n in sorted(_pagini_randate(cat)) if n > 1 and not _linkuri_paginare(cat, n)]
    assert not fara, "pagini fara navigatie: " + ", ".join(fara)


def test_o_categorie_cu_o_singura_pagina_nu_arata_paginare(randat):
    for cat in config.CATEGORIES:
        if _pagini_randate(cat) == {1}:
            assert not _linkuri_paginare(cat, 1), f"{cat} are o pagina, dar afiseaza paginare"


def test_un_slug_numeric_nu_fura_calea_unei_pagini_de_paginare():
    """`/sport/2/` e pagina 2, nu un articol. Articolele se scriu dupa paginile de listare,
    deci un slug „2" ar suprascrie pagina si linkul din navigatie ar duce la un articol."""
    arts = [{"title": "2", "category": "sport", "published": "2026-08-03T10:00:00+00:00"},
            {"title": "007", "category": "sport", "published": "2026-08-03T10:00:00+00:00"}]
    render._assign_slugs(arts)
    assert [a["slug"] for a in arts] == ["stirea-2", "stirea-007"]
    assert not any(a["slug"].isdigit() for a in arts)


def test_significance_a_disparut_din_sabloane():
    """Ramura moarta: 0 din 1736 de articole aveau campul, iar generator/ nu-l scria nicaieri."""
    for nume in ("_card.html", "index.html"):
        html = open(os.path.join(ROOT, "templates", nume), encoding="utf-8").read()
        assert "significance" not in html, f"{nume} inca randeaza significance"
    css = open(os.path.join(ROOT, "static", "styles.css"), encoding="utf-8").read()
    assert ".sig " not in css and ".sig{" not in css, "styles.css inca are reguli pentru .sig"
