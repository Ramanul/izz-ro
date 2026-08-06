"""Teste pentru poarta de falsificabilitate din tools/pr_review_gemini.py.

Ce apara: recenzorul publica DOAR constatari pe care proprietarul le poate verifica singur
(fisier atins de PR + linie + reproducere). Fara poarta, un al doilea recenzor AI adauga
zgomot nearbitrabil, nu verificare -- vezi LECTII.md.
"""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "pr_review_gemini", Path(__file__).resolve().parents[1] / "tools" / "pr_review_gemini.py")
prg = importlib.util.module_from_spec(_spec)
sys.modules["pr_review_gemini"] = prg
_spec.loader.exec_module(prg)

ATINSE = {"generator/main.py", "generator/cluster.py"}


def _ok(**kw):
    baza = {"file": "generator/main.py", "line": 42, "severity": "error",
            "claim": "sortarea inverseaza ordinea", "repro": "doua iteme cu published egal -> ordine instabila"}
    baza.update(kw)
    return baza


def test_constatare_completa_trece():
    pastrate, aruncate = prg.filtreaza([_ok()], ATINSE)
    assert len(pastrate) == 1 and not aruncate


def test_fara_linie_e_aruncata():
    pastrate, aruncate = prg.filtreaza([_ok(line=None)], ATINSE)
    assert not pastrate and aruncate[0][1] == "fara fisier:linie"


def test_linie_ca_text_e_aruncata():
    """Modelul returneaza uneori "42" in loc de 42; un string nu e o ancora verificabila."""
    pastrate, aruncate = prg.filtreaza([_ok(line="42")], ATINSE)
    assert not pastrate and aruncate[0][1] == "fara fisier:linie"


def test_bool_nu_trece_ca_linie():
    """`isinstance(True, int)` e adevarat in Python -- capcana care ar lasa sa treaca `line: true`."""
    pastrate, aruncate = prg.filtreaza([_ok(line=True)], ATINSE)
    assert not pastrate and aruncate[0][1] == "fara fisier:linie"


def test_fisier_neatins_de_pr_e_aruncat():
    """Constatarea despre cod pe care PR-ul nici nu-l atinge: nearbitrabila in contextul PR-ului."""
    pastrate, aruncate = prg.filtreaza([_ok(file="generator/render.py")], ATINSE)
    assert not pastrate and "neatins" in aruncate[0][1]


def test_fara_reproducere_e_aruncata():
    pastrate, aruncate = prg.filtreaza([_ok(repro="   ")], ATINSE)
    assert not pastrate and aruncate[0][1] == "fara reproducere"


def test_element_care_nu_e_obiect_nu_arunca_exceptie():
    pastrate, aruncate = prg.filtreaza(["doar un sir", 7, None], ATINSE)
    assert not pastrate and len(aruncate) == 3


def test_amestec_pastreaza_doar_valabilele():
    findings = [_ok(), _ok(line=None), _ok(file="alt/fisier.py"), _ok(repro="")]
    pastrate, aruncate = prg.filtreaza(findings, ATINSE)
    assert len(pastrate) == 1 and len(aruncate) == 3


def test_obiect_invelit_in_lista():
    """Gemini 3.x returneaza uneori obiectul intr-o lista (IZZ-0076). Fara asta, `.get` crapa."""
    assert prg._obiect('[{"findings": []}]') == {"findings": []}


def test_obiect_direct():
    assert prg._obiect('{"findings": [{"file": "a.py"}]}')["findings"][0]["file"] == "a.py"


def test_json_invalid_da_dict_gol():
    assert prg._obiect("nu e json") == {}


def test_lista_fara_dict_da_dict_gol():
    assert prg._obiect('[1, 2, "trei"]') == {}
