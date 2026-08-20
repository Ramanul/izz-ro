"""Cele PATRU cai de procesare scriu efectiv in jurnalul de suprapunere.

De ce un test separat de `test_suprapunere_copiere.py`: acolo se verifica masuratoarea,
aici se verifica CABLAJUL. Sunt moduri de esec diferite — o functie corecta pe care n-o
apeleaza nimeni arata exact ca o functie care merge, si fix asta s-a intamplat cu
`verifica_sinteza.py`: cod bun, scris de mult, apelat doar de o unealta offline, deci
niciodata rulat la generare.

Auditul din 20 aug numarase TREI cai (`00-PLAN-DE-ACTIUNE.md`, [C2]). Sunt patru:
`process_clusters_batch` — model C in lot — lipsea din inventar. Testul asta o acopera
explicit ca sa nu se mai piarda.
"""
import json

import pytest

from generator import process


class ProviderFals:
    """Tine locul modelului: intoarce un raspuns fix, fara apel de retea."""

    name = "provider-fals"
    calls = 0
    failures = 0

    def __init__(self, raspuns: str):
        self._raspuns = raspuns

    def complete(self, system, user):        # noqa: ARG002 - semnatura impusa de apelant
        return self._raspuns


@pytest.fixture
def jurnal(tmp_path, monkeypatch):
    """Redirecteaza jurnalul in tmp si intoarce o functie care-l citeste."""
    cale = tmp_path / "raport.jsonl"
    monkeypatch.setattr("generator.raport_copiere.CALE", cale)
    def randuri():
        if not cale.exists():
            return []
        return [json.loads(x) for x in cale.read_text(encoding="utf-8").splitlines() if x.strip()]
    return randuri


# Textul sursei contine o propozitie pe care „modelul" o va da inapoi neschimbata.
COPIAT = "lucrarile de reabilitare a stadionului vor incepe in luna septembrie"
SURSA_DESC = f"Primaria a anuntat ca {COPIAT}, cu buget de 12 milioane de lei."


def _item():
    return {"original_title": "Stadionul intra in renovare",
            "description": SURSA_DESC,
            "original_link": "http://exemplu.ro/stadion",
            "source_name": "Exemplu", "published": "2026-08-20T10:00:00+00:00"}


def test_model_B_singur_scrie_in_jurnal(jurnal):
    raspuns = json.dumps({"title": "Stadionul intra in renovare",
                          "teaser": f"Se anunta ca {COPIAT}.",
                          "entities": [], "category": "administratie", "icon": None})
    process.process_single(_item(), ProviderFals(raspuns))
    r = jurnal()
    assert len(r) == 1, "calea B singura nu a scris nimic"
    assert r[0]["model"] == "B"
    assert r[0]["text_max_cuvinte"] >= 8, "propozitia copiata nu a fost prinsa"


def test_model_B_in_lot_scrie_in_jurnal(jurnal):
    raspuns = json.dumps([{"id": 0, "title": "Stadionul intra in renovare",
                           "teaser": f"Se anunta ca {COPIAT}.",
                           "entities": [], "category": "administratie", "icon": None}])
    process.process_batch([_item()], ProviderFals(raspuns))
    r = jurnal()
    assert len(r) == 1, "calea B in lot nu a scris nimic"
    assert r[0]["text_max_cuvinte"] >= 8


def test_model_C_singur_scrie_in_jurnal(jurnal):
    raspuns = json.dumps({"title": "Stadionul intra in renovare",
                          "synthesis": f"Autoritatile spun ca {COPIAT}.",
                          "entities": [], "category": "administratie", "icon": None})
    process.process_cluster([_item()], ProviderFals(raspuns))
    r = jurnal()
    assert len(r) == 1, "calea C singura nu a scris nimic"
    assert r[0]["model"] == "C"
    assert r[0]["text_max_cuvinte"] >= 8


def test_model_C_in_lot_scrie_in_jurnal(jurnal):
    """Calea pe care auditul o ratase. Fara test, s-ar pierde din nou la urmatorul refactor."""
    raspuns = json.dumps([{"id": 0, "title": "Stadionul intra in renovare",
                           "synthesis": f"Autoritatile spun ca {COPIAT}.",
                           "entities": [], "category": "administratie", "icon": None}])
    process.process_clusters_batch([[_item()]], ProviderFals(raspuns))
    r = jurnal()
    assert len(r) == 1, "calea C in lot nu a scris nimic"
    assert r[0]["model"] == "C"
    assert r[0]["text_max_cuvinte"] >= 8


def test_reformularea_reala_nu_produce_semnal(jurnal):
    """Contra-proba: daca modelul chiar reformuleaza, jurnalul trebuie sa arate curat.

    Fara testul asta n-as sti daca masuratoarea e utila sau doar aprinsa mereu.
    """
    raspuns = json.dumps({"title": "Renovare la stadion din toamna",
                          "teaser": "Arena orasului va fi modernizata, pentru 12 milioane de lei.",
                          "entities": [], "category": "administratie", "icon": None})
    process.process_single(_item(), ProviderFals(raspuns))
    r = jurnal()
    assert len(r) == 1
    assert r[0]["text_procent"] == 0.0
    assert r[0]["text_max_cuvinte"] < 8


def test_jurnalul_stricat_nu_opreste_publicarea(tmp_path, monkeypatch):
    """Daca scrierea jurnalului esueaza, articolul se publica oricum.

    O plasa de siguranta care poate darama rularea e mai rea decat lipsa ei — regula 2 din
    antetul lui `raport_copiere`. Simulez esecul cu o cale imposibila.
    """
    monkeypatch.setattr("generator.raport_copiere.CALE", tmp_path / "\0" / "imposibil.jsonl")
    raspuns = json.dumps({"title": "Titlu", "teaser": "Text oarecare.",
                          "entities": [], "category": "administratie", "icon": None})
    rezultat = process.process_single(_item(), ProviderFals(raspuns))
    assert rezultat is not None, "un jurnal nescriibil a amanat un articol bun"
    assert rezultat["title"] == "Titlu"
