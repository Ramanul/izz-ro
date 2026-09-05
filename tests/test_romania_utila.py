"""Regresii pentru prima felie România Utilă: datele volatile trebuie să fie trasabile și curente."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ENTITIES = ROOT / "data" / "entities"


def _load(name: str) -> dict:
    with (ENTITIES / name).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_salarii_si_alocatii_sunt_verificate_pentru_2026():
    salariu = _load("salariul-minim.yaml")
    alocatie = _load("alocatia-copii.yaml")

    assert salariu["verificat"] is True
    assert salariu["valoare_curenta"]["brut"] == 4325
    assert salariu["valoare_curenta"]["in_vigoare_de"] == "2026-07-01"
    assert alocatie["verificat"] is True
    assert alocatie["valoare_curenta"]["brut"] == 292
    assert alocatie["valoare_curenta"]["valoare_secundara"] == 719


def test_calendarul_anaf_are_termenele_curente_si_sursa_oficiala():
    ent = _load("calendar-anaf.yaml")
    assert ent["id"] == "calendar-anaf"
    assert ent["verificat"] is True
    assert ent["ultima_verificare"] == "2026-09-04"
    assert ent["termene"]
    assert {x["data"] for x in ent["termene"]} >= {"2026-09-25", "2026-09-30"}
    assert "anaf.ro" in ent["valoare_curenta"]["sursa_url"]
