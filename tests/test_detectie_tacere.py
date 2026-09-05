"""Detectorul de tăcere: logica de verdict, izolată de rețea (gh e stub-uit)."""
from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location("detectie_tacere", ROOT / "tools" / "detectie_tacere.py")
dt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dt)


def test_varsta_ore_parseaza_iso_si_z():
    acum = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
    assert dt._varsta_ore("2026-09-05T10:00:00Z", acum) == 2.0
    assert dt._varsta_ore("2026-09-05T10:00:00+00:00", acum) == 2.0


def test_totul_viul_daca_toate_mecanismele_au_rulat_curand(monkeypatch):
    acum = datetime.now(timezone.utc)
    monkeypatch.setattr(dt, "ultimul_commit_continut", lambda acum, repo: 1.0)
    monkeypatch.setattr(dt, "ultima_rulare", lambda wf, acum, repo: 0.2)
    assert dt.constata("Ramanul/izz-ro", acum) == []


def test_continut_inghetat_este_constatare(monkeypatch):
    acum = datetime.now(timezone.utc)
    monkeypatch.setattr(dt, "ultimul_commit_continut", lambda acum, repo: 9.5)
    monkeypatch.setattr(dt, "ultima_rulare", lambda wf, acum, repo: 0.2)
    probleme = dt.constata("Ramanul/izz-ro", acum)
    assert len(probleme) == 1
    assert "înghețat" in probleme[0]


def test_workflow_niciodata_rulat_si_tacut_este_constatare(monkeypatch):
    acum = datetime.now(timezone.utc)
    monkeypatch.setattr(dt, "ultimul_commit_continut", lambda acum, repo: 1.0)
    def fals(wf, acum, repo):
        return None if wf == "smoke.yml" else 0.1
    monkeypatch.setattr(dt, "ultima_rulare", fals)
    probleme = dt.constata("Ramanul/izz-ro", acum)
    assert any("smoke.yml" in p and "nicio rulare" in p for p in probleme)
    assert len(probleme) == 1


def test_main_exit_2_cand_gh_esueaza(monkeypatch, capsys):
    monkeypatch.setattr(dt, "ultimul_commit_continut",
                        lambda acum, repo: (_ for _ in ()).throw(RuntimeError("gh lipsa")))
    cod = dt.main()
    assert cod == 2
    assert "NECLAR" in capsys.readouterr().out


def test_main_exit_1_si_scrie_alerta_la_tacere(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(dt, "ultimul_commit_continut", lambda acum, repo: 99.0)
    monkeypatch.setattr(dt, "ultima_rulare", lambda wf, acum, repo: 99.0)
    cod = dt.main()
    assert cod == 1
    alerta = (tmp_path / "alerta.md").read_text(encoding="utf-8")
    assert "înghețat" in alerta
