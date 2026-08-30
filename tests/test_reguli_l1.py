"""Garzile stratului L1 — hook-ul care livreaza regulile conditionate.

Aceleasi doua reguli de casa ca la `test_reguli.py`: functiile se testeaza pure, si
FIECARE garda are testul ei negativ. O garda care nu poate esua nu e o garda.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "reguli_l1.py"

_spec = importlib.util.spec_from_file_location("reguli_l1", HOOK)
l1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(l1)


# --- ce a atins unealta -------------------------------------------------------------

@pytest.mark.parametrize("intrare,asteptat", [
    ({"file_path": "templates/_card.html"}, "templates/_card.html"),
    ({"notebook_path": "x.ipynb"}, "x.ipynb"),
    ({"command": "sed -n 1,5p static/styles.css"}, "sed -n 1,5p static/styles.css"),
    ({"file_path": r"C:\p\templates\a.html"}, "C:/p/templates/a.html"),
])
def test_tinta_extrage_ce_trebuie(intrare, asteptat):
    assert l1.tinta({"tool_input": intrare}) == asteptat


@pytest.mark.parametrize("payload", [{}, {"tool_input": None}, {"tool_input": {}},
                                     {"tool_input": {"file_path": 7}}])
def test_tinta_nu_crapa_pe_intrare_ciudata(payload):
    """Un hook care arunca pe un payload neasteptat rupe sesiunea. Nu are voie."""
    assert l1.tinta(payload) == ""


# --- ce reguli se aprind ------------------------------------------------------------

@pytest.mark.parametrize("cale", [
    "templates/base.html",
    "static/styles.css",
    "generator/render.py",
    "/home/user/izz-ro/templates/index.html",
])
def test_caile_de_frontend_aprind_regula(cale):
    assert l1.reguli_aprinse(cale) == ["13-frontend"]


@pytest.mark.parametrize("cale", [
    "generator/fetch.py", "specs/STATE.md", "static/logo.svg", "tests/test_state.py", "",
])
def test_garda_nu_se_aprinde_pe_ce_nu_o_priveste(cale):
    """Testul negativ: daca s-ar aprinde la orice, ar fi doar zgomot cu pasi in plus."""
    assert l1.reguli_aprinse(cale) == []


def test_supra_declansarea_pe_bash_e_ASUMATA_nu_accidentala():
    """Decizie proprietar 2026-08-29: `ls templates/` aprinde §13, desi e doar o citire.

    Testul exista ca sa fie CONSTIENTA: daca cineva ingusteaza filtrul, pica aici si
    citeste motivul, in loc sa creada ca repara un bug.
    """
    assert l1.reguli_aprinse("ls templates/") == ["13-frontend"]


def test_fiecare_regula_din_catalog_are_fisier():
    for rid, (fisier, cai) in l1.CATALOG.items():
        assert (ROOT / ".claude" / "reguli" / fisier).is_file(), f"{rid}: lipseste {fisier}"
        assert cai, f"{rid}: fara cai declansatoare nu s-ar aprinde niciodata"


# --- livrarea o singura data pe sesiune ---------------------------------------------

def test_regula_se_livreaza_o_singura_data_pe_sesiune(tmp_path, monkeypatch):
    monkeypatch.setattr(l1.tempfile, "gettempdir", lambda: str(tmp_path))
    assert l1.deja_livrata("sesiunea-A", "13-frontend") is False
    assert l1.deja_livrata("sesiunea-A", "13-frontend") is True


def test_sesiuni_diferite_primesc_fiecare_regula(tmp_path, monkeypatch):
    monkeypatch.setattr(l1.tempfile, "gettempdir", lambda: str(tmp_path))
    assert l1.deja_livrata("sesiunea-A", "13-frontend") is False
    assert l1.deja_livrata("sesiunea-B", "13-frontend") is False


def test_marcajul_nu_lasa_id_ul_de_sesiune_sa_scrie_unde_vrea(tmp_path, monkeypatch):
    """`session_id` vine din afara: o cale relativa in el nu are voie sa scape din temp."""
    monkeypatch.setattr(l1.tempfile, "gettempdir", lambda: str(tmp_path))
    m = l1._marcaj("../../etc/pwned", "13-frontend")
    assert tmp_path in m.parents


# --- hook-ul intreg, rulat ca proces -------------------------------------------------

def _ruleaza(payload: dict, temp: Path) -> str:
    """`temp` izoleaza marcajele de dedupe: altfel a doua rulare a suitei tace, corect
    dar inutil, si testul ar parea rupt cand de fapt hook-ul si-a facut treaba."""
    mediu = {**os.environ, "TMPDIR": str(temp), "TEMP": str(temp), "TMP": str(temp)}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True, check=True,
                          cwd=ROOT, env=mediu).stdout


def test_hook_ul_livreaza_regula_pe_o_cale_de_frontend(tmp_path):
    out = _ruleaza({"session_id": "test-livrare", "tool_name": "Edit",
                    "tool_input": {"file_path": "templates/_card.html"}}, tmp_path)
    date = json.loads(out)
    ctx = date["hookSpecificOutput"]["additionalContext"]
    assert date["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "audit.sh" in ctx and "pa11y" in ctx


def test_hook_ul_tace_pe_o_cale_care_nu_il_priveste(tmp_path):
    assert _ruleaza({"session_id": "test-tacere", "tool_name": "Edit",
                     "tool_input": {"file_path": "generator/fetch.py"}}, tmp_path) == ""


def test_hook_ul_nu_repeta_regula_in_aceeasi_sesiune(tmp_path):
    """A doua atingere a aceluiasi fisier nu mai plateste 1,4 KB de context."""
    p = {"session_id": "test-repet", "tool_name": "Edit",
         "tool_input": {"file_path": "templates/_card.html"}}
    assert _ruleaza(p, tmp_path) != ""
    assert _ruleaza(p, tmp_path) == ""


def test_hook_ul_nu_crapa_pe_intrare_stricata():
    """Ultima plasa: orice ar primi, iese 0 si nu scrie nimic."""
    p = subprocess.run([sys.executable, str(HOOK)], input="{ nu e json",
                       capture_output=True, text=True, cwd=ROOT)
    assert p.returncode == 0 and p.stdout == ""


# --- cablajul: hook-ul chiar e inregistrat -------------------------------------------

def test_hookul_e_inregistrat_in_settings_comis():
    """Un hook scris dar neinregistrat nu exista. `settings.local.json` e gitignored,
    deci inregistrarea trebuie sa fie in `settings.json`, care se comite."""
    cfg = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    comenzi = [h.get("command", "")
               for grup in cfg.get("hooks", {}).get("PostToolUse", [])
               for h in grup.get("hooks", [])]
    assert any("reguli-l1.sh" in c for c in comenzi), "PostToolUse nu cheama reguli-l1.sh"
