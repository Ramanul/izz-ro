"""Contractul „`published` e uniform ISO UTC" — impus, nu presupus.

DE CE EXISTA, pe langa `test_published_is_utc.py`. Acela verifica STAREA COMISA: se uita in
`data/articles.json` si spune daca invariantul tine azi. E o garda de rezultat, si si-a facut
treaba — ea a ridicat regresia din 2026-09-11. Dar a ridicat-o TARZIU: commiturile de continut
sunt impinse cu `GITHUB_TOKEN`, iar GitHub nu declanseaza workflow-uri pentru asemenea push-uri,
deci datele au intrat in repo netestate si defectul a iesit la iveala abia cand un PR oarecare a
dat peste el, in merge commit.

Fisierul asta verifica MECANISMUL: ca normalizatorul exista, ca e corect pe cazuri numite, ca
`save` chiar il aplica, si ca nicio cale de parsare nu mai produce valori naive. O garda de
rezultat spune CA s-a stricat; una de mecanism spune CA NU SE POATE STRICA la fel.

Regresia, pe scurt: calea WP-JSON facea `(date_gmt or date or "")[:10]`, deci `2026-09-11`.
Lexicografic `'2026-09-11' < '2026-09-11T08:00:00+00:00'`, iar `save` sorteaza pe sir cu
`reverse=True` — asa ca 159 de anunturi de primarie aparaeu mai VECHI decat erau, in aceeasi zi.
Nu era doar un test rosu: era ordine editoriala gresita.
"""
from __future__ import annotations

import json
import re

import pytest

from generator import fetch, state
from generator.util import iso_utc

_CU_FUS = re.compile(r"([+-]\d{2}:\d{2}|Z)$")
_CITAT = re.compile(r"`[^`]*`")


def _fara_citate(linie: str) -> str:
    """Linia fara spanurile dintre backticks.

    O garda care citeste sursa trebuie sa distinga CODUL de documentatia care il citeaza —
    altfel primul lucru pe care il prinde e chiar docstringul care explica ce a fost reparat,
    iar autorul e impins sa slabeasca regula ca sa-si poata scrie explicatia. Masurat:
    exact asta s-a intamplat la prima rulare a acestui test."""
    return _CITAT.sub("", linie)


# --- normalizatorul, pe cazuri numite -------------------------------------------------

@pytest.mark.parametrize("brut,asteptat", [
    ("2026-09-11", "2026-09-11T00:00:00+00:00"),            # data goala = miezul noptii UTC
    ("2026-09-11T08:30:00", "2026-09-11T08:30:00+00:00"),   # naiv (date_gmt din WP)
    ("2026-09-11T08:30:00+00:00", "2026-09-11T08:30:00+00:00"),
    ("2026-09-11T08:30:00Z", "2026-09-11T08:30:00+00:00"),  # sufix Z
    ("2026-09-11T11:30:00+03:00", "2026-09-11T08:30:00+00:00"),  # convertit, nu doar etichetat
    ("  2026-09-11  ", "2026-09-11T00:00:00+00:00"),
])
def test_iso_utc_normalizeaza(brut, asteptat):
    assert iso_utc(brut) == asteptat


@pytest.mark.parametrize("brut", ["", "   ", None, "maine", "11.09.2026", "2026-13-45"])
def test_iso_utc_refuza_ce_nu_e_data(brut):
    """`None` inseamna „nu stiu", ca apelantul sa decida — nu o data inventata."""
    assert iso_utc(brut) is None


def test_iso_utc_e_idempotent():
    o_data = iso_utc("2026-09-11T08:30:00")
    assert iso_utc(o_data) == o_data


# --- preventia: calea WP-JSON nu mai produce valori naive ------------------------------

@pytest.mark.parametrize("entry,asteptat", [
    ({"date_gmt": "2026-09-11T08:30:00", "date": "2026-09-11T11:30:00"},
     "2026-09-11T08:30:00+00:00"),                       # date_gmt are prioritate
    ({"date": "2026-09-11T11:30:00"}, "2026-09-11T11:30:00+00:00"),   # fallback pe `date`
    ({"date_gmt": "", "date": "2026-09-11"}, "2026-09-11T00:00:00+00:00"),
])
def test_wp_published_iese_cu_fus(entry, asteptat):
    assert fetch._wp_published(entry) == asteptat


def test_wp_published_fara_nicio_data_cade_pe_acum():
    rezultat = fetch._wp_published({})
    assert _CU_FUS.search(rezultat), rezultat


def test_wp_published_nu_mai_trunchiaza():
    """Regresia exacta: `[:10]` pastra doar ziua. Ora trebuie sa supravietuiasca."""
    assert fetch._wp_published({"date_gmt": "2026-09-11T08:30:00"}) != "2026-09-11"


# --- vindecarea: `save` repara randurile deja scrise -----------------------------------

def _articol(url: str, published: str) -> dict:
    return {"url": url, "title": "t", "published": published, "source": "s",
            "category": "actualitate"}


def test_save_normalizeaza_randurile_naive(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_PATH", str(tmp_path / "articles.json"))
    state.save([
        _articol("https://a.ro/1", "2026-09-11"),                     # naiv, ca cele 159
        _articol("https://a.ro/2", "2026-09-11T08:00:00+00:00"),      # deja corect
    ])
    salvate = json.loads((tmp_path / "articles.json").read_text(encoding="utf-8"))
    assert all(_CU_FUS.search(a["published"]) for a in salvate), salvate


def test_save_repara_si_ordinea_nu_doar_formatul(tmp_path, monkeypatch):
    """Miezul problemei. Naiv, `2026-09-11` se sorta DUPA `2026-09-11T08:00:00+00:00`, adica
    anuntul de la pranz aparea mai vechi decat cel de dimineata."""
    monkeypatch.setattr(state, "STATE_PATH", str(tmp_path / "articles.json"))
    state.save([
        _articol("https://a.ro/dimineata", "2026-09-11T08:00:00+00:00"),
        _articol("https://a.ro/pranz", "2026-09-11T12:00:00"),   # naiv, dar mai NOU
    ])
    salvate = json.loads((tmp_path / "articles.json").read_text(encoding="utf-8"))
    assert [a["url"] for a in salvate] == ["https://a.ro/pranz", "https://a.ro/dimineata"]


def test_save_nu_atinge_ce_e_deja_corect(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_PATH", str(tmp_path / "articles.json"))
    original = "2026-09-11T08:00:00+00:00"
    state.save([_articol("https://a.ro/1", original)])
    salvate = json.loads((tmp_path / "articles.json").read_text(encoding="utf-8"))
    assert salvate[0]["published"] == original


def test_save_lasa_in_pace_articolele_fara_data(tmp_path, monkeypatch):
    """Lipsa datei e o stare legitima; normalizatorul nu are voie sa inventeze una."""
    monkeypatch.setattr(state, "STATE_PATH", str(tmp_path / "articles.json"))
    art = _articol("https://a.ro/1", "")
    state.save([art])
    salvate = json.loads((tmp_path / "articles.json").read_text(encoding="utf-8"))
    assert salvate[0]["published"] == ""


@pytest.mark.parametrize("intrare", [None, "un sir", 123, ["lista"], {"published": 20260911},
                                     {"published": None}, {}])
def test_normalizatorul_nu_cade_pe_intrari_malformate(intrare):
    """Contract preexistent, prins de `test_state_resync`: o intrare stricata nu are voie sa
    opreasca pipeline-ul, fiindca `load` nu prinde `AttributeError`. Masurat: prima versiune a
    normalizatorului chema `.get()` pe orice si a rupt cinci teste."""
    assert state._impune_published_utc([intrare]) == 0


def test_impune_published_utc_numara_doar_reparatiile():
    articole = [
        _articol("https://a.ro/1", "2026-09-11"),                  # reparat
        _articol("https://a.ro/2", "2026-09-11T08:00:00+00:00"),   # deja bun
        _articol("https://a.ro/3", ""),                            # sarit
        _articol("https://a.ro/4", "nu e o data"),                 # nereparabil, lasat asa
    ]
    assert state._impune_published_utc(articole) == 1
    assert articole[3]["published"] == "nu e o data"


# --- garda pe invariant: nicio cale de parsare nu produce valori naive ------------------

def test_toate_caile_de_data_ies_cu_fus():
    """Cele patru cai din `fetch`, verificate impreuna. A patra a fost cea care a rupt
    contractul; testul le tine pe toate sub aceeasi conditie, nu doar pe cea reparata."""
    rezultate = {
        "_parse_ro_date": fetch._parse_ro_date("11.09.2026"),
        "_parse_ro_date (gunoi)": fetch._parse_ro_date("nu e data"),
        "_wp_published": fetch._wp_published({"date_gmt": "2026-09-11T08:30:00"}),
        "_wp_published (gol)": fetch._wp_published({}),
    }
    fara_fus = {nume: val for nume, val in rezultate.items() if not _CU_FUS.search(val)}
    assert not fara_fus, f"cai care produc `published` naiv: {fara_fus}"


def test_nicio_trunchiere_de_data_in_fetch():
    """Garda pe TIPAR, nu pe linia de azi: `[:10]` pe un camp de data taie si fusul.

    Reintroducerea ei ar rupe contractul exact la fel, tacut. Aici se vede la prima rulare.
    """
    from pathlib import Path
    sursa = Path(fetch.__file__).read_text(encoding="utf-8").splitlines()
    suspecte = [
        f"  fetch.py:{nr}: {linie.strip()}"
        for nr, linie in enumerate(sursa, 1)
        if re.search(r'(date_gmt|"date"|published).*\[:10\]', _fara_citate(linie))
        and not linie.lstrip().startswith("#")
    ]
    assert not suspecte, "data trunchiata la 10 caractere:\n" + "\n".join(suspecte)
