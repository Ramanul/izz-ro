"""Corpus adversarial pentru redirectare/SSRF la ingestie (PLAN UNIFICAT #9).

CE DOVEDESTE. `guard.url_ostil` verifica LEXICAL, fara DNS, si lasa deliberat un gol numit in
propriul docstring: „un domeniu public care REZOLVA catre o adresa interna trece de aici; ala
e treaba lui `fetch._deschizator_sigur`, care verifica fiecare salt de redirectare".

Masurat pe 2026-09-11: `grep -rn deschizator_sigur` peste tot repo-ul returna O SINGURA
aparitie — chiar citarea din `guard.py:202`. Nu exista nici functia, nici vreun opener sau
handler de redirectare in `fetch.py`, iar `urllib.request.urlopen` urmeaza redirecturile
implicit. Compensarea declarata era un mecanism fantoma, pe un control de securitate.

Calea reala, nu ipotetica: `_parse_sitemap_news` valideaza cu `url_ostil` `<loc>`-ul unui
sitemap TERT, apoi `_fetch_meta_description` cere acel URL si ii pune raspunsul in
`description`, adica in corpusul publicabil. Un `<loc>` catre un domeniu public care raspunde
`302 -> http://169.254.169.254/latest/meta-data/` trecea de garda si era urmat.

CUM E CONSTRUIT TESTUL. Server HTTP local pe `127.0.0.1`, deci deterministic si fara retea
externa. Tinta redirectarii e tot serverul local: daca garda cedeaza, cererea REUSESTE repede
si testul vede continutul intern (semnal clar de esec), in loc sa atarne pe o adresa
neroutabila. `test_urlopen_gol_chiar_urmeaza_redirectul` pastreaza dovada ca golul era real:
stdlib-ul, fara opener, chiar urmeaza saltul.
"""
from __future__ import annotations

import http.server
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from generator import fetch

SECRET = "continut-intern-care-nu-trebuie-sa-iasa"
PAGINA_INTERNA = (
    f'<html><head><meta name="description" content="{SECRET}"></head><body></body></html>'
)
PAGINA_PUBLICA = '<html><head><meta name="description" content="descriere legitima"></head></html>'


class _Handler(http.server.BaseHTTPRequestHandler):
    """/redirect -> 302 catre /intern (aceeasi gazda locala); /intern si /public servesc HTML."""

    def do_GET(self):  # noqa: N802 — nume impus de BaseHTTPRequestHandler
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{self.server.server_port}/intern")
            self.end_headers()
            return
        if self.path == "/relativ":
            self.send_response(302)
            self.send_header("Location", "/intern")   # relativ, ca in realitate
            self.end_headers()
            return
        corp = (PAGINA_INTERNA if self.path == "/intern" else PAGINA_PUBLICA).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corp)))
        self.end_headers()
        self.wfile.write(corp)

    def log_message(self, *_args):
        pass  # fara zgomot in iesirea pytest


@pytest.fixture(scope="module")
def server():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    fir = threading.Thread(target=srv.serve_forever, daemon=True)
    fir.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()
    srv.server_close()


def test_urlopen_gol_chiar_urmeaza_redirectul(server):
    """Dovada ca golul era real: stdlib-ul, fara opener, ajunge la tinta interna.

    Daca acest test incepe sa pice, `urllib` si-a schimbat comportamentul implicit si
    motivarea gardii trebuie recitita — nu sters testul.
    """
    with urllib.request.urlopen(f"{server}/redirect", timeout=5) as resp:
        assert SECRET in resp.read().decode()


def test_redirect_catre_gazda_interna_e_refuzat(server):
    with pytest.raises(urllib.error.HTTPError) as exc:
        fetch._deschizator_sigur().open(f"{server}/redirect", timeout=5)
    assert "redirectare refuzata de garda" in str(exc.value)


def test_meta_description_nu_extrage_prin_redirect_intern(server):
    """Capatul care conteaza: nimic din spatele redirectarii nu ajunge in corpus."""
    assert fetch._fetch_meta_description(f"{server}/redirect") == ""


def test_pagina_fara_redirect_se_citeste_normal(server):
    """Granita: garda apara SALTURILE, nu blocheaza cererea initiala a apelantului.

    URL-ul initial ramane treaba lui `url_ostil`, aplicat de `_parse_sitemap_news` inainte de
    fetch; daca garda ar refuza si prima cerere, ar dubla verificarea in locul gresit."""
    assert fetch._fetch_meta_description(f"{server}/public") == "descriere legitima"


@pytest.mark.parametrize("tinta", [
    "http://169.254.169.254/latest/meta-data/",
    "http://127.0.0.1:8080/admin",
    "http://localhost/",
    "http://10.0.0.5/",
    "http://[::1]/",
    "http://metadata.google.internal/computeMetadata/v1/",
    "file:///etc/passwd",
    "gopher://127.0.0.1:11211/",
    "https://izz.ro@evil.example/",
])
def test_tintele_de_redirectare_ostile_sunt_toate_respinse(tinta):
    """Corpusul propriu-zis. Nu trece prin retea: verifica predicatul pe care il foloseste
    handlerul, ca lista sa poata creste fara sa creasca si timpul suitei."""
    assert fetch.guard.url_ostil(tinta) is not None, tinta


@pytest.mark.parametrize("tinta", [
    "https://digi24.ro/stiri/actualitate/x",
    "http://primariatm.ro/noutati/anunt",
    "https://www.libertatea.ro/stiri/1",
])
def test_tintele_de_redirectare_legitime_trec(tinta):
    """Cealalta directie: o garda care respinge tot nu e o garda, e o pana."""
    assert fetch.guard.url_ostil(tinta) is None, tinta


def test_location_relativ_ajunge_absolut_la_garda(server, monkeypatch):
    """Premisa fara de care garda ar rupe redirecturi legitime — masurata, nu presupusa.

    `url_ostil` respinge orice nu incepe cu http/https. Daca handlerul ar primi `Location`-ul
    brut, un `Location: /pagina` (relativ, perfect legal si foarte raspandit) ar fi citit ca
    „schema de URL nepermisa" si ORICE sursa care redirecteaza relativ ar muri tacut.

    Masurat: `urllib` rezolva `Location` fata de URL-ul cererii INAINTE de `redirect_request`,
    deci garda vede mereu un URL absolut. Testul tine premisa asta sub observatie; daca pica,
    garda trebuie sa rezolve ea `newurl`, nu sa fie slabita.
    """
    vazute = []
    original = fetch._RedirectVerificat.redirect_request

    def spion(self, req, fp, code, msg, headers, newurl):
        vazute.append(newurl)
        return original(self, req, fp, code, msg, headers, newurl)

    monkeypatch.setattr(fetch._RedirectVerificat, "redirect_request", spion)
    fetch._fetch_meta_description(f"{server}/relativ")

    assert vazute, "handlerul nu a fost chemat deloc"
    assert vazute[0].startswith("http://"), f"Location nerezolvat: {vazute[0]!r}"
    assert vazute[0].endswith("/intern")


def test_nicio_iesire_in_retea_nu_ocoleste_cusatura():
    """Garda pe INVARIANT, nu pe apelurile de azi.

    `_deschide` aplica politica doar daca toate cererile trec pe acolo. Un apel nou scris
    direct cu `urllib.request.urlopen(` ar reintroduce golul tacut — exact modul in care a
    aparut prima data. Aici se vede la prima rulare, nu peste sase luni.
    """
    sursa = (Path(fetch.__file__)).read_text(encoding="utf-8")
    linii = [
        f"  fetch.py:{nr}: {linie.strip()}"
        for nr, linie in enumerate(sursa.splitlines(), 1)
        if "urllib.request.urlopen(" in linie and not linie.lstrip().startswith("#")
        and "`urllib.request.urlopen(`" not in linie
    ]
    assert not linii, "apel direct in retea, in afara lui _deschide:\n" + "\n".join(linii)
