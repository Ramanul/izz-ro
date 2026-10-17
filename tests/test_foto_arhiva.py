"""Fotografia de arhiva a omului din titlu (2026-10-17).

Ce pazesc testele:
  1. subiectul e omul numit PRIMUL in titlu, nu prima entitate care are o poza libera;
  2. cardul nu primeste chipul altcuiva cand subiectul are doar poza cu credit obligatoriu;
  3. pagina de articol nu mai deseneaza decorul generat; arata portretul de arhiva, etichetat,
     cu credit complet si linkul licentei (CC BY 4.0 par.3(a)(1)(C));
  4. allowlist-ul de licente din htmlart e acelasi cu cel din render.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import htmlart, render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ZEL = {"img": "portraits/zel.jpg", "name": "Volodymyr Zelensky", "credit_required": True}
LEPEN = {"img": "portraits/lepen.jpg", "name": "Marine Le Pen"}
ART = {"category": "extern", "source": "x", "url": "u",
       "title": "Volodimir Zelenski îi răspunde Marinei Le Pen privind ajutorul pentru Ucraina",
       "entities": ["Marine Le Pen", "Volodimir Zelenski"]}


def test_subiectul_e_cel_numit_primul_in_titlu_nu_primul_extras():
    """Entitatile vin in ordinea extragerii AI (Le Pen intai); subiectul gramatical e Zelenski."""
    toate = {"volodimir zelenski": ZEL, "marine le pen": LEPEN}
    key, rec = htmlart.subiect_titlu(ART, toate)
    assert key == "volodimir zelenski" and rec is ZEL


def test_NEGATIV_cardul_nu_primeste_chipul_altcuiva(monkeypatch):
    """Zelenski are doar poza cu credit; Le Pen are poza libera. Inainte, cardul purta chipul
    lui Le Pen pe stirea despre Zelenski. Acum ramane fara chip."""
    monkeypatch.setattr(htmlart, "_PORTRETE_LIBERE", {"marine le pen": LEPEN})
    monkeypatch.setattr(htmlart, "_PORTRETE_TOATE", {"volodimir zelenski": ZEL, "marine le pen": LEPEN})
    assert htmlart._portret_liber(ART) is None


def test_cardul_pastreaza_portretul_liber_al_subiectului(monkeypatch):
    lib = {"volodimir zelenski": {"img": "portraits/zel.jpg", "name": "Volodymyr Zelensky"}}
    monkeypatch.setattr(htmlart, "_PORTRETE_LIBERE", lib)
    monkeypatch.setattr(htmlart, "_PORTRETE_TOATE", {"volodimir zelenski": ZEL, "marine le pen": LEPEN})
    assert htmlart._portret_liber(ART) == lib["volodimir zelenski"]


def test_NEGATIV_omul_pomenit_doar_in_rezumat_nu_e_subiect():
    a = {**ART, "title": "Ucraina primește un nou pachet de ajutor", "teaser": "Zelenski a mulțumit."}
    assert htmlart.subiect_titlu(a, {"volodimir zelenski": ZEL}) is None


# --- pagina de articol ----------------------------------------------------------------

def _portraits(lic):
    return {"volodimir zelenski": {"name": "Volodymyr Zelensky", "img": "portraits/zel.jpg",
                                   "artist": "President.gov.ua", "license": lic,
                                   "page": "https://commons.wikimedia.org/wiki/File:Z.jpg"}}


def test_foto_arhiva_cu_credit_are_linkul_licentei(tmp_path, monkeypatch):
    media = tmp_path / "media" / "portraits"
    media.mkdir(parents=True)
    (media / "zel.jpg").write_bytes(b"\xff\xd8" + b"0" * 5000)
    monkeypatch.setattr(render, "MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path / "out"))
    ents = {"volodimir-zelenski": {}}
    ar = render._foto_arhiva(ART, _portraits("CC BY 4.0"), ents)
    assert ar and ar["key"] == "volodimir zelenski"
    assert ar["license_url"] == "https://creativecommons.org/licenses/by/4.0/"
    assert ar["slug"] == "volodimir-zelenski"
    assert (tmp_path / "out" / "portraits" / "zel.jpg").exists(), "fisierul n-a fost copiat"


def test_NEGATIV_licenta_necunoscuta_nu_produce_foto_de_arhiva(tmp_path, monkeypatch):
    media = tmp_path / "media" / "portraits"
    media.mkdir(parents=True)
    (media / "zel.jpg").write_bytes(b"\xff\xd8" + b"0" * 5000)
    monkeypatch.setattr(render, "MEDIA_DIR", str(tmp_path / "media"))
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path / "out"))
    for lic in ("Copyrighted", "", "CC BY-NC 4.0", "GFDL"):
        assert render._foto_arhiva(ART, _portraits(lic), {}) is None, lic


def test_pagina_de_articol_nu_mai_deseneaza_decorul_generat():
    with open(os.path.join(ROOT, "templates", "article.html"), encoding="utf-8") as fh:
        tpl = fh.read()
    assert "art--articol" not in tpl and "art(a" not in tpl
    assert "Foto de arhivă" in tpl and "arhiva.license_url" in tpl
    # „In imagini" poarta si el linkul licentei
    assert "p.license_url" in tpl


def test_clasele_fotografiei_de_arhiva_exista_in_css():
    with open(os.path.join(ROOT, "static", "styles.css"), encoding="utf-8") as fh:
        css = fh.read()
    for cls in (".arhiva-foto", ".arhiva-eticheta", ".arhiva-nume"):
        assert cls in css


# --- paritatea licentelor ----------------------------------------------------------------

def test_allowlist_de_licente_e_acelasi_in_htmlart_si_render():
    with open(os.path.join(ROOT, "data", "portraits.json"), encoding="utf-8") as fh:
        lic = {(v or {}).get("license") or "" for v in json.load(fh).values() if isinstance(v, dict)}
    lic |= {"CC BY 4.0", "CC BY-SA 3.0 ro", "CC BY-NC 4.0", "CC BY", "Copyrighted", ""}
    for x in lic:
        assert bool(htmlart._CREDIT_REQ_RE.match(x.strip())) == render._is_credit_required_license(x), x
