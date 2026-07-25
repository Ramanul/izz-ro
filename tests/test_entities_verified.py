"""Un ghid nu are voie sa spuna „Verificat" fara ca datele sa fi fost chiar verificate.

Context: trei ghiduri au stat publicate cu valori marcate „placeholder" intr-un comentariu
YAML — invizibil pentru parser — si cu eticheta „✅ Verificat" langa ele. Comentariul a
devenit campul `verificat`, iar testele de mai jos apara exact drumul pe care s-a scurs
minciuna: validarea, sablonul de ghid si indexul.
"""
import importlib
import os
import subprocess
import sys

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
build_entities = importlib.import_module("build_entities")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTITIES_DIR = os.path.join(ROOT, "data", "entities")


def _entitate_valida(**kw):
    ent = {
        "id": "test", "nume": "Test", "tip": "valoare_monetara",
        "categorie_ghid": "bani", "ultima_verificare": "2026-01-01", "verificat": True,
        "valoare_curenta": {"act_normativ": "HG 1/2026",
                            "sursa_url": "https://x.ro/monitor/hg-1-2026",
                            "in_vigoare_de": "2026-01-01"},
    }
    ent.update(kw)
    return ent


def test_entitate_completa_trece():
    assert build_entities.validate(_entitate_valida()) == []


def test_lipsa_campului_verificat_blocheaza_buildul():
    """Absenta nu poate insemna „verificat" — asta a tinut trei ghiduri publicate gresit."""
    ent = _entitate_valida()
    del ent["verificat"]
    erori = build_entities.validate(ent)
    assert any("verificat" in e for e in erori), erori


def test_verificat_false_e_valid_nu_eroare():
    """A recunoaste ca datele nu-s verificate e o stare legitima, nu un build stricat."""
    assert build_entities.validate(_entitate_valida(verificat=False)) == []


def test_verificat_trebuie_sa_fie_bool_nu_sir():
    """'da', 'nu', 'false' sunt toate adevarate in Python — un sir ar publica date neverificate."""
    for valoare in ("da", "nu", "false", 1):
        erori = build_entities.validate(_entitate_valida(verificat=valoare))
        assert any("verificat" in e for e in erori), f"{valoare!r} a trecut ca bool"


def test_verificat_true_cere_link_catre_pagina_exacta_nu_homepage():
    """Un link catre mmuncii.ro nu duce cititorul la cifra. Regula se aplica doar celor
    care DECLARA verificarea — cine isi recunoaste starea de neverificat nu e blocat."""
    homepage = _entitate_valida(verificat=True)
    homepage["valoare_curenta"]["sursa_url"] = "https://mmuncii.ro/"
    assert any("pagina exacta" in e for e in build_entities.validate(homepage))

    exact = _entitate_valida(verificat=True)
    exact["valoare_curenta"]["sursa_url"] = "https://mmuncii.ro/j33/images/hg-1506-2025.pdf"
    assert build_entities.validate(exact) == []

    # neverificat + homepage: acceptat, fiindca pagina spune deja ca datele nu-s confirmate
    neverificat = _entitate_valida(verificat=False)
    neverificat["valoare_curenta"]["sursa_url"] = "https://mmuncii.ro/"
    assert build_entities.validate(neverificat) == []


def test_fiecare_entitate_reala_declara_explicit_verificat():
    for fn in sorted(os.listdir(ENTITIES_DIR)):
        if not fn.endswith((".yaml", ".yml")):
            continue
        with open(os.path.join(ENTITIES_DIR, fn), encoding="utf-8") as fh:
            ent = yaml.safe_load(fh)
        assert isinstance(ent.get("verificat"), bool), f"{fn}: `verificat` lipseste sau nu e bool"


def _entitati():
    for fn in sorted(os.listdir(ENTITIES_DIR)):
        if fn.endswith((".yaml", ".yml")):
            with open(os.path.join(ENTITIES_DIR, fn), encoding="utf-8") as fh:
                yield yaml.safe_load(fh)


@pytest.fixture(scope="module")
def site_randat():
    """Randeaza site-ul daca lipseste, ca testul sa nu se poata ocoli sarind peste el:
    un test care se auto-dezactiveaza cand nu gaseste output/ lasa suita verde exact
    in cazul in care regresia ar fi trecut nedetectata."""
    ghiduri = os.path.join(ROOT, "output", "ghiduri")
    if not os.path.isdir(ghiduri):
        r = subprocess.run([sys.executable, "-m", "generator.main", "--render-only"],
                           cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, f"randarea a esuat:\n{r.stdout}\n{r.stderr}"
    assert os.path.isdir(ghiduri), "output/ghiduri lipseste si dupa randare"
    return ghiduri


def test_eticheta_si_avertismentul_se_exclud_pe_fiecare_ghid(site_randat):
    """Pe HTML-ul chiar emis, nu pe sablon. Cele doua stari nu pot coexista."""
    for ent in _entitati():
        pagina = os.path.join(site_randat, ent["id"], "index.html")
        assert os.path.isfile(pagina), f"{ent['id']}: pagina randata lipseste"
        html = open(pagina, encoding="utf-8").read()
        if ent.get("verificat"):
            assert "Verificat:" in html, f"{ent['id']}: verificat, dar eticheta lipseste"
            assert "Valori neconfirmate" not in html, f"{ent['id']}: verificat, dar are avertisment"
        else:
            assert "Verificat:" not in html, f"{ent['id']}: neverificat, dar scrie „Verificat\""
            assert "Valori neconfirmate" in html, f"{ent['id']}: lipseste avertismentul"


def test_indexul_numara_ghidurile_neconfirmate_si_nu_promite_verificat(site_randat):
    """Indexul isi ajusteaza promisiunea; altfel titlul contrazice cardurile de sub el."""
    html = open(os.path.join(site_randat, "index.html"), encoding="utf-8").read()
    total = sum(1 for _ in _entitati())
    neconfirmate = sum(1 for e in _entitati() if not e.get("verificat"))
    if neconfirmate:
        assert f"{neconfirmate} din {total}" in html, "numarul de ghiduri neconfirmate lipseste"
        assert "actualizate și verificate" not in html, "promite „verificate\" desi nu sunt"
        assert html.count("Neconfirmat") >= neconfirmate, "cardurile nu arata starea"
    else:
        assert "actualizate și verificate" in html
