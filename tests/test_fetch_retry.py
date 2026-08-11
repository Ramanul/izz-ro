"""Un 429 e un refuz temporar, nu o sursa moarta.

Feedcheck 2026-07-24 (run 30093310671): libertatea, unica si bzi au raspuns 429 de pe
runnerii GitHub. `build.yml` ruleaza pe aceiasi runneri, deci productia le pierdea la
prima incercare, desi feed-urile sunt vii.
"""
import urllib.error

import pytest

from generator import fetch


class _FakeResponse:
    """Context manager minimal, cat sa treaca prin `with urllib.request.urlopen(...)`."""

    def __init__(self, body: bytes):
        self._body = body
        self.headers = {}

    def read(self, amt=None):
        """`amt` exista fiindca `HTTPResponse.read` il are, si `fetch._read_limitat` il
        foloseste ca sa plafoneze raspunsul. Un fake fara el ascundea plafonul."""
        return self._body if amt is None else self._body[:amt]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _http_error(code: int, retry_after=None):
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else {}
    return urllib.error.HTTPError(
        url="https://example.invalid/feed", code=code, msg="nope", hdrs=headers, fp=None)


@pytest.fixture
def no_sleep(monkeypatch):
    """Testele nu asteapta cu adevarat; retinem cat S-AR fi asteptat."""
    slept = []
    monkeypatch.setattr(fetch.time, "sleep", lambda s: slept.append(s))
    return slept


def _patch_urlopen(monkeypatch, responses):
    """`responses`: lista de exceptii sau bytes, consumate in ordine, cate una per apel."""
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(getattr(req, "full_url", req))
        result = responses[len(calls) - 1]
        if isinstance(result, Exception):
            raise result
        return _FakeResponse(result)

    monkeypatch.setattr(fetch.urllib.request, "urlopen", fake_urlopen)
    return calls


SOURCE = {"url": "https://example.invalid/feed", "name": "Example",
          "category": "general", "lang": "ro"}

# Un RSS minimal, cat sa produca un item real prin feedparser.
RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>
<item><title>Stire</title><link>https://example.invalid/a</link></item>
</channel></rss>"""


def test_429_apoi_200_reuseste(monkeypatch, no_sleep):
    """(a) Un refuz temporar urmat de succes NU trebuie sa piarda sursa."""
    calls = _patch_urlopen(monkeypatch, [_http_error(429), RSS])

    items, err = fetch._fetch_one("ex", SOURCE)

    assert err is None
    assert len(items) == 1 and items[0]["original_title"] == "Stire"
    assert len(calls) == 2
    assert no_sleep == [fetch.RETRY_BACKOFF[0]]


def test_429_permanent_ajunge_sursa_moarta(monkeypatch, no_sleep):
    """(b) Daca 429 persista, sursa e moarta — dar dupa exact 1 + RETRY_ATTEMPTS incercari."""
    calls = _patch_urlopen(monkeypatch, [_http_error(429)] * (fetch.RETRY_ATTEMPTS + 1))

    items, err = fetch._fetch_one("ex", SOURCE)

    assert items == []
    assert err.startswith("ex: ") and "429" in err
    assert len(calls) == fetch.RETRY_ATTEMPTS + 1
    assert no_sleep == list(fetch.RETRY_BACKOFF[:fetch.RETRY_ATTEMPTS])


def test_retry_after_prea_mare_renunta_imediat(monkeypatch, no_sleep):
    """(c) Un `Retry-After` peste plafon: renuntam, nu blocam un worker din pool."""
    calls = _patch_urlopen(monkeypatch, [_http_error(429, retry_after=fetch.RETRY_AFTER_CAP + 1)])

    items, err = fetch._fetch_one("ex", SOURCE)

    assert items == [] and "429" in err
    assert len(calls) == 1, "nu trebuie sa reincerce"
    assert no_sleep == [], "nu trebuie sa astepte deloc"


def test_retry_after_sub_plafon_e_respectat(monkeypatch, no_sleep):
    """Serverul are ultimul cuvant cand cere o pauza rezonabila."""
    _patch_urlopen(monkeypatch, [_http_error(429, retry_after=2), RSS])

    items, err = fetch._fetch_one("ex", SOURCE)

    assert err is None and len(items) == 1
    assert no_sleep == [2.0], "trebuie sa respecte Retry-After, nu backoff-ul propriu"


def test_404_e_mort_din_prima(monkeypatch, no_sleep):
    """(d) Erorile permanente nu merita reincercate — ar irosi timp in fiecare build."""
    calls = _patch_urlopen(monkeypatch, [_http_error(404)])

    items, err = fetch._fetch_one("ex", SOURCE)

    assert items == [] and "404" in err
    assert len(calls) == 1
    assert no_sleep == []


def test_304_ramane_sursa_sanatoasa(monkeypatch, no_sleep):
    """Regresie: 304 inseamna 'neschimbat', nu eroare — si nu se reincearca."""
    calls = _patch_urlopen(monkeypatch, [_http_error(304)])

    items, err = fetch._fetch_one("ex", SOURCE)

    assert items == [] and err is None
    assert len(calls) == 1
    assert no_sleep == []
