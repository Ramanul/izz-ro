"""Jurnalul de triage: o rulare = un rand; esec de scriere nu opreste pipeline-ul."""
from __future__ import annotations

import json

from generator import config, jurnal_triage


def test_o_rulare_un_rand_cu_motive(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", str(tmp_path))
    jurnal_triage.inregistreaza({"garda titular": 3, "titlu gol": 1},
                                {"https://exemplu.ro/a", "https://exemplu.ro/b"}, 7)
    linii = [json.loads(l) for l in (tmp_path / "data" / "triage_log.jsonl")
             .read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(linii) == 1
    rand = linii[0]
    assert rand["ingestie"] == {"garda titular": 3, "titlu gol": 1}
    assert rand["fara_substanta"] == 2
    assert rand["expirate"] == 7
    assert "cand" in rand


def test_exemplele_sunt_limitate_si_sortate(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", str(tmp_path))
    multe = {f"https://exemplu.ro/{i}" for i in range(25)}
    jurnal_triage.inregistreaza({}, multe, 0)
    rand = json.loads((tmp_path / "data" / "triage_log.jsonl").read_text(encoding="utf-8"))
    assert len(rand["fara_substanta_exemple"]) == 10
    assert rand["fara_substanta_exemple"] == sorted(multe)[:10]


def test_esec_de_scriere_nu_arunca_exceptie(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ROOT", str(tmp_path))
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "triage_log.jsonl").mkdir()  # cale = director => OSError la scriere
    jurnal_triage.inregistreaza({"x": 1}, set(), 0)  # nu trebuie sa arunce
