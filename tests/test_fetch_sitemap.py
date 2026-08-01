"""Parser de sitemap Google News (surse fara RSS, ex. piataauto.md). Verificat pe
fixture XML realist — sandbox-ul n-are internet, dar parserul e Python pur.

Regresie (iulie 2026): sursa raspundea 200 cu <url>-uri valide, dar toate intrarile
erau sarite in tacere -> 0 articole SI 0 erori, deci nu aparea nici in lista surselor
moarte. Un esec tacut e mai rau decat unul zgomotos: degradeaza nevazut."""
from generator import config
from generator.fetch import _parse_sitemap_news

SRC = {"name": "Piata Auto MD", "category": "auto"}

NS = ('xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
      'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"')


def _entry(loc: str, title: str | None = "Titlu", date: str = "2026-07-24") -> str:
    news = "" if title is None else (
        f"<news:news><news:title>{title}</news:title>"
        f"<news:publication_date>{date}</news:publication_date></news:news>")
    return f"<url><loc>{loc}</loc>{news}</url>"


def _doc(entries: str) -> bytes:
    return f'<?xml version="1.0"?><urlset {NS}>{entries}</urlset>'.encode()


def test_parses_valid_entries():
    raw = _doc(_entry("https://piataauto.md/a", "Dacia lansează un model nou")
               + _entry("https://piataauto.md/b", "Test drive electric"))
    items, err = _parse_sitemap_news(raw, "piataauto", SRC)
    assert err is None
    assert [i["title"] for i in items] == ["Dacia lansează un model nou", "Test drive electric"]
    assert items[0]["category"] == "auto"
    assert items[0]["published"].startswith("2026-07-24")


def test_entries_without_title_are_reported_not_silent():
    """Structura schimbata (fara news:title) -> eroare explicita, nu lista goala tacuta."""
    raw = _doc("".join(_entry(f"https://piataauto.md/{i}", None) for i in range(3)))
    items, err = _parse_sitemap_news(raw, "piataauto", SRC)
    assert items == []
    assert err is not None
    assert "0 utilizabile" in err and "3" in err


def test_cap_applies_after_filtering():
    """Plafonul MAX_PER_SOURCE se aplica pe intrarile BUNE, nu pe felia bruta."""
    bad = "".join(_entry(f"https://piataauto.md/x{i}", None) for i in range(config.MAX_PER_SOURCE))
    good = "".join(_entry(f"https://piataauto.md/g{i}", f"Stire {i}") for i in range(3))
    items, err = _parse_sitemap_news(_doc(bad + good), "piataauto", SRC)
    assert err is None
    assert len(items) == 3


def test_cap_is_enforced():
    good = "".join(_entry(f"https://piataauto.md/g{i}", f"Stire {i}") for i in range(20))
    items, _ = _parse_sitemap_news(_doc(good), "piataauto", SRC)
    assert len(items) == config.MAX_PER_SOURCE


def test_empty_sitemap_reports_error():
    items, err = _parse_sitemap_news(_doc(""), "piataauto", SRC)
    assert items == [] and "0 intrari" in err


def test_invalid_xml_reports_error():
    items, err = _parse_sitemap_news(b"<nu-e-xml", "piataauto", SRC)
    assert items == [] and "XML invalid" in err
