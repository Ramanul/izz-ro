"""O sursa care raspunde 200 si nu produce niciun articol trebuie sa se VADA.

`fetch_all()` aduna in `dead` doar sursele care au dat EROARE. O sursa care raspunde 200
si al carei feed nu produce nimic iesea tacut din corpus: nu aparea nici in `dead`, nici
altundeva. #98 a inchis exact gaura asta pentru `sitemap_news` (piataauto, iulie 2026);
testul asta o inchide si pentru RSS si pentru listele HTML.

De ce conteaza, masurat 2026-08-02: feedcheck-ul de pe runnerii GitHub raporteaza 76 de
surse fara articole, iar aceleasi surse dau 8 articole fiecare de pe IP-ul de acasa
(`recorder`, `contributors`, `zch`, `stirilemoldovei`, `cronicaolteniei`, `stirimuntenia`,
`stirileolteniei` — toate 8/8, err=None). Productia ruleaza pe acei runneri si citeste
~861 articole unde o rulare locala citeste ~1428. Diferenta nu se vedea in niciun raport.

Ce NU trebuie sa se schimbe: un 304 („feed neschimbat") ramane sanatos, nu devine sursa
moarta. Aia e cazul in care zero articole e raspunsul corect.
"""
import urllib.error

import pytest

from generator import fetch


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body
        self.headers = {}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


RSS_CU_ARTICOLE = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Titlu real</title><link>https://exemplu.ro/a</link></item>
</channel></rss>"""

RSS_GOL = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<title>Feed fara intrari</title>
</channel></rss>"""

RSS_INTRARI_INUTILIZABILE = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Fara link</title></item>
<item><link>https://exemplu.ro/b</link></item>
</channel></rss>"""

NU_E_FEED = b"<html><body>Acces restrictionat</body></html>"

SURSA = {"url": "https://exemplu.ro/feed", "name": "Exemplu", "category": "general"}


@pytest.fixture
def raspunde(monkeypatch):
    def _set(body):
        monkeypatch.setattr(fetch.urllib.request, "urlopen",
                            lambda req, timeout=None: _FakeResponse(body))
    return _set


def test_feed_valid_nu_raporteaza_nimic(raspunde):
    raspunde(RSS_CU_ARTICOLE)
    items, err = fetch._fetch_one("exemplu", SURSA, cache={})
    assert len(items) == 1
    assert err is None


@pytest.mark.parametrize("corp,eticheta", [
    (RSS_GOL, "feed gol"),
    (RSS_INTRARI_INUTILIZABILE, "intrari fara link/titlu"),
    (NU_E_FEED, None),
])
def test_zero_articole_devine_sursa_moarta(raspunde, corp, eticheta):
    raspunde(corp)
    items, err = fetch._fetch_one("exemplu", SURSA, cache={})
    assert items == []
    assert err is not None, "sursa a iesit goala si tacuta — exact regresia de evitat"
    assert "exemplu" in err and "0 articole" in err
    if eticheta:
        assert eticheta in err


def test_304_ramane_sanatos(monkeypatch):
    """Zero articole e raspunsul CORECT aici — sursa nu are nimic nou, nu e moarta."""
    def _304(req, timeout=None):
        raise urllib.error.HTTPError(url=SURSA["url"], code=304, msg="Not Modified",
                                     hdrs={}, fp=None)
    monkeypatch.setattr(fetch.urllib.request, "urlopen", _304)
    items, err = fetch._fetch_one("exemplu", SURSA, cache={})
    assert items == []
    assert err is None


def test_sursa_moarta_ajunge_in_lista_din_fetch_all(monkeypatch, raspunde):
    """Verificarea la nivelul la care conteaza: raportul rularii."""
    monkeypatch.setattr(fetch.config, "SOURCES", {"exemplu": SURSA})
    monkeypatch.setattr(fetch, "_cache_load", lambda: {})
    monkeypatch.setattr(fetch, "_cache_save", lambda c: None)
    raspunde(RSS_GOL)
    items, dead = fetch.fetch_all()
    assert items == []
    assert len(dead) == 1 and "exemplu" in dead[0]
