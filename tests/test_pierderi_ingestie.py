"""Contorul de pierderi la ingestie chiar numara — altfel e cod care nu face nimic.

DE CE EXISTA: sect. 7 PRESCRIE saritul tacut („SARE itemul — nu-l publica stricat"), iar
`main.py` numara ce se pierde DUPA fetch (`stale_skipped`, `deferred`, itemele fara
substanta). Ce nu intra NICIODATA in pipeline era invizibil prin constructie: un item sarit
la ingestie nu apare pe site, nu apare in `articles.json`, nu apare in log. Masurat
2026-09-02: opt puncte de abandon in `fetch.py`, zero contoare.

Contorul nu schimba comportamentul — il face numarabil. Testele de aici apara exact asta:
ca incrementarea se produce SI ca itemul chiar e aruncat, nu doar numarat.

Cifra care merita urmarita in timp e „garda de continut ostil": pana acum nimeni nu putea
spune cate articole respinge `guard` intr-o rulare reala (`IZZ-0168` a calibrat-o pe 3380
de articole, o singura data, in august).
"""
import pytest

from generator import fetch


@pytest.fixture(autouse=True)
def contor_curat():
    """Fiecare test porneste de la zero — `_SARITE` e stare de modul."""
    fetch._SARITE.clear()
    yield
    fetch._SARITE.clear()


def test_pierderi_ingestie_porneste_gol():
    assert fetch.pierderi_ingestie() == {}


def test_item_fara_titlu_e_numarat_SI_aruncat():
    """Doua afirmatii intr-un test, deliberat: un contor care numara fara sa arunce ar fi
    mai rau decat niciun contor — ar raporta pierderi inexistente."""
    xml = """<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
            xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
      <url><loc>https://exemplu.ro/a/</loc>
        <news:news><news:title>Titlu valid despre ceva</news:title></news:news></url>
      <url><loc>https://exemplu.ro/b/</loc>
        <news:news><news:title></news:title></news:news></url>
    </urlset>"""
    iteme, _err = fetch._parse_sitemap_news(
        xml.encode("utf-8"), "test",
        {"name": "Test", "url": "https://exemplu.ro", "category": "general"})
    p = fetch.pierderi_ingestie()
    assert sum(p.values()) == 1, f"asteptam exact o pierdere, avem {p}"
    assert "item incomplet" in " ".join(p), p
    # si chiar a fost aruncat, nu doar numarat
    assert all("/b/" not in (i.get("url") or "") for i in iteme), iteme


def test_motivele_sunt_distincte_nu_un_total():
    """Un contor cu un singur bucket ar spune «am pierdut 40» fara sa spuna DE CE, adica
    exact informatia pentru care exista."""
    fetch._SARITE["item incomplet (fara link sau titlu)"] += 3
    fetch._SARITE["garda de continut ostil"] += 2
    p = fetch.pierderi_ingestie()
    assert len(p) == 2 and sum(p.values()) == 5, p


def test_contorul_e_o_copie_nu_referinta():
    """Apelantul nu trebuie sa poata modifica starea interna din greseala."""
    fetch._SARITE["ceva"] += 1
    p = fetch.pierderi_ingestie()
    p["ceva"] = 999
    assert fetch.pierderi_ingestie()["ceva"] == 1


def _sursa(nume="Test", url="https://exemplu.ro"):
    return {"name": nume, "url": url, "base_url": url, "item": "div.art",
            "category": "general", "lang": "ro"}


def test_agentia_e_numarata_ca_agentie_in_toate_cele_trei_parsere():
    """Motivul trebuie sa fie CORECT, nu doar prezent.

    Regresie masurata 2026-09-04 (semnalata de recenzia Gemini pe PR #252, sosita la 20 de
    secunde DUPA merge, deci necitita): in `_items_from_html` cele doua conditii erau
    comasate intr-un singur `if`, deci un articol de agentie se numara drept „item
    incomplet". Efect: pe orice sursa de tip lista HTML contorul de agentie ramanea 0, iar
    „item incomplet" era umflat — exact contorul livrat ca sa faca pierderea VIZIBILA
    raporta gresit DE CE. Celelalte doua parsere separau corect; testul le prinde pe toate
    trei, ca fixul sa nu se piarda la urmatoarea rescriere a unuia dintre ele.
    """
    agentie = "https://www.agerpres.ro/stire/1/"

    # 1. lista HTML (scraper) — calea care avea defectul
    html = f'<div class="art"><a href="{agentie}">Titlu de agentie despre ceva</a></div>'
    iteme, _ = fetch._items_from_html(html, "test", _sursa())
    assert iteme == [], "articolul de agentie trebuie aruncat, nu doar numarat"
    p = fetch.pierderi_ingestie()
    assert p == {"agentie de presa (exclusa deliberat)": 1}, p

    # 2. sitemap Google News
    fetch._SARITE.clear()
    xml = f"""<?xml version="1.0"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
            xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
      <url><loc>{agentie}</loc>
        <news:news><news:title>Titlu de agentie despre ceva</news:title></news:news></url>
    </urlset>"""
    iteme, _ = fetch._parse_sitemap_news(xml.encode("utf-8"), "test", _sursa())
    assert iteme == []
    p = fetch.pierderi_ingestie()
    assert p == {"agentie de presa (exclusa deliberat)": 1}, p


def test_articolul_normal_trece_fara_sa_fie_numarat():
    """Granita cealalta: fixul nu trebuie sa arunce nici sa numere ce e in regula.

    MASURAT scriind testul, si mai grav decat parea: `_GenericListParser` NU emite iteme
    fara href sau fara text (verificat pe trei intrari — ancora goala, `&nbsp;`, href vid;
    toate dau `[]`). Deci ramura „item incomplet" din `_items_from_html` e defensiva,
    inaccesibila prin parser. Consecinta asupra bugului reparat: pe o sursa de tip lista
    HTML, contorul acela nu putea creste DECAT din agentii — deci nu o parte din cifra era
    atribuita gresit, ci TOATA. Ramura ramane (parserul se poate schimba), dar nu se poate
    testa prin el.
    """
    html = '<div class="art"><a href="https://exemplu.ro/a/">Titlu normal despre ceva</a></div>'
    iteme, _ = fetch._items_from_html(html, "test", _sursa())
    assert len(iteme) == 1, iteme
    assert fetch.pierderi_ingestie() == {}, "un articol valid nu e o pierdere"
