"""Motorul generic de scraping (Monitor Local): parser config-driven pentru
liste de anunturi ale primariilor fara RSS. Verificat pe fixture HTML realist
(sandbox-ul n-are internet, dar parserul e Python pur)."""
from generator.fetch import _GenericListParser, _parse_ro_date, _sel

# Fixture realist: 3 anunturi, div-uri imbricate, <img> (void), data in format ro,
# plus zgomot inainte/dupa lista (header/footer) ca sa prindem falsele pozitive.
FIXTURE = """
<html><body>
<header><nav><a href="/acasa">Acasă</a></nav></header>
<main>
  <div class="news-item">
    <div class="thumb"><a href="/anunt/1"><img src="/img/1.jpg"></a></div>
    <div class="body">
      <a class="title" href="/anunt/1">Ședință de consiliu local pe 20 iulie</a>
      <span class="date">17.07.2026</span>
    </div>
  </div>
  <div class="news-item">
    <div class="body">
      <a class="title" href="https://primaria.ro/anunt/2">Program cu publicul modificat</a>
      <span class="date">15 iulie 2026</span>
    </div>
  </div>
  <div class="news-item">
    <div class="body">
      <a class="title" href="/anunt/3">Licitație pentru reabilitare drum</a>
      <span class="date">2026-07-10</span>
    </div>
  </div>
</main>
<footer><a href="/contact">Contact</a></footer>
</body></html>
"""


def test_sel_parses_selectors():
    assert _sel("div.news-item") == ("div", "news-item")
    assert _sel("article") == ("article", None)
    assert _sel(None) == (None, None)


def test_generic_parser_extracts_only_list_items():
    p = _GenericListParser("https://primaria.ro", "div.news-item",
                           title="a.title", date="span.date")
    p.feed(FIXTURE)
    # exact 3 anunturi — nu prinde link-urile din header/footer (Acasă / Contact)
    assert len(p.items) == 3
    titles = [i["title"] for i in p.items]
    assert "Ședință de consiliu local pe 20 iulie" in titles[0]
    assert "Licitație pentru reabilitare drum" in titles[2]


def test_generic_parser_resolves_relative_and_absolute_hrefs():
    p = _GenericListParser("https://primaria.ro", "div.news-item",
                           title="a.title", date="span.date")
    p.feed(FIXTURE)
    hrefs = [i["href"] for i in p.items]
    assert hrefs[0] == "https://primaria.ro/anunt/1"          # relativ -> absolut
    assert hrefs[1] == "https://primaria.ro/anunt/2"          # deja absolut, pastrat


def test_generic_parser_void_tags_dont_break_depth():
    # <img> in primul item nu trebuie sa dezechilibreze adancimea (item-urile urmatoare ok)
    p = _GenericListParser("https://primaria.ro", "div.news-item",
                           title="a.title", date="span.date")
    p.feed(FIXTURE)
    assert all(i.get("href") and i.get("title") for i in p.items)


def test_generic_parser_default_title_is_first_anchor():
    # fara selector de titlu: ia prima ancora din container (cazul thumb-only ar da /anunt/1)
    html = ('<div class="ni"><a href="/x">Titlu simplu</a>'
            '<a href="/y">al doilea link ignorat</a></div>')
    p = _GenericListParser("https://p.ro", "div.ni")
    p.feed(html)
    assert len(p.items) == 1
    assert p.items[0]["href"] == "https://p.ro/x"
    assert p.items[0]["title"] == "Titlu simplu"


def test_parse_ro_date_formats():
    assert _parse_ro_date("17.07.2026").startswith("2026-07-17")
    assert _parse_ro_date("17/07/2026").startswith("2026-07-17")
    assert _parse_ro_date("2026-07-10").startswith("2026-07-10")
    assert _parse_ro_date("15 iulie 2026").startswith("2026-07-15")
    assert _parse_ro_date("Publicat: 3 decembrie 2025, ora 10").startswith("2025-12-03")


def test_parse_ro_date_garbage_falls_back_to_now():
    # data ilizibila -> nu pica, foloseste momentul curent (an valid)
    out = _parse_ro_date("saptamana trecuta")
    assert out.startswith("20")  # ISO, an 20xx
