"""Regresii pentru prima felie România Utilă.

Testăm contractul de date și legăturile publice, nu rendererul în oglindă: valorile rămân în
`data/entities/*.yaml`, iar paginile sunt generate din acea sursă unică.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ENTITIES = ROOT / "data" / "entities"


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _load(name: str) -> dict:
    with (ENTITIES / name).open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_landing_romania_utila_exista_si_leaga_felia_1():
    text = _read("content/pages/romania-utila.md")
    for needle in (
        "# România Utilă",
        "/ghiduri/salariul-minim/",
        "/ghiduri/alocatia-copii/",
        "/ghiduri/calendar-anaf/",
        "/instrumente/calculator-salariu/",
    ):
        assert needle in text


def test_calendarul_anaf_are_sursa_oficiala_si_termenul_curent():
    text = _read("data/entities/calendar-anaf.yaml")
    assert "id: calendar-anaf" in text
    assert "static.anaf.ro" in text
    assert "2026-09-25" in text
    assert "verificat: true" in text


def test_alocatia_are_valori_confirmate():
    text = _read("data/entities/alocatia-copii.yaml")
    assert "brut: 292" in text
    assert "valoare_secundara: 719" in text
    assert "verificat: true" in text
    assert "ultima_verificare: \"2026-09-04\"" in text
    assert "Valori NEVERIFICATE" not in text


def test_salariul_minim_este_actualizat():
    """Cele trei asertiuni pe care AMBELE versiuni ale acestui PR le sustineau.

    Versiunea originala mai cerea si `200 lei/lună` + `OUG 89/2025` — facilitatea din a doua
    jumatate a lui 2026. Continutul acela NU a fost integrat la rezolvarea conflictului cu
    #266: descria o facilitate reala invocand un act normativ, dar fara URL catre act, iar
    portalul legislativ nu e accesibil din mediul de rezolvare (`legislatie.just.ro` ->
    conexiune esuata, masurat 2026-09-05). Regula proprietarului e ca temeiul e ACTUL, nu
    proza care il invoca. Asertiunile au plecat odata cu continutul pe care il pazeau, nu ca
    sa treaca suita. Repunerea lor merge impreuna cu continutul, cand actul e verificat.
    """
    text = _read("data/entities/salariul-minim.yaml")
    assert "brut: 4325" in text
    assert "in_vigoare_de: \"2026-07-01\"" in text
    assert "ultima_verificare: \"2026-09-04\"" in text


def test_fiecare_treapta_din_istoric_isi_numeste_actul_normativ():
    """Structura istoricului, nu datele disputate — vezi `IZZ-0312`.

    Versiunea originala afirma ca 3.700 lei se aplica din 2024-07-01 prin HG 598/2024 si ca
    varianta cu 2025-01-01 e GRESITA. Datele de pe main spun 2025-01-01 prin HG 1493/2024.
    Una din ele e falsa, si nu se poate decide fara actul normativ, care nu e accesibil din
    mediul de rezolvare. A pastra oricare dintre asertiuni ar fi insemnat sa declar castigator
    fara dovada, pe o cifra financiara publicata. Ce se poate paza fara sa arbitrez: fiecare
    treapta isi numeste actul si data — deci o treapta adaugata fara temei pica in continuare.
    """
    istoric = _load("salariul-minim.yaml")["istoric"]
    assert istoric, "istoricul salariului minim e gol"
    for treapta in istoric:
        assert isinstance(treapta.get("brut"), int), treapta
        assert treapta.get("in_vigoare_de"), treapta
        assert treapta.get("act_normativ"), treapta


def test_aliasurile_romania_utila_sunt_301_si_tinta_exista():
    text = _read("data/redirects_migrare.tsv")
    expected = {
        "/romania-utila/salariul-minim/\t/ghiduri/salariul-minim/",
        "/romania-utila/alocatii/\t/ghiduri/alocatia-copii/",
        "/romania-utila/calendar-anaf/\t/ghiduri/calendar-anaf/",
    }
    rows = {line for line in text.splitlines() if line.startswith("/romania-utila/")}
    assert rows == expected


# --- aduse din versiunea de pe main (#266): verifica pe obiectul YAML, nu pe text ---

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
