"""Poarta de accesibilitate statica (`tools/a11y_static.py`) trebuie sa POATA pica.

Rulat pe `output/` real, unealta raporteaza 0 incalcari tari — exact rezultatul pe care l-ar
da si un checker stricat (sau unul care nu mai gaseste inputurile). De aceea testele de aici
sunt de MUTATIE: fiecare construieste o pagina valida si strica un singur lucru, apoi cere
ca unealta sa-l prinda. In plus, doua cazuri care NU trebuie semnalate (eticheta implicita
prin `<label>` infasurator, `alt=""` la imaginea decorativa) — altfel poarta ar da alarme
false si ar fi dezactivata la prima rulare.

Ruleaza pe HTML-ul din fixture-ul de randare, deci nu are nevoie de browser (vezi
specs/masuratori-frontend.md, „ce nu am putut masura").
"""
import importlib
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
a11y = importlib.import_module("tools.a11y_static")

CURAT = """<!DOCTYPE html><html lang="ro"><head><title>t</title></head><body>
<a class="skip" href="#main">Sari la conținut</a>
<nav aria-label="Principal"><a href="/despre/">Despre</a></nav>
<main id="main">
  <h1>Titlu</h1>
  <h2>Subtitlu</h2>
  <p>Text.</p>
  <img src="/x.png" alt="" width="960" height="504">
  <form><label>Caută <input type="search" placeholder="…"></label>
        <label for="q2">Al doilea</label><input id="q2" type="text"></form>
  <a href="/articol/">Citește</a>
  <a href="/poza/" aria-hidden="true" tabindex="-1"><img src="/y.png" alt="" width="1" height="1"></a>
  <button type="button">Trimite</button>
  <a href="https://exemplu.ro" target="_blank" rel="noopener noreferrer">Sursă</a>
  <div id="unic"></div>
</main></body></html>"""


def _verifica(html, tmp_path):
    cale = tmp_path / "index.html"
    cale.write_text(html, encoding="utf-8")
    return a11y.verifica(str(cale))


def test_pagina_curata_trece(tmp_path):
    r = _verifica(CURAT, tmp_path)
    assert r["tari"] == [], r["tari"]
    assert r["slabe"] == [], r["slabe"]


@pytest.mark.parametrize("defect,asteptat", [
    ('<img src="/z.png" width="1" height="1">', "img fara alt"),
    ('<input type="text">', "input fara eticheta"),
    ('<a href="/gol/"></a>', "linkuri fara nume accesibil"),
    ('<button type="button"></button>', "butoane fara nume"),
    ('<div tabindex="2">x</div>', "tabindex pozitiv"),
])
def test_defectele_sunt_prinse(tmp_path, defect, asteptat):
    html = CURAT.replace("</main>", defect + "</main>")
    r = _verifica(html, tmp_path)
    assert any(asteptat in t for t in r["tari"]), r["tari"]


def test_doua_h1_si_lang_gresit(tmp_path):
    html = CURAT.replace('<h2>Subtitlu</h2>', '<h2>Subtitlu</h2><h1>Al doilea</h1>')
    r = _verifica(html, tmp_path)
    assert any("2 titluri h1" in t for t in r["tari"]), r["tari"]

    html = CURAT.replace('lang="ro"', 'lang="en"')
    r = _verifica(html, tmp_path)
    assert any("lang='en'" in t for t in r["tari"]), r["tari"]


def test_id_duplicat(tmp_path):
    html = CURAT.replace("</main>", '<div id="unic"></div></main>')
    r = _verifica(html, tmp_path)
    assert any("id-uri duplicate" in t for t in r["tari"]), r["tari"]


def test_eticheta_implicita_nu_e_semnalata(tmp_path):
    """`<label>Caută <input></label>` da nume accesibil prin infasurare — fara asta,
    harta (care foloseste exact tiparul) ar aparea cu 44 de incalcari false."""
    html = CURAT.replace('<label for="q2">Al doilea</label><input id="q2" type="text">', "")
    r = _verifica(html, tmp_path)
    assert r["tari"] == [], r["tari"]


# Poarta pe build-ul REAL nu se ruleaza aici: `output/` e un efect secundar al altor teste
# (fiecare randare de fixture il rescrie), deci un test care il citeste depinde de ordinea
# aleatoare a `pytest-randomly` si pica pe CI exact cand o alta randare a lasat un output
# partial. Poarta sta in jobul `html-gate` din `.github/workflows/tests.yml`, imediat dupa
# `--render-only`, adica pe un output construit intentionat — si local, ca unealta:
#   python tools/a11y_static.py
