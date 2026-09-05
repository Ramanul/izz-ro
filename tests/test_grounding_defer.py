"""Defer pentru incalcari deterministe de grounding (PLAN UNIFICAT #1: blocare/defer).

Itemele incalcatoare nu se publica in rularea curenta si nu blocheaza release-ul:
ies din starea salvata (revin ca noi la urmatoarea rulare) si din dovada gate.
"""
from __future__ import annotations

import json

from generator import raport_copiere


def _scrie(cale, randuri):
    cale.write_text(
        "".join(json.dumps(r) + "\n" for r in randuri),
        encoding="utf-8",
    )


def test_url_uri_blocate_citeste_din_raport(tmp_path):
    cale = tmp_path / "gate.jsonl"
    _scrie(cale, [
        {"id": "https://exemplu.test/a", "blocking_issues": [{"cod": "titlu_copiat"}]},
        {"id": "https://exemplu.test/b", "blocking_issues": []},
    ])
    assert raport_copiere.url_uri_blocate(str(cale)) == {"https://exemplu.test/a"}


def test_pastreaza_doar_curate_scoate_blocantele(tmp_path):
    cale = tmp_path / "gate.jsonl"
    _scrie(cale, [
        {"id": "https://exemplu.test/a", "blocking_issues": [{"cod": "text_copiat"}]},
        {"id": "https://exemplu.test/b", "blocking_issues": []},
    ])
    scoase = raport_copiere.pastreaza_doar_curate(str(cale))
    assert scoase == 1
    randuri = [json.loads(l) for l in cale.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert [r["id"] for r in randuri] == ["https://exemplu.test/b"]


def test_rand_malformat_nu_rescrie_dovada(tmp_path):
    cale = tmp_path / "gate.jsonl"
    _scrie(cale, [{"id": "https://exemplu.test/a", "blocking_issues": []}])
    cale.write_text(cale.read_text(encoding="utf-8") + "nu-e-json\n", encoding="utf-8")
    assert raport_copiere.pastreaza_doar_curate(str(cale)) == 0
    assert "nu-e-json" in cale.read_text(encoding="utf-8")


def test_fisier_lipsa_inseamna_nimic_blocat(tmp_path):
    assert raport_copiere.url_uri_blocate(str(tmp_path / "lipsa.jsonl")) == set()
    assert raport_copiere.pastreaza_doar_curate(str(tmp_path / "lipsa.jsonl")) == 0
