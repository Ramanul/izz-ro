"""Regresii pentru felia curentă România Utilă.

Testăm contractul de date și legăturile publice, nu rendererul în oglindă: valorile rămân în
`data/entities/*.yaml`, iar paginile sunt generate din acea sursă unică.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


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


def test_salariul_minim_este_actualizat_si_documenteaza_facilitatea_200():
    text = _read("data/entities/salariul-minim.yaml")
    assert "brut: 4325" in text
    assert "in_vigoare_de: \"2026-07-01\"" in text
    assert "ultima_verificare: \"2026-09-04\"" in text
    assert "200 lei/lună" in text
    assert "OUG 89/2025" in text


def test_pensia_minima_are_sursa_si_data_verificarii():
    text = _read("data/entities/pensia-minima.yaml")
    assert "brut: 1281" in text
    assert "cnpp.ro" in text
    assert "verificat: true" in text
    assert "15 ani" not in text


def test_actele_si_pasaportul_au_tarife_actuale():
    text = _read("data/entities/buletin-pasaport.yaml")
    assert "265 lei" in text
    assert "70 lei" in text
    assert "40 lei" in text
    assert "verificat: true" in text
    assert "258 lei" not in text


def test_permisul_auto_are_tariful_curent_si_schimbarea_publicata():
    text = _read("data/entities/permis-auto.yaml")
    assert "89 lei" in text
    assert "139 lei" in text
    assert "15 septembrie 2026" in text
    assert "verificat: true" in text


def test_noua_casa_nu_prezinta_cifre_2026_neconfirmate_ca_valori_curente():
    text = _read("data/entities/noua-casa.yaml")
    assert "verificat: false" in text
    assert "ultima_verificare: \"2026-09-04\"" in text
    assert "plafonul anual" in text


def test_aliasurile_romania_utila_sunt_301_si_tinta_exista():
    text = _read("data/redirects_migrare.tsv")
    expected = {
        "/romania-utila/salariul-minim/\t/ghiduri/salariul-minim/",
        "/romania-utila/alocatii/\t/ghiduri/alocatia-copii/",
        "/romania-utila/calendar-anaf/\t/ghiduri/calendar-anaf/",
    }
    rows = {line for line in text.splitlines() if line.startswith("/romania-utila/")}
    assert rows == expected
