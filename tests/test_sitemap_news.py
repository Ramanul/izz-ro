"""Sitemap Google News + `robots.txt` anunta doar fisiere care exista.

Doua goluri masurate pe LIVE, 2026-08-03:

    https://izz.ro/sitemap-news.xml     -> 404
    https://izz.ro/robots.txt           -> anunta sitemap-images.xml neconditionat

Primul e o lipsa: `_write_sitemap` emitea `xmlns` standard + `xmlns:image`, deci un site de
stiri publicat la fiecare doua ore nu avea niciun canal de descoperire rapida.

Al doilea e mai subtil si de asta e testat separat: `sitemap-images.xml` se scrie DOAR daca
exista coperti (`if img_locs`), dar robots il anunta mereu. Pe o rulare fara imagini,
crawlerul primeste un 404 pe un sitemap declarat. Nu s-a manifestat pentru ca productia are
mereu coperti — ceea ce inseamna ca defectul astepta, nu ca lipsea.

Fereastra de 48h e a protocolului, nu a noastra: Google ignora orice intrare mai veche, iar
un fisier plin de intrari ignorate e un semnal prost. Testul care conteaza cel mai mult e
cel de expirare — restul (namespace, campuri) ar pica zgomotos, expirarea ar trece tacut.
"""
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import pytest

from generator import config, render

SM = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
NEWS = "{http://www.google.com/schemas/sitemap-news/0.9}"
NOW = datetime(2026, 8, 3, 12, 0, 0, tzinfo=timezone.utc)


def _art(hours_ago: float, slug: str, **kw) -> dict:
    a = {"category": "general", "slug": slug, "title": f"Titlu {slug}",
         "published": (NOW - timedelta(hours=hours_ago)).isoformat()}
    a.update(kw)
    return a


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    monkeypatch.setattr(render, "_SITEMAPS_WRITTEN", [])
    return tmp_path


def _news_root(out):
    path = os.path.join(str(out), "sitemap-news.xml")
    assert os.path.isfile(path), "sitemap-news.xml nu s-a scris"
    return ET.parse(path).getroot()


def test_doar_articolele_din_fereastra_intra(out):
    """Inima feliei. Un articol expirat nu doar ca e inutil — Google trateaza sitemap-ul
    ca pe unul cu intrari invalide."""
    render._write_news_sitemap(
        [_art(1, "acum"), _art(45.5, "la-limita"), _art(47, "expirat"), _art(200, "vechi")],
        NOW)
    locs = [e.text for e in _news_root(out).iter(SM + "loc")]
    assert any(u.endswith("/acum/") for u in locs)
    assert any(u.endswith("/la-limita/") for u in locs)
    assert not any("expirat" in u or "vechi" in u for u in locs), locs


def test_fereastra_lasa_loc_pentru_un_ciclu_de_cron():
    """Fisierul se scrie o data pe rulare si sta pe live pana la urmatoarea. O fereastra de
    fix 48h ar publica intrari care trec de limita *dupa* generare, fara ca nimic sa le mai
    atinga. Observat pe preview-ul lui #122: valide la generare, invalide 20 de minute mai
    tarziu. Deci fereastra + un interval de cron trebuie sa incapa in cele doua zile."""
    assert render._NEWS_WINDOW_H + render._NEWS_CRON_MARGIN_H <= 48
    assert render._NEWS_CRON_MARGIN_H >= 2, "build.yml ruleaza la 2h (`13 */2`, §17)"


def test_ordinea_e_cronologica_descrescatoare(out):
    render._write_news_sitemap([_art(10, "b"), _art(1, "a"), _art(30, "c")], NOW)
    locs = [e.text for e in _news_root(out).iter(SM + "loc")]
    assert [u.rstrip("/").rsplit("/", 1)[-1] for u in locs] == ["a", "b", "c"]


def test_fiecare_intrare_are_campurile_cerute_de_protocol(out):
    render._write_news_sitemap([_art(2, "stire")], NOW)
    root = _news_root(out)
    news = root.find(f"{SM}url/{NEWS}news")
    assert news is not None, "elementul news:news lipseste"
    assert news.findtext(f"{NEWS}publication/{NEWS}name") == config.SITE["name"]
    assert news.findtext(f"{NEWS}publication/{NEWS}language") == config.SITE["lang"]
    assert news.findtext(f"{NEWS}title") == "Titlu stire"
    assert news.findtext(f"{NEWS}publication_date") == (NOW - timedelta(hours=2)).isoformat()


def test_data_de_publicare_pastreaza_fusul(out):
    """`publication_date` trebuie sa fie W3C datetime cu offset. Un `+00:00` pierdut ar fi
    citit ca ora locala a crawlerului si ar imbatrani articolul cu pana la o zi."""
    render._write_news_sitemap([_art(3, "fus")], NOW)
    raw = _news_root(out).findtext(f"{SM}url/{NEWS}news/{NEWS}publication_date")
    assert datetime.fromisoformat(raw).utcoffset() == timedelta(0)


def test_plafonul_de_1000_e_respectat(out):
    """Limita protocolului. Masurat 2026-08-03: 517 articole in fereastra din 1736 pastrate,
    deci nu musca azi — dar o zi cu volum dublu ar emite un fisier invalid."""
    render._write_news_sitemap([_art(i / 100, f"a{i}") for i in range(1200)], NOW)
    assert len(_news_root(out).findall(f"{SM}url")) == 1000


def test_fara_articole_recente_nu_se_scrie_fisierul(out):
    """Un `<urlset>` gol e XML valid si exact de asta e periculos: ar fi raportat ca sitemap
    gol, nu ca absent."""
    render._write_news_sitemap([_art(72, "vechi")], NOW)
    assert not os.path.exists(os.path.join(str(out), "sitemap-news.xml"))
    assert "sitemap-news.xml" not in render._SITEMAPS_WRITTEN


def test_publicat_nevalid_e_sarit_nu_arunca(out):
    render._write_news_sitemap(
        [_art(1, "bun"), {"category": "general", "slug": "rupt", "published": "ieri"},
         {"category": "general", "slug": "gol"}],
        NOW)
    locs = [e.text for e in _news_root(out).iter(SM + "loc")]
    assert len(locs) == 1 and locs[0].endswith("/bun/")


def test_robots_anunta_doar_sitemapurile_scrise(out):
    """Regresia pe 404: fara coperti nu exista sitemap-images.xml, deci robots nu-l anunta."""
    render._write_sitemap([_art(1, "stire")], now=NOW)
    render._write_robots()
    robots = (out / "robots.txt").read_text(encoding="utf-8")
    url = config.SITE["url"]
    assert f"Sitemap: {url}/sitemap.xml\n" in robots
    assert f"Sitemap: {url}/sitemap-news.xml\n" in robots
    assert "sitemap-images.xml" not in robots
    assert not os.path.exists(os.path.join(str(out), "sitemap-images.xml"))


def test_robots_anunta_imaginile_cand_exista(out):
    render._write_sitemap([_art(1, "stire", cover_url="https://izz.ro/media/x.webp")], now=NOW)
    render._write_robots()
    robots = (out / "robots.txt").read_text(encoding="utf-8")
    assert f"Sitemap: {config.SITE['url']}/sitemap-images.xml\n" in robots
    assert os.path.isfile(os.path.join(str(out), "sitemap-images.xml"))


def test_sitemapul_principal_ramane_fara_namespace_news(out):
    """Protocolul cere doar stiri din 48h in fisierul news; `sitemap.xml` are ~1300 de
    URL-uri, inclusiv ghiduri si pagini legale. Sunt doua fisiere, nu unul."""
    render._write_sitemap([_art(1, "stire"), _art(100, "vechi")], now=NOW)
    raw = (out / "sitemap.xml").read_text(encoding="utf-8")
    assert "sitemap-news/0.9" not in raw
    assert "/vechi/" in raw, "articolele vechi raman in sitemap-ul standard"
