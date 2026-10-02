"""Garda „published din viitor": o dată de eveniment parsată din textul anunțului nu are
voie să ajungă data de publicare — cazul real: Voiteg/Retim Ecologic cu „01.01.2027"
într-un anunț publicat în octombrie 2026, care împingea „actualizat …" din statistici
în viitor. Clamp-ul din generator.fetch._clamp_future cade pe momentul crawl-ului."""
from datetime import datetime, timedelta, timezone

from generator.fetch import _clamp_future


def test_data_din_viitor_cade_pe_crawl():
    acum = datetime.now(timezone.utc)
    viitor = (acum + timedelta(days=90)).isoformat()
    out = datetime.fromisoformat(_clamp_future(viitor))
    assert abs((out - acum).total_seconds()) < 60


def test_in_marja_de_48h_ramane_neatinsa():
    acum = datetime.now(timezone.utc)
    aproape = (acum + timedelta(hours=40)).isoformat()
    assert _clamp_future(aproape) == aproape


def test_data_din_trecut_ramane_neatinsa():
    trecut = "2024-03-05T10:00:00+00:00"
    assert _clamp_future(trecut) == trecut


def test_valori_neparsabile_se_predau_neatinsa():
    assert _clamp_future("nu-e-data") == "nu-e-data"
