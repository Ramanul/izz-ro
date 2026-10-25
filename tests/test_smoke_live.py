"""Teste pentru sondele de challenge si reincercarile din `tools/smoke_live.py`.

Context (masurat 2026-10-11): smoke-live a picat o data (rularea 38035435047, 10 oct) si nu s-a
putut diagnostica — jurnalele binare ale jobului nu sunt accesibile din sandbox (`gh run view
--log-failed` -> EOF), iar adnotarea automata spune doar „exit code 1”. De aceea scriptul:
  - reincearca o data erorile TRANZITORII (retea, 5xx), ca monitor.yml,
  - trateaza un bot challenge Cloudflare ca INCONCLUIENT (acelasi principiu ca deploy-failover.yml
    si monitor.yml), reluand probele pe originea de build,
  - scrie adnotari `::error title=smoke live::` cu fiecare regula incalcata.

Testele de aici nu ating reteaua: acopera doar decizia, nu cererea HTTP.
"""
import importlib
import io
import os
import sys
import urllib.error

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
smoke = importlib.import_module("tools.smoke_live")


def _http_error(code: int, body: bytes = b"", headers: dict | None = None) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://izz.ro/", code, "err", headers or {}, io.BytesIO(body))


@pytest.fixture(autouse=True)
def _fara_somn(monkeypatch):
    """Suita nu sta 5 secunde degeaba intre incercari."""
    monkeypatch.setattr(smoke.time, "sleep", lambda _s: None)


# --- detectia challenge-ului --------------------------------------------------------------
def test_challenge_prin_antet_si_prin_corp():
    assert smoke._e_challenge(_http_error(403, headers={"cf-mitigated": "challenge"}))
    assert smoke._e_challenge(_http_error(403, b"<html>Just a moment...</html>"))
    assert smoke._e_challenge(_http_error(503, b"<html><script>window.__cf_chl</script></html>"))


def test_challenge_fara_antet_e_recunoscut_si_la_a_doua_citire():
    """Regresie (recenzia Gemini pe PR #474): acelasi `HTTPError` trece de doua ori prin
    `_e_challenge` — o data in reincercare, o data la alegerea originii. `read()` consuma
    stream-ul, deci fara cache un challenge servit cu 503 si fara antet `cf-mitigated` ar fi
    ratat exact pe drumul spre fallback."""
    exc = _http_error(503, b"<html>Just a moment...</html>")
    assert smoke._e_challenge(exc), "prima citire vede corpul"
    assert smoke._e_challenge(exc), "a doua citire foloseste corpul din cache"
    # Corpul se citeste o singura data: stream-ul e deja la EOF dupa prima trecere.
    assert exc.read() == b""


def test_eroarea_obisnuita_nu_e_challenge():
    assert not smoke._e_challenge(_http_error(404, b"<html>pagina lipseste</html>"))
    assert not smoke._e_challenge(_http_error(500, b"<html>eroare server</html>"))
    # O eroare de retea nu e challenge (nu are raspuns de la server).
    assert not smoke._e_challenge(urllib.error.URLError("connection refused"))
    assert not smoke._e_challenge(TimeoutError("timed out"))


def test_interstitial_servit_cu_200():
    assert smoke._interstitial("<html><title>Just a moment...</title></html>")
    assert not smoke._interstitial("<html><title>Portalul știrilor tale</title></html>")


# --- reincercarea pe erori tranzitorii ----------------------------------------------------
def test_reincercarea_esueaza_o_data_apoi_reuseste(monkeypatch):
    apeluri = {"n": 0}

    def get_uneori_rau(path):
        apeluri["n"] += 1
        if apeluri["n"] == 1:
            raise urllib.error.URLError("connection reset")
        return "<html>ok</html>"

    monkeypatch.setattr(smoke, "get", get_uneori_rau)
    monkeypatch.setattr(smoke.time, "sleep", lambda _s: None)

    assert smoke._get_cu_reincercare("/") == "<html>ok</html>"
    assert apeluri["n"] == 2


def test_5xx_se_reincearca_dar_404_nu(monkeypatch):
    apeluri = {"n": 0}

    def get_5xx(path):
        apeluri["n"] += 1
        raise _http_error(502, b"bad gateway")

    monkeypatch.setattr(smoke, "get", get_5xx)
    monkeypatch.setattr(smoke.time, "sleep", lambda _s: None)
    with pytest.raises(urllib.error.HTTPError):
        smoke._get_cu_reincercare("/")
    assert apeluri["n"] == 2, "5xx e tranzitoriu, se reincearca"

    apeluri["n"] = 0

    def get_404(path):
        apeluri["n"] += 1
        raise _http_error(404, b"lipseste")

    monkeypatch.setattr(smoke, "get", get_404)
    with pytest.raises(urllib.error.HTTPError):
        smoke._get_cu_reincercare("/")
    assert apeluri["n"] == 1, "404 e raspuns de site, nu pana de retea"


def test_challenge_nu_se_reincearca_pe_acelasi_domeniu(monkeypatch):
    """Un challenge nu se rezolva cu o a doua cerere: se schimba originea, nu ritmul."""
    apeluri = {"n": 0}

    def get_challenge(path):
        apeluri["n"] += 1
        raise _http_error(403, headers={"cf-mitigated": "challenge"})

    monkeypatch.setattr(smoke, "get", get_challenge)
    with pytest.raises(urllib.error.HTTPError):
        smoke._get_cu_reincercare("/")
    assert apeluri["n"] == 1


# --- alegerea originii --------------------------------------------------------------------
def test_pe_challenge_probele_continua_pe_originea_de_build(monkeypatch):
    monkeypatch.setattr(smoke, "BASE", "https://izz.ro")
    monkeypatch.setattr(smoke, "FALLBACK", "https://build.example")
    probat = {"base": None}

    def guarded_challenge(path):
        raise _http_error(403, headers={"cf-mitigated": "challenge"})

    def get_pe_fallback(path):
        probat["base"] = smoke.BASE
        return "<html>Portalul știrilor tale</html>"

    monkeypatch.setattr(smoke, "_get_cu_reincercare", guarded_challenge)
    monkeypatch.setattr(smoke, "get", get_pe_fallback)

    home = smoke._alege_originea()

    assert "Portalul" in home
    assert smoke.BASE == "https://build.example"
    assert probat["base"] == "https://build.example", "cererea de dupa fallback merge pe origine noua"


def test_challenge_503_fara_antet_trece_prin_reincercare_pana_la_fallback(monkeypatch):
    """Traseul complet din recenzia Gemini: izz.ro serveste 503 „Just a moment” (fara
    `cf-mitigated`). `_get_cu_reincercare` vede 5xx, intreaba `_e_challenge` (prima citire),
    apoi `_alege_originea` intreaba din nou acelasi obiect (a doua citire) — fallback doar
    daca ambele raspund corect."""
    monkeypatch.setattr(smoke, "BASE", "https://izz.ro")
    monkeypatch.setattr(smoke, "FALLBACK", "https://build.example")

    def get_oriunde(path):
        if smoke.BASE == "https://izz.ro":
            raise _http_error(503, b"<html>Just a moment...</html>")
        return "<html>Portalul știrilor tale</html>"

    monkeypatch.setattr(smoke, "get", get_oriunde)

    home = smoke._alege_originea()

    assert "Portalul" in home
    assert smoke.BASE == "https://build.example", "challenge-ul 503 a comutat pe origine"


def test_fara_challenge_ramane_pe_domeniu(monkeypatch):
    monkeypatch.setattr(smoke, "BASE", "https://izz.ro")
    monkeypatch.setattr(smoke, "_get_cu_reincercare",
                        lambda path: "<html>Portalul știrilor tale</html>")

    smoke._alege_originea()

    assert smoke.BASE == "https://izz.ro", "fallback doar la challenge, nu preventiv"


def test_o_eroare_reala_nu_e_mascata_de_fallback(monkeypatch):
    """Daca izz.ro raspunde cu 500, nu e „challenge” — eroarea trebuie sa iasa, nu sa fie
    transformata in verde pe originea de build."""
    monkeypatch.setattr(smoke, "BASE", "https://izz.ro")
    monkeypatch.setattr(smoke, "FALLBACK", "https://build.example")

    def get_500(path):
        raise _http_error(500, b"eroare server")

    monkeypatch.setattr(smoke, "get", get_500)

    with pytest.raises(urllib.error.HTTPError):
        smoke._alege_originea()
    assert smoke.BASE == "https://izz.ro"


@pytest.mark.parametrize("html", [
    '<aside id="editorial-copy-status" class="notice" role="status" hidden></aside>',
    '<aside class="notice" aria-label="Corecție editorială">Corecție</aside>',
    '<aside class="notice dialectic-update">Actualizare sinteză</aside>',
    '<p class="verification-note">Notă pentru cititor</p>',
])
def test_functional_notices_do_not_trigger_retired_disclaimer(html):
    assert not smoke._ArticleMarkup(html).legacy_notice


@pytest.mark.parametrize("html", [
    '<p class="notice">IZZ.ro reformulează titlul și extrage faptele.</p>',
    "<p id='old-method' class='extra notice'>Pentru toate detaliile, mergi la sursă.</p>",
])
def test_retired_method_paragraph_still_fails(html):
    assert smoke._ArticleMarkup(html).legacy_notice


def test_article_without_optional_photo_does_not_request_or_fail(monkeypatch):
    monkeypatch.setattr(smoke, "fails", [])

    def unexpected_request(*args, **kwargs):
        pytest.fail("A text-only article must not require a decorative image")

    monkeypatch.setattr(smoke.http.client, "HTTPSConnection", unexpected_request)
    smoke._check_article_images(smoke._ArticleMarkup('<p class="body">Știre</p>'), "/text/")
    assert smoke.fails == []


@pytest.mark.parametrize("html", [
    '<img src="/photo.jpg" class="extra article-art">',
    '<figure class="arhiva-foto"><img src="/photo.jpg"></figure>',
])
@pytest.mark.parametrize("result,passes", [
    ("image", True), ("html", False), ("small", False), ("404", False),
])
def test_present_article_and_archive_photos_must_load(monkeypatch, html, result, passes):
    monkeypatch.setattr(smoke, "fails", [])
    requested = []

    class Connection:
        def __init__(self, host, port, timeout):
            assert host == "izz.ro"
            self.status = 404 if result == "404" else 200

        def request(self, method, path, headers):
            assert method == "GET"
            requested.append(smoke.BASE + path)

        def getresponse(self):
            return self

        def getheader(self, name, default):
            return "text/html" if result == "html" else "image/jpeg"

        def read(self):
            return b"x" * (100 if result == "small" else 6000)

        def close(self):
            pass

    monkeypatch.setattr(smoke.http.client, "HTTPSConnection", Connection)
    smoke._check_article_images(smoke._ArticleMarkup(html), "/photo/")
    assert requested == [smoke.BASE + "/photo.jpg"]
    assert (not smoke.fails) is passes


def test_empty_photo_src_fails_and_unrelated_images_are_ignored(monkeypatch):
    monkeypatch.setattr(smoke, "fails", [])
    markup = smoke._ArticleMarkup(
        '<figure class="arhiva-foto"><img src=""></figure><img src="/logo.svg">'
    )
    assert markup.images == [""]
    smoke._check_article_images(markup, "/broken/")
    assert len(smoke.fails) == 1


@pytest.mark.parametrize("source", ["file:///etc/passwd", "ftp://host/photo.jpg"])
def test_photo_probe_rejects_non_http_schemes(monkeypatch, source):
    monkeypatch.setattr(smoke, "fails", [])

    def unexpected_connection(*args, **kwargs):
        pytest.fail("Unsupported schemes must not start a connection")

    monkeypatch.setattr(smoke.http.client, "HTTPSConnection", unexpected_connection)
    smoke._check_article_images(smoke._ArticleMarkup(f'<img class="article-art" src="{source}">'),
                                "/unsupported/")
    assert len(smoke.fails) == 1
