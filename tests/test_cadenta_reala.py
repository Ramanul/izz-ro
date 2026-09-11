"""Garda uneltei de cadenta (`tools/cadenta_reala.py`).

Unealta exista fiindca o cifra de cadenta scrisa in contract s-a dovedit falsa cand a fost
masurata. Testele de aici apara exact acea lectie: baza de comparatie se CITESTE din workflow
(nu se da de mana, unde s-ar putea potrivi cu concluzia dorita), iar o forma de cron pe care
unealta n-o intelege trebuie sa esueze tare, nu sa ghiceasca un interval plauzibil.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools import cadenta_reala as cr  # noqa: E402

T0 = datetime(2026, 9, 5, 0, 0, tzinfo=timezone.utc)


def _runs(minute: list[int], cheie: str = "run_started_at") -> dict:
    return {"workflow_runs": [
        {cheie: (T0 + timedelta(minutes=m)).isoformat().replace("+00:00", "Z")}
        for m in minute
    ]}


def test_baza_de_comparatie_se_citeste_din_workflow():
    """Daca cronul din build.yml se schimba, unealta il urmeaza singura."""
    interval, prag = cr._citeste_workflow()
    assert interval > 0 and prag > 0
    text = open(cr.WORKFLOW, encoding="utf-8").read()
    assert f'PRAG_MIN: "{prag}"' in text


def test_cron_cu_forma_neacoperita_esueaza_in_loc_sa_ghiceasca(tmp_path):
    w = tmp_path / "build.yml"
    w.write_text('on:\n  schedule:\n    - cron: "13 3,9,15 * * *"\n', encoding="utf-8")
    with pytest.raises(SystemExit, match="nu e acoperita"):
        cr._citeste_workflow(str(w))


def test_cron_la_fiecare_n_ore_e_inteles(tmp_path):
    w = tmp_path / "build.yml"
    w.write_text('    - cron: "13 */3 * * *"\n    PRAG_MIN: "105"\n', encoding="utf-8")
    assert cr._citeste_workflow(str(w)) == (180, 105)


def test_cron_lipsa_sau_incomplet_esueaza(tmp_path):
    gol = tmp_path / "a.yml"
    gol.write_text("on:\n  push:\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="niciun `cron:`"):
        cr._citeste_workflow(str(gol))
    scurt = tmp_path / "b.yml"
    scurt.write_text('- cron: "13 * * *"\n', encoding="utf-8")
    with pytest.raises(SystemExit, match="4 campuri"):
        cr._citeste_workflow(str(scurt))


def test_program_perfect_orar_da_rata_de_o_suta_la_suta():
    porniri = cr._porniri(_runs([60 * i for i in range(25)]))
    st = cr.masoara(porniri, 60, 105)
    assert st["rata_declansare"] == 1.0
    assert st["gol_min"] == st["gol_median"] == st["gol_max"] == 60
    assert st["goluri_sub_prag"] == 24  # 60 < 105: acolo poarta CHIAR ar fi ce limiteaza


def test_golurile_sub_prag_se_numara_doar_cand_sunt_sub_prag():
    st = cr.masoara(cr._porniri(_runs([0, 100, 300, 420])), 60, 105)
    assert st["goluri_sub_prag"] == 1, "doar golul de 100 min e sub pragul de 105"


def test_rata_sub_unu_cand_planificatorul_sare_rulari():
    """Cazul masurat pe repo: rulari lipsa, nu rulari oprite de poarta."""
    st = cr.masoara(cr._porniri(_runs([0, 240, 480, 720])), 60, 105)
    assert st["rata_declansare"] == 0.25
    assert st["goluri_sub_prag"] == 0


def test_accepta_ambele_forme_de_intrare_si_cade_pe_created_at():
    a = cr._porniri(_runs([0, 60]))
    b = cr._porniri(_runs([0, 60])["workflow_runs"])
    c = cr._porniri(_runs([0, 60], cheie="created_at"))
    assert a == b == c


def test_o_singura_rulare_nu_produce_un_interval():
    with pytest.raises(SystemExit, match="cel putin doua"):
        cr.masoara(cr._porniri(_runs([0])), 60, 105)


def test_intrare_goala_spune_ce_lipseste():
    rez = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "cadenta_reala.py")],
        input="", capture_output=True, text=True, cwd=ROOT,
    )
    assert rez.returncode != 0
    assert "nicio intrare" in rez.stdout + rez.stderr


def test_cli_ruleaza_si_isi_declara_limitele(tmp_path):
    f = tmp_path / "runs.json"
    f.write_text(json.dumps(_runs([0, 240, 480])), encoding="utf-8")
    rez = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "cadenta_reala.py"), str(f)],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert rez.returncode == 0, rez.stdout + rez.stderr
    assert "rata de declansare" in rez.stdout
    assert "NU se poate citi de aici DE CE lipseste o rulare" in rez.stdout


def test_json_e_parsabil_pentru_alt_consumator(tmp_path):
    f = tmp_path / "runs.json"
    f.write_text(json.dumps(_runs([0, 240])), encoding="utf-8")
    rez = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "cadenta_reala.py"), str(f), "--json"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert json.loads(rez.stdout)["rulari"] == 2
