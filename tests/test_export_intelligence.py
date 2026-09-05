import json
from pathlib import Path

from tools.export_intelligence import export_json, flatten, load

ROOT = Path(__file__).resolve().parents[1]


def test_json_export_is_versioned_and_wrapped():
    data = load()
    exported = export_json(data, "market")
    assert exported["schema"] == "izz-intelligence-v1"
    assert exported["section"] == "market"
    assert "market" in exported["data"]
    assert "retrieved_at" in exported


def test_company_flatten_keeps_cui_and_change_fields():
    rows = flatten("companies", load()["companies"])
    assert rows
    assert {"cui", "name", "date", "type", "confidence"}.issubset(rows[0])


def test_dataset_file_is_parseable():
    with (ROOT / "static" / "inteligenta" / "data.json").open(encoding="utf-8") as handle:
        assert isinstance(json.load(handle), dict)
