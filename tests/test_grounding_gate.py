from __future__ import annotations

import json

from tools.grounding_gate import main


def _write(path, rows):
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_grounding_gate_passes_clean_report(tmp_path, monkeypatch):
    report = tmp_path / "grounding.jsonl"
    _write(report, [{"id": "1", "model": "B", "blocking_issues": [], "advisory_issues": []}])
    monkeypatch.setenv("IZZ_RAPORT_COPIERE_GATE", str(report))
    assert main() == 0


def test_grounding_gate_blocks_quote_and_foreign_number(tmp_path, monkeypatch):
    report = tmp_path / "grounding.jsonl"
    _write(report, [{
        "id": "https://example.test/a",
        "model": "B",
        "blocking_issues": [
            {"cod": "citat_inventat", "detaliu": "citat"},
            {"cod": "cifra_straina", "detaliu": "9876"},
        ],
        "advisory_issues": [],
    }])
    monkeypatch.setenv("IZZ_RAPORT_COPIERE_GATE", str(report))
    assert main() == 1


def test_grounding_gate_does_not_block_advisory_reserve(tmp_path, monkeypatch):
    report = tmp_path / "grounding.jsonl"
    _write(report, [{
        "id": "2",
        "model": "C",
        "blocking_issues": [],
        "advisory_issues": [{"cod": "rezerva_pierduta", "detaliu": ""}],
    }])
    monkeypatch.setenv("IZZ_RAPORT_COPIERE_GATE", str(report))
    assert main() == 0
