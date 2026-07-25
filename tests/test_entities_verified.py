"""Un ghid nu are voie sa spuna „Verificat" fara ca datele sa fi fost chiar verificate.

Context: trei ghiduri au stat publicate cu valori marcate „placeholder" intr-un comentariu
YAML — invizibil pentru parser — si cu eticheta „✅ Verificat" langa ele. Comentariul a
devenit campul `verificat`, iar testele de mai jos apara exact drumul pe care s-a scurs
minciuna: validarea, sablonul de ghid si indexul.
"""
import importlib
import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
build_entities = importlib.import_module("build_entities")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTITIES_DIR = os.path.join(ROOT, "data", "entities")


def _entitate_valida(**kw):
    ent = {
        "id": "test", "nume": "Test", "tip": "valoare_monetara",
        "categorie_ghid": "bani", "ultima_verificare": "2026-01-01", "verificat": True,
        "valoare_curenta": {"act_normativ": "HG 1/2026", "sursa_url": "https://x.ro/",
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


def test_fiecare_entitate_reala_declara_explicit_verificat():
    for fn in sorted(os.listdir(ENTITIES_DIR)):
        if not fn.endswith((".yaml", ".yml")):
            continue
        with open(os.path.join(ENTITIES_DIR, fn), encoding="utf-8") as fh:
            ent = yaml.safe_load(fh)
        assert isinstance(ent.get("verificat"), bool), f"{fn}: `verificat` lipseste sau nu e bool"


def test_ghidurile_neverificate_nu_afiseaza_eticheta_verificat():
    """Verificare pe HTML-ul chiar emis, nu pe sablon: eticheta si avertismentul se exclud."""
    ghiduri = os.path.join(ROOT, "output", "ghiduri")
    if not os.path.isdir(ghiduri):
        import pytest
        pytest.skip("site-ul nu e randat; ruleaza `python -m generator.main --render-only`")
    for fn in sorted(os.listdir(ENTITIES_DIR)):
        if not fn.endswith((".yaml", ".yml")):
            continue
        with open(os.path.join(ENTITIES_DIR, fn), encoding="utf-8") as fh:
            ent = yaml.safe_load(fh)
        pagina = os.path.join(ghiduri, ent["id"], "index.html")
        if not os.path.isfile(pagina):
            continue
        html = open(pagina, encoding="utf-8").read()
        if ent.get("verificat"):
            assert "Verificat:" in html, f"{ent['id']}: verificat, dar eticheta lipseste"
        else:
            assert "Verificat:" not in html, f"{ent['id']}: neverificat, dar scrie „Verificat\""
            assert "Valori neconfirmate" in html, f"{ent['id']}: lipseste avertismentul"
