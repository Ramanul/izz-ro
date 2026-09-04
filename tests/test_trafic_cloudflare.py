"""Partile pure ale sondei de trafic — cele care se pot verifica fara retea si fara token."""
from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("trafic_cloudflare", ROOT / "tools" / "trafic_cloudflare.py")
tc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tc)


def test_fereastra_e_in_utc_si_acopera_exact_zilele_cerute():
    assert tc.fereastra(7, date(2026, 8, 30)) == ("2026-08-23T00:00:00Z", "2026-08-30T00:00:00Z")


def test_erorile_api_ului_ajung_intregi_la_suprafata():
    """Mesajul exact ESTE rezultatul cand tokenul n-are scope. Daca il inghitim, n-am masurat."""
    assert tc.erori({"errors": [{"code": 10000, "message": "Authentication error"}]}) \
        == ["10000: Authentication error"]


def test_lipsa_erorilor_nu_inventeaza_una():
    assert tc.erori({"data": {}}) == [] and tc.erori({}) == []


def test_rezuma_extrage_cererile_pe_zi_si_script():
    raspuns = {"data": {"viewer": {"accounts": [{"workersInvocationsAdaptive": [
        {"dimensions": {"date": "2026-08-29", "scriptName": "izz-ro"},
         "sum": {"requests": 1234, "errors": 5}}]}]}}}
    assert tc.rezuma(raspuns) == [("2026-08-29 izz-ro", 1234, 5)]


def test_rezuma_arata_starea_cand_API_ul_o_trimite():
    """`status` decide daca ~1.400 de „erori" pe zi sunt excepcii reale sau clienti deconectati."""
    raspuns = {"data": {"viewer": {"accounts": [{"workersInvocationsAdaptive": [
        {"dimensions": {"date": "2026-08-29", "scriptName": "izz-failover",
                        "status": "clientDisconnected"},
         "sum": {"requests": 1400, "errors": 1400}}]}]}}}
    assert tc.rezuma(raspuns) == [("2026-08-29 izz-failover  [clientDisconnected]", 1400, 1400)]


def test_rezuma_nu_crapa_pe_raspuns_incomplet():
    """Un raspuns partial nu are voie sa arunce: sonda ar parea 'picata' cand de fapt merge."""
    for raspuns in ({}, {"data": None}, {"data": {"viewer": {"accounts": []}}},
                    {"data": {"viewer": {"accounts": [{}]}}}):
        assert tc.rezuma(raspuns) == []


def test_endpointul_e_verificat_inainte_de_apel(monkeypatch):
    """Testul negativ al gardei de endpoint: daca cineva parametrizeaza `API` cu altceva,
    apelul pica AICI, nu in productie. Semgrep semnala exact riscul asta (`file://` prin
    urllib); garda il face imposibil in loc sa-l suprime."""
    import pytest
    monkeypatch.setattr(tc, "API", "file:///etc/passwd")
    with pytest.raises(ValueError, match="endpoint neasteptat"):
        tc.interogheaza("token-fals", "cont-fals")


def test_garda_lasa_endpointul_real_sa_treaca(monkeypatch):
    """Si perechea pozitiva: garda nu blocheaza URL-ul legitim. Apelul de retea e inlocuit,
    deci testul ramane fara retea."""
    monkeypatch.setattr(tc.urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("nu ajunge aici")))
    try:
        tc.interogheaza("token-fals", "cont-fals")
    except AssertionError as exc:
        assert "nu ajunge aici" in str(exc)   # a trecut de garda, a ajuns la apel
    except ValueError:
        raise AssertionError("garda a respins endpointul real") from None
