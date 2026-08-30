"""Registrul nu poate avea doua randuri cu acelasi ID -- si nici nu se poate scrie asa.

DE CE EXISTA (2026-08-22, `IZZ-0241`). Pe 21 august, patru sesiuni au lucrat in paralel pe acelasi
`main` si doua ID-uri au fost revendicate de cate doua ramuri: IZZ-0237 de #204 si #205, IZZ-0238
de #204 si #206. Cauza e mecanica, nu neatentie: `_next_id` ia `max+1` peste randurile pe care le
vede ramura ei, iar toate patru vedeau acelasi ultim ID (IZZ-0236). `tools/registru.py` avea garda
pe TITLU duplicat (`_cheie`, linia ~156) si NICIUNA pe ID, iar `tests/test_registru*.py` nu exista
deloc -- deci ciocnirea nu avea cum sa fie semnalata de nimeni.

Ce NU rezolva garda asta, spus explicit: nu face alocarea sigura intre ramuri. Doua sesiuni care
nu se vad una pe alta vor continua sa calculeze aceeasi cifra, si fiecare ramura in parte va fi
consistenta cu ea insasi -- ar cere un lacat partajat, pe care nu-l avem. Ce face este sa opreasca
ateriz*rea* tacuta: `tests.yml` ruleaza pe fiecare pull_request, iar GitHub verifica starea MERGED
a PR-ului, deci a doua ramura care incearca sa intre cu un ID deja luat iese rosie in loc sa
suprascrie evidenta primei. Registrul e append-only (§20); o suprascriere tacuta e exact defectul
pe care registrul are rolul sa-l previna.

Fiecare garda are aici si test NEGATIV, pe intrare stricata dinadins: o garda care nu poate esua
e mai rea decat niciuna (`IZZ-0177`).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools.registru as registru  # noqa: E402


def _rand(id_: str, titlu: str = "ceva") -> dict:
    return {"id": id_, "data": "2026-08-22", "zona": "proces", "titlu": titlu,
            "stare": "propus", "decident": "claude", "dovada": "", "motiv": "", "leaga": ""}


def test_registrul_livrat_nu_are_id_duplicat():
    """Fisierul real. Asta e aserttiunea care ar fi prins IZZ-0237 si IZZ-0238."""
    assert registru.id_duplicate(registru._read()) == []


def test_garda_prinde_id_duplicat():
    """NEGATIV: exact forma ciocnirii din 21 august -- acelasi ID, doua titluri diferite."""
    incalcari = registru.id_duplicate([
        _rand("IZZ-0236"), _rand("IZZ-0237", "dosar resurse"), _rand("IZZ-0237", "poze CC BY"),
    ])
    assert incalcari == ["IZZ-0237 apare de 2 ori"]


def test_garda_prinde_si_randul_fara_id():
    """NEGATIV: doua randuri cu id gol sunt tot o ciocnire, doar ca fara cifra de aratat."""
    assert registru.id_duplicate([_rand(""), _rand("")]) == ["(gol) apare de 2 ori"]


def test_scrierea_refuza_id_duplicat(tmp_path, monkeypatch):
    """NEGATIV, pe cealalta jumatate: garda nu doar raporteaza, ci opreste scrierea."""
    tinta = tmp_path / "registru.tsv"
    monkeypatch.setattr(registru, "PATH", str(tinta))
    with pytest.raises(SystemExit) as exc:
        registru._write([_rand("IZZ-0001"), _rand("IZZ-0001")])
    assert "IZZ-0001" in str(exc.value)
    assert not tinta.exists(), "a scris desi trebuia sa refuze"


def test_scrierea_merge_cand_id_urile_sunt_unice(tmp_path, monkeypatch):
    """POZITIV, ca garda sa nu fie doar un blocaj: calea buna ramane deschisa."""
    tinta = tmp_path / "registru.tsv"
    monkeypatch.setattr(registru, "PATH", str(tinta))
    registru._write([_rand("IZZ-0002"), _rand("IZZ-0001")])
    linii = tinta.read_text(encoding="utf-8").splitlines()
    assert linii[0].split("\t")[0] == "id"
    assert [ln.split("\t")[0] for ln in linii[1:]] == ["IZZ-0001", "IZZ-0002"]


def test_next_id_nu_intoarce_un_id_deja_luat():
    randuri = registru._read()
    assert registru._next_id(randuri) not in {r["id"] for r in randuri}
