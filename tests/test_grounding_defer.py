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


# --- aplica_defer: defer dupa toata procesarea AI, cu restaurare pe upgrade -------

from generator import raport_copiere as rc  # noqa: E402


def test_articol_nou_blocat_iese_din_stare():
    articol = {"url": "https://a.test/x", "original_link": "https://a.test/x", "title": "Nou"}
    iesire, amanate, nerezolvate = rc.aplica_defer(
        [articol], {"https://a.test/x"}, {}, {"https://a.test/x"})
    assert iesire == [] and amanate == 1 and nerezolvate == []


def test_articol_nou_blocat_pe_original_link_iese():
    articol = {"url": "https://a.test/normalizat", "original_link": "https://a.test/raw", "title": "Nou"}
    iesire, amanate, _ = rc.aplica_defer([articol], {"https://a.test/raw"}, {}, {"https://a.test/raw"})
    assert iesire == [] and amanate == 1


def test_upgrade_blocat_se_restaureaza_din_instantaneu():
    vechi = {"url": "https://a.test/v", "original_link": "https://a.test/v", "title": "Vechi bun"}
    mutat = dict(vechi, title="Sinteza cu cifra straina")
    instantanee = {"https://a.test/v": vechi}
    iesire, amanate, nerezolvate = rc.aplica_defer([mutat], {"https://a.test/v"}, instantanee, set())
    assert amanate == 1 and nerezolvate == []
    assert iesire[0]["title"] == "Vechi bun"  # continutul vechi, deja public, ramane


def test_blocat_fara_instantaneu_si_fara_statut_de_nou_ramane_si_se_raporteaza():
    vechi = {"url": "https://a.test/v", "title": "Vechi"}
    iesire, amanate, nerezolvate = rc.aplica_defer([vechi], {"https://a.test/v"}, {}, set())
    assert iesire == [vechi] and amanate == 1 and nerezolvate == ["https://a.test/v"]


def test_fara_blocante_lista_ramane_intacta():
    articole = [{"url": "https://a.test/1"}, {"url": "https://a.test/2"}]
    iesire, amanate, nerezolvate = rc.aplica_defer(articole, set(), {}, set())
    assert iesire == articole and amanate == 0 and nerezolvate == []
