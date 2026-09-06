"""Teste offline pentru fetcher-ul de poze de eveniment (clasa A)."""
import datetime
import importlib.util
import os


spec = importlib.util.spec_from_file_location(
    "fep", os.path.join(os.path.dirname(__file__), "..", "tools", "fetch_eventphotos.py"))
fep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fep)


def test_event_noun_recunoaste_evenimentele_din_dict():
    assert fep.event_noun("Viitură catastrofală la graniță") == "flood"
    assert fep.event_noun("Inundațiile din Nepal") == "flood"
    assert fep.event_noun("Cutremur de 5,2 în Vrancea") == "earthquake"
    assert fep.event_noun("Incendiu într-un depozit") == "fire"
    assert fep.event_noun("Protest în fața prefecturii") == "protest"
    assert fep.event_noun("Măturile străzii au fost luate de vânt") is None


def test_fereastra_asimetrica_spre_trecut():
    f = fep._fereastra("2026-09-02")
    assert f == (datetime.date(2026, 8, 26), datetime.date(2026, 9, 4))
    assert fep._fereastra("garbage") is None
    assert fep._fereastra(None) is None


def test_in_fereastra_inclusiv_la_capete():
    f = (datetime.date(2026, 8, 26), datetime.date(2026, 9, 4))
    assert fep._in_fereastra("2026-08-26", f)
    assert fep._in_fereastra("2026-09-04", f)
    assert not fep._in_fereastra("2026-08-25", f)
    assert not fep._in_fereastra("", f)


def test_cauta_filtrare_pe_extensie(monkeypatch):
    payload = {"query": {"pages": {
        "1": {"title": "File:Flood in Nepal.jpg",
              "imageinfo": [{"thumburl": "x", "width": 1400, "height": 900,
                             "descriptionurl": "p",
                             "extmetadata": {"LicenseShortName": {"value": "Public domain"},
                                             "DateTimeOriginal": {"value": "2026-08-26"}}}]},
        "2": {"title": "File:map.svg",
              "imageinfo": [{"thumburl": "y", "width": 1400, "height": 900,
                             "descriptionurl": "p", "extmetadata": {}}]}}}}

    class FP:
        LEAD_W = 1400
        UA = {}

        @staticmethod
        def _get(url):
            return payload

        @staticmethod
        def clean_html(s):
            return s

    fep.lp.fp = FP()
    rows = fep.cauta("nepal flood")
    assert len(rows) == 1  # svg-ul e aruncat
    assert rows[0]["license"] == "Public domain" and rows[0]["data"] == "2026-08-26"
