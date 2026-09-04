import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "static" / "inteligenta" / "data.json"


def load_data() -> dict:
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_strategy_dataset_is_valid_json_and_has_core_sections():
    data = load_data()
    assert set(("catalog", "providers", "companies", "market", "commerce", "events")).issubset(data)
    assert isinstance(data["catalog"], list)
    assert len(data["catalog"]) >= 37


def test_strategy_catalog_has_unique_product_names():
    names = [item["name"] for item in load_data()["catalog"]]
    assert len(names) == len(set(names))
    assert all(name.strip() for name in names)


def test_lead_provider_records_have_matching_fields():
    for provider in load_data()["providers"]:
        assert provider["name"]
        assert provider["city"]
        assert provider["categories"]
        assert provider["budgets"]
        assert provider["contact"]


def test_business_records_have_confidence_and_dates():
    for company in load_data()["companies"].values():
        assert company["name"]
        for change in company["changes"]:
            assert 0 <= int(change["confidence"]) <= 100
            assert change["date"]
            assert change["type"]
            assert change["text"]
