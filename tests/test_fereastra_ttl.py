"""Garda uneltei `tools/fereastra_ttl.py`.

Unealta exista ca sa explice de ce `test_buget_fisiere.py::test_podeaua_absoluta_...` a picat
pe 13 sep si a trecut pe 14 fara nicio reparatie. Daca unealta insasi calculeaza altfel decat
garda pe care o explica, e mai rau decat inutila. De aceea primul test de aici e o
echivalenta pe starea REALA, nu pe o fixtura.

Fiecare garda are si un caz NEGATIV: o garda care nu poate pica e mai rea decat niciuna
(IZZ-0177).
"""
import datetime
import importlib.util
import json
import os
import sys
from collections import Counter

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from generator import config                                     # noqa: E402
from tools import fereastra_ttl as ft                            # noqa: E402


def _incarca(cale: str, nume: str):
    """Incarca un modul dupa CALE, nu dupa sys.path.

    `tests/` n-are `__init__.py`, iar pytest importa fisierele de test ca module de nivel
    superior (import-mode `prepend`). Un `from tests import ...` ar merge azi, dar l-ar
    incarca a doua oara sub alt nume si s-ar rupe la orice schimbare de import-mode. Calea e
    stabila indiferent de cum e invocat pytest.
    """
    spec = importlib.util.spec_from_file_location(nume, os.path.join(ROOT, cale))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


garda = _incarca("tests/test_buget_fisiere.py", "_garda_buget_fisiere")


def _stare() -> list:
    with open(os.path.join(ROOT, "data", "articles" + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def _zile(perechi) -> Counter:
    return Counter(dict(perechi))


# --- echivalenta cu garda pe care unealta o explica ---------------------------------

def test_unealta_da_ACEEASI_cifra_ca_garda_pe_starea_reala():
    """Daca cele doua se despart, raportul uneltei devine o a doua sursa de adevar."""
    articole = _stare()
    zile = ft.zile_stare(articole)
    assert ft.in_fereastra(zile, max(zile)) == garda._in_fereastra_ttl(articole)


def test_fractia_publicata_nu_se_desparte_de_garda():
    """Aceeasi masuratoare din 2026-09-09 e scrisa in doua fisiere; nu poate drifta tacit."""
    assert ft.FRACTIA_PUBLICATA == garda.FRACTIA_PUBLICATA


def test_pragul_A_e_cel_din_garda_nu_o_a_doua_parere():
    prag_a, _ = ft.praguri()
    assert prag_a == config.OUTPUT_FILE_BUDGET - config.OUTPUT_NON_ARTICLE_RESERVE


def test_pragul_B_sta_deasupra_pragului_A():
    """B e consecinta reala, A e tripwire-ul timpuriu. Ordinea inversa ar face A inutil."""
    prag_a, prag_b = ft.praguri()
    assert prag_a < prag_b


# --- ancora: fereastra nu se vindeca prin trecerea timpului --------------------------

def test_ancora_e_data_din_stare_nu_ceasul_de_azi():
    """Tot rostul garzii: o stare inghetata nu devine verde fiindca a trecut o saptamana."""
    zile = _zile([("2026-01-01", 5), ("2026-01-10", 7)])
    assert ft.in_fereastra(zile, "2026-01-10", ttl=21) == 12


def test_NEGATIV_ce_iese_din_fereastra_chiar_nu_se_numara():
    """Cazul negativ al testului de mai sus: TTL mic taie, altfel ancora n-ar conta."""
    zile = _zile([("2026-01-01", 5), ("2026-01-10", 7)])
    assert ft.in_fereastra(zile, "2026-01-10", ttl=3) == 7


def test_marginea_de_jos_e_EXCLUSIVA_exact_ca_in_garda():
    """Garda numara `d > prag`, nu `d >= prag`. O zi diferenta = ~1.000 de articole."""
    zile = _zile([("2026-01-01", 900), ("2026-01-02", 1), ("2026-01-22", 1)])
    assert ft.in_fereastra(zile, "2026-01-22", ttl=21) == 2, "ziua exact pe prag nu intra"


def test_dintele_de_fierastrau_e_reproductibil():
    """Incidentul insusi: ancora +1 zi scoate o zi intreaga, deci cifra SCADE fara reparatie."""
    zile = _zile([("2026-08-24", 1037), ("2026-09-13", 500), ("2026-09-14", 8)])
    la_13 = ft.in_fereastra(zile, "2026-09-13", ttl=21)
    la_14 = ft.in_fereastra(zile, "2026-09-14", ttl=21)
    assert la_13 == 1537 and la_14 == 508
    assert la_14 < la_13, "asta e exact iluzia de reparatie pe care unealta o demasca"


# --- proiectia: fereastra pierde zile, nu doar castiga -------------------------------

def test_proiectia_SCADE_din_ziua_care_iese_nu_doar_aduna():
    """Extrapolarea naiva marja/debit ignora ziua care iese si supraestimeaza cresterea."""
    zile = _zile([("2026-09-14", 100)] + [(f"2026-08-{d:02d}", 1000) for d in (24, 25)])
    pr = ft.proiecteaza(zile, "2026-09-14", debit=1000, orizont=1)
    # ziua 0: se completeaza la debit (100 -> 1000). ziua 1: +1000 dar iese 2026-08-25 (1000)
    assert pr[0]["n"] - pr[1]["n"] == 0, "castig 1000, pierdere 1000 => plat"


def test_NEGATIV_cand_ziua_care_iese_e_goala_proiectia_chiar_creste():
    """Cazul negativ: fara zi de scazut, aceeasi proiectie urca cu tot debitul."""
    zile = _zile([("2026-09-14", 100)])
    pr = ft.proiecteaza(zile, "2026-09-14", debit=1000, orizont=1)
    assert pr[1]["n"] - pr[0]["n"] == 1000


def test_proiectia_marcheaza_pragurile_pe_care_le_depaseste():
    zile = _zile([("2026-09-14", 1)])
    pr = ft.proiecteaza(zile, "2026-09-14", debit=99_000, orizont=1)
    assert pr[-1]["peste_A"] and pr[-1]["peste_B"]


def test_debitul_implicit_sare_ziua_IN_CURS():
    """Ziua ancorei e incompleta; bagata in median ar trage debitul artificial in jos."""
    zile = _zile([("2026-09-11", 900), ("2026-09-12", 910), ("2026-09-13", 920),
                  ("2026-09-14", 8)])
    assert ft.debit_observat(zile, "2026-09-14") == 910


# --- esecuri zgomotoase ---------------------------------------------------------------

def test_stare_fara_date_nu_raporteaza_tacut_zero():
    """Un zero tacut aici ar raporta marja maxima exact cand nu stim nimic."""
    with pytest.raises(SystemExit):
        ft.masoara([{"titlu": "fara published"}])


def test_articolele_fara_data_sunt_ignorate_nu_ghicite():
    zile = ft.zile_stare([{"published": "2026-09-14T10:00:00"}, {"published": None}, {}])
    assert zile == Counter({"2026-09-14": 1})


def test_masoara_raporteaza_marje_cu_semn():
    """Marja negativa trebuie sa se vada ca negativa, nu sa fie taiata la zero."""
    st = ft.masoara([{"published": f"2026-09-{d:02d}"} for d in range(1, 15)])
    assert st["marja_A"] == ft.praguri()[0] - st["in_fereastra"] > 0
    mare = ft.masoara([{"published": "2026-09-14"}] * 20_000)
    assert mare["marja_A"] < 0 and mare["marja_B"] < 0


def test_orizontul_zero_da_doar_ziua_curenta():
    zile = _zile([("2026-09-14", 10)])
    assert len(ft.proiecteaza(zile, "2026-09-14", debit=10, orizont=0)) == 1


def test_ancora_istorica_nu_numara_viitorul():
    """Fara marginea de sus, o ancora istorica ar include zile de dupa ea."""
    zile = _zile([("2026-09-10", 5), ("2026-09-14", 500)])
    assert ft.in_fereastra(zile, "2026-09-10", ttl=21) == 5


def test_ttl_implicit_vine_din_config_nu_din_constanta_locala():
    zile = _zile([("2026-01-01", 1), ("2026-06-01", 1)])
    ancora = "2026-06-01"
    prag = (datetime.date.fromisoformat(ancora)
            - datetime.timedelta(days=config.ARTICLE_TTL_DAYS))
    asteptat = 2 if prag <= datetime.date(2026, 1, 1) else 1
    assert ft.in_fereastra(zile, ancora) == asteptat
