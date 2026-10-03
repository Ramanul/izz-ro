"""PWA instalabilă cu citire offline: manifest, service worker, buton de instalare, alertă.

DE CE EXISTĂ TESTELE ASTEA, ȘI CE PRIND. Trei defecte din această suprafață NU se văd în
Python și nici în CI-ul obișnuit:

  · un service worker publicat la `/static/sw.js` nu controlează decât `/static/` — site-ul
    s-ar „instala" fără să poată funcționa offline. De aici testul că ajunge la RĂDĂCINĂ și
    că NU ajunge și în `/static/`;
  · un buton de instalare care apare în header împinge tot conținutul în jos cu 49 px —
    măsurat pe 2026-08-02, 100% din CLS-ul de 0.272 era al lui (`specs/masuratori-frontend.md`).
    De aici testul că butonul NU e în `<nav>` și că e scos din flux (`position: fixed`);
  · un `display: flex` pe containerul butonului bate atributul `hidden`, deci butonul s-ar
    vedea la toată lumea, nu doar la cei cărora browserul le poate oferi instalarea.

Cele trei teste de SURSĂ (pe `static/*.js`) sunt marcate ca atare: repo-ul n-are runner de
JS în pytest, deci ele apără proprietăți de formă, NU comportamentul. Comportamentul
criptării și al rutelor e verificat rulând codul, în `tests/test_push_criptare.py` și
`tests/test_push_rute.py`.
"""
from __future__ import annotations

import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from generator import render  # noqa: E402

STATIC = os.path.join(ROOT, "static")
TEMPLATES = os.path.join(ROOT, "templates")


def _citeste(cale: str) -> str:
    with open(cale, encoding="utf-8") as fh:
        return fh.read()


def _sw() -> str:
    return _citeste(os.path.join(STATIC, "sw.js"))


# --- manifest --------------------------------------------------------------------

def test_manifestul_e_complet_si_valid():
    manifest = json.loads(_citeste(os.path.join(STATIC, "site.webmanifest")))
    for camp in ("name", "short_name", "start_url", "scope", "display", "icons", "id"):
        assert manifest.get(camp), f"manifestul n-are `{camp}` — instalarea refuza fara el"
    assert manifest["start_url"].startswith("/") and manifest["scope"] == "/"
    assert manifest["lang"] == "ro"
    assert manifest["display"] == "standalone"


def test_pictogramele_din_manifest_exista_pe_disc():
    """O pictogramă lipsă nu oprește instalarea — doar o face cu o iconiță goală. Tăcut."""
    manifest = json.loads(_citeste(os.path.join(STATIC, "site.webmanifest")))
    assert len(manifest["icons"]) >= 2
    for ico in manifest["icons"]:
        cale = os.path.join(ROOT, ico["src"].lstrip("/"))
        assert os.path.isfile(cale), f"{ico['src']} e in manifest, dar nu exista in repo"
    # Fara macar una `maskable`, Androidul decupeaza singur iconita si taie din logo.
    assert any("maskable" in ico.get("purpose", "") for ico in manifest["icons"])


def test_scurtaturile_duc_la_rute_reale():
    manifest = json.loads(_citeste(os.path.join(STATIC, "site.webmanifest")))
    assert manifest["shortcuts"], "fara shortcuts, aplicatia instalata n-are meniu lung"
    for sc in manifest["shortcuts"]:
        assert sc["url"].startswith("/") and sc["name"], sc


# --- service worker --------------------------------------------------------------

def test_sw_ajunge_la_radacina(tmp_path, monkeypatch):
    """Un SW la /static/ nu vede decât /static/ — deci niciun articol. Vezi docstring."""
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    render._write_sw()
    radacina = tmp_path / "sw.js"
    assert radacina.is_file(), "service workerul nu s-a scris la radacina"
    assert radacina.read_text(encoding="utf-8") == _sw()


def test_sw_nu_ajunge_si_in_static(tmp_path, monkeypatch):
    """Cazul negativ al excluderii: dacă `sw.js` e în `static/`, trebuie să NU fie copiat."""
    static_sursa = tmp_path / "static"
    static_sursa.mkdir()
    (static_sursa / "sw.js").write_text("// sw", encoding="utf-8")
    (static_sursa / "styles.css").write_text("body{}", encoding="utf-8")
    iesire = tmp_path / "out"
    iesire.mkdir()
    monkeypatch.setattr(render, "STATIC_DIR", str(static_sursa))
    monkeypatch.setattr(render, "OUT_DIR", str(iesire))
    render._copy_static()
    assert (iesire / "static" / "styles.css").is_file(), "copierea nu mai copiaza nimic"
    assert not (iesire / "static" / "sw.js").exists(), (
        "sw.js a ajuns si in /static/: fisier irosit si al doilea service worker posibil")


def test_sw_fara_sursa_nu_opreste_randarea(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    monkeypatch.setattr(render, "_SW_SRC", str(tmp_path / "nu-exista.js"))
    render._write_sw()   # nu trebuie sa arunce
    assert not (tmp_path / "sw.js").exists()


@pytest.mark.parametrize("cheie", ["/", "/offline/", "/static/styles.css", "/static/pwa.js",
                                   "/static/push.js", "/static/fonts/Inter-400.ro.woff2"])
def test_precache_contine_doar_ce_exista(cheie):
    """O intrare greșită în precache face ca instalarea să pice, deci SW-ul să nu existe."""
    sw = _sw()
    lista = re.search(r"const PRECACHE = \[(.*?)\];", sw, re.S).group(1)
    # `/offline/` sta in constanta OFFLINE, ca acelasi sir sa nu apara in trei locuri.
    constante = dict(re.findall(r"const (OFFLINE) = '([^']+)'", sw))
    assert f"'{cheie}'" in lista or constante.get("OFFLINE") == cheie, (
        f"{cheie} lipseste din precache — offline-ul e partial")
    if cheie.startswith("/static/"):
        assert os.path.isfile(os.path.join(ROOT, cheie.lstrip("/"))), cheie


def test_precache_ramane_mic():
    """Fiecare intrare se descarcă la instalare: costul e plătit de vizitator, nu de noi."""
    lista = re.findall(r"'([^']+)'", re.search(r"const PRECACHE = \[(.*?)\];", _sw(), re.S).group(1))
    assert 5 <= len(lista) <= 25, f"{len(lista)} intrari in precache: prea putine sau prea multe"


def test_sw_nu_intercepteaza_post_si_push():
    sw = _sw()
    assert "request.method !== 'GET'" in sw, "un SW care prinde si POST-urile strica abonarea"
    assert "url.pathname.startsWith('/push/')" in sw


def test_sw_are_strategia_ceruta_si_plafon_pe_cache():
    sw = _sw()
    assert "staleWhileRevalidate" in sw
    assert "MAX_ARTICOLE" in sw, "fara plafon, cache-ul de articole creste pana la cota"


def test_sw_deschide_articolul_la_click_pe_alerta():
    sw = _sw()
    assert "notificationclick" in sw and "openWindow" in sw, (
        "o alerta care deschide prima pagina in loc de articol e zgomot, nu informatie")


# --- pagina de offline -----------------------------------------------------------

def test_pagina_de_offline_se_randeaza_fara_eroare():
    html = render._env().get_template("offline.html").render(**render._base_ctx("/offline/"))
    assert "Fără conexiune" in html
    assert 'content="noindex,follow"' in html, "pagina de offline nu are ce cauta in Google"


def test_pagina_de_offline_nu_intra_in_sitemap():
    assert "offline" not in render._SITEMAP_SECTIONS


def test_headersul_ruleaza_sw_ul_prin_revalidare(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    render._write_headers()
    continut = (tmp_path / "_headers").read_text(encoding="utf-8")
    assert "/sw.js" in continut and "must-revalidate" in continut, (
        "fara revalidare, un service worker reparat nu ajunge la vizitatori zile intregi")


# --- butonul de instalare --------------------------------------------------------

def _baza() -> str:
    return _citeste(os.path.join(TEMPLATES, "base.html"))


def test_butonul_de_instalare_nu_mai_e_in_nav():
    """Regresia măsurată: în `<nav>` apărea la `beforeinstallprompt` și împingea <main>."""
    nav = re.search(r"<nav class=\"nav\".*?</nav>", _baza(), re.S).group(0)
    assert "izz-install" not in nav


def test_butonul_de_instalare_e_in_afara_fluxului():
    baza = _baza()
    assert 'id="izz-install"' in baza
    assert 'id="izz-install-btn"' in baza
    assert 'id="izz-install-inchide"' in baza
    css = _citeste(os.path.join(STATIC, "styles.css"))
    bloc = re.search(r"\.izz-install \{(.*?)\}", css, re.S).group(1)
    assert "position: fixed" in bloc, "butonul trebuie sa ramana scos din flux (CLS)"
    assert ".izz-install[hidden] { display: none; }" in css, (
        "`display: flex` bate atributul `hidden`: butonul s-ar vedea la toata lumea")


def test_textele_sunt_in_romana():
    baza = _baza()
    for text in ("Instalează aplicația", "Alerte de ultimă oră", "Activează alertele",
                 "Dezactivează alertele", "o alertă pe zi"):
        assert text in baza, f"«{text}» lipseste din interfata"


def test_panoul_de_alerte_e_ultimul_din_footer():
    """Apare/dispare după suportul browserului; la coada documentului nu mișcă nimic."""
    footer = re.search(r"<footer class=\"site-footer\">(.*?)</footer>", _baza(), re.S).group(1)
    assert footer.rstrip().endswith("</div>")
    assert footer.index('id="izz-alerte"') > footer.index('id="izz-alerte"') - 1  # prezent
    assert footer.index('id="izz-alerte"') > footer.rindex("</nav>"), (
        "blocul de alerte trebuie sa fie DUPA nav-ul din footer, nu inaintea lui")


# --- scripturile -----------------------------------------------------------------

def test_scripturile_sunt_externe_si_versionate():
    baza = _baza()
    for nume in ("pwa.js", "push.js"):
        assert f'/static/{nume}?v={{{{ asset_ver[\'{nume}\'] }}}}' in baza, (
            f"{nume} nu e versionat: activele /static/ tin 30 de zile in cache (§16.2)")
    render._ASSET_VER = None
    ver = render._asset_ver()
    for nume in ("pwa.js", "push.js"):
        assert ver[nume] not in ("", "0"), f"{nume} lipseste din static/"


def test_pwa_js_nu_inregistreaza_pe_save_data():
    """Precache-ul articolelor e o optimizare; pe o conexiune economisită devine un cost."""
    js = _citeste(os.path.join(STATIC, "pwa.js"))
    assert "saveData" in js, "fara verificarea asta, descarcam articole contra vointei omului"
    assert "'/sw.js'" in js and "scope: '/'" in js


def test_push_js_nu_cere_permisiunea_fara_click():
    """Opt-in explicit: nicio cerere de permisiune care nu pornește dintr-un click."""
    js = _citeste(os.path.join(STATIC, "push.js"))
    assert js.count("requestPermission") == 1
    # Apelul e in interiorul functiei `activeaza`, legata de click, nu la init.
    assert "porneste.addEventListener('click', activeaza)" in js
    assert "userVisibleOnly: true" in js, (
        "fara el, unele browsere refuza abonarea cu totul")
