"""Masthead-ul de ziar: data RO + „numerele zilei" (Faza 1 din recuperarea #297).

Pazeste trei lucruri care se pot rupe tacut:
  1. fereastra de 24h — o stire de 25h trebuie sa iasa, una de 2h sa intre;
  2. strip-ul nu arata zerori falsi — fara stiri in fereastra, `zi` e None;
  3. judetele se numara prin `geo.judet_sursa`, aceeasi atribuire ca pe harta.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _art(published, source="zcj", category="judetean"):
    return {"published": published, "source": source, "category": category}


def test_fereastra_de_24h_este_corecta():
    acum = datetime.now(timezone.utc)
    stiri = [
        _art((acum - timedelta(hours=2)).isoformat()),
        _art((acum - timedelta(hours=23)).isoformat()),
        _art((acum - timedelta(hours=25)).isoformat()),   # iesit din fereastra
        _art("2020-01-01T00:00:00+00:00"),                # iesit de tot
        _art("data-invalida"),                            # stricat: sarit, nu crah
    ]
    zi = render._numerele_zilei(stiri)
    assert zi["stiri"] == 2


def test_fara_stiri_in_fereastra_nu_arata_zerori():
    acum = datetime.now(timezone.utc)
    vechi = [_art((acum - timedelta(hours=48)).isoformat())]
    assert render._numerele_zilei(vechi) is None
    assert render._numerele_zilei([]) is None


def test_sursele_distincte_se_numara_o_singura_data():
    acum = datetime.now(timezone.utc)
    stiri = [
        _art((acum - timedelta(hours=1)).isoformat(), source="zcj"),
        _art((acum - timedelta(hours=2)).isoformat(), source="zcj"),
        _art((acum - timedelta(hours=3)).isoformat(), source="adp"),
    ]
    zi = render._numerele_zilei(stiri)
    assert zi["stiri"] == 3 and zi["surse"] == 2


def test_judetele_venite_din_cheia_sursei_se_numara():
    acum = datetime.now(timezone.utc)
    stiri = [
        _art((acum - timedelta(hours=1)).isoformat(), source="pl_cluj_judelean"),
        _art((acum - timedelta(hours=2)).isoformat(), source="pl_cluj_judelean_2"),
        _art((acum - timedelta(hours=3)).isoformat(), source="cj_dambovita_anunt"),
        # local fara judet in cheie si nedeclarat: nu se numara nicaieri, nu crapa
        _art((acum - timedelta(hours=4)).isoformat(), source="necunoscut", category="local"),
    ]
    zi = render._numerele_zilei(stiri)
    assert zi["judete"] == 2
    assert zi["pe_judet"]["CLUJ"] == 2 and zi["pe_judet"]["DAMBOVITA"] == 1


def test_timpul_fara_fus_se_trateaza_ca_utc():
    acum = datetime.now(timezone.utc)
    stiri = [_art((acum - timedelta(hours=1)).replace(tzinfo=None).isoformat())]
    assert render._numerele_zilei(stiri)["stiri"] == 1


def test_today_ro_arata_zi_si_luna_in_romana():
    azi = render._today_ro()
    assert any(d in azi for d in render._RO_DAYS), azi
    assert any(l in azi for l in render._RO_MONTHS[1:]), azi


def test_mastheadul_are_regulile_in_css_si_marker_in_sablon():
    with open(os.path.join(ROOT, "static", "styles.css"), encoding="utf-8") as fh:
        css = fh.read()
    assert ".dateline {" in css and ".day-numbers {" in css
    with open(os.path.join(ROOT, "templates", "base.html"), encoding="utf-8") as fh:
        base = fh.read()
    assert "day-numbers" in base and "{% if zi %}" in base
