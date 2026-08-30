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
        {"dimensions": {"datetime": "2026-08-29T00:00:00Z", "scriptName": "izz-ro"},
         "sum": {"requests": 1234, "errors": 5}}]}]}}}
    assert tc.rezuma(raspuns) == [("2026-08-29 izz-ro", 1234, 5)]


def test_rezuma_nu_crapa_pe_raspuns_incomplet():
    """Un raspuns partial nu are voie sa arunce: sonda ar parea 'picata' cand de fapt merge."""
    for raspuns in ({}, {"data": None}, {"data": {"viewer": {"accounts": []}}},
                    {"data": {"viewer": {"accounts": [{}]}}}):
        assert tc.rezuma(raspuns) == []
