import json
from pathlib import Path

from generator.intelligence import get_company_monitor, match_leads, suggest_actions, validate_dataset

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "static" / "inteligenta" / "data.json"


def load_data() -> dict:
    with DATA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_dataset_contract_has_no_errors():
    assert validate_dataset(load_data()) == []


def test_lead_matching_is_explainable_and_sorted():
    matches = match_leads(load_data()["providers"], need="acoperiș", city="Timișoara", budget="high")
    assert 1 <= len(matches) <= 3
    assert matches[0].provider["name"] == "Acoperiș Timiș"
    assert matches[0].score == 100
    assert "categorie" in matches[0].reasons
    assert "localitate" in matches[0].reasons
    assert "buget" in matches[0].reasons
    assert all(matches[i].score >= matches[i + 1].score for i in range(len(matches) - 1))


def test_company_monitor_normalizes_cui_and_orders_changes():
    company = get_company_monitor(load_data()["companies"], " ro 12345678 ")
    assert company is not None
    assert company["changes"][0]["date"] >= company["changes"][-1]["date"]


def test_actions_cover_core_intent_classes():
    assert "Calculează impactul pentru profilul tău" in suggest_actions("Se schimbă salariul minim")
    assert "Verifică textul oficial și termenul de aplicare" in suggest_actions("Guvernul emite o ordonanță")
    assert "Caută oportunități și contracte similare" in suggest_actions("Apare o licitație nouă")
    assert "Compară ofertele și costul total" in suggest_actions("Se schimbă prețul la energie")
    assert suggest_actions("ceva neutru") == ["Salvează subiectul și activează o alertă de schimbare"]
