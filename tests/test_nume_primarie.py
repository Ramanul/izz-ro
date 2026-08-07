"""Numele afisat al unei surse de primarie: cu diacritice, fara prefix administrativ.

Ce repara: coloana `localitate` din `primarii_status.csv` e in MAJUSCULE FARA DIACRITICE, iar
formula veche era `"Primăria " + localitate.title()` — care nu le poate inventa. Masurat pe
`data/articles.json` la 2026-08-06: 39 de nume distincte stricate, pe 143 de articole publicate
(„Primăria Municipiul Sebes", „Primăria Oras Navodari"). Numele apare pe FIECARE card al sursei.

Diacriticele vin din `data/localities.json` prin `localities.match`, care cere potrivire pe
judet — obligatorie, fiindca exista omonime in judete diferite.
"""
import pytest

from generator import local_sources as ls
from generator import localities


@pytest.fixture(scope="module")
def by_name():
    d = localities.load_dataset()
    if not d:
        pytest.skip("data/localities.json lipseste")
    return d


@pytest.mark.parametrize("judet,localitate,asteptat", [
    ("PRAHOVA", "MUNICIPIUL PLOIESTI", "Primăria Ploiești"),
    ("PRAHOVA", "ORAS BAICOI", "Primăria Băicoi"),
    ("ALBA", "MUNICIPIUL SEBES", "Primăria Sebeș"),
    ("CONSTANTA", "ORAS NAVODARI", "Primăria Năvodari"),
    ("ALBA", "ROSIA MONTANA", "Primăria Roșia Montană"),
    # cratima vine si ea din dataset, nu din CSV
    ("CLUJ", "MUNICIPIUL CLUJ NAPOCA", "Primăria Cluj-Napoca"),
])
def test_diacriticele_si_prefixul(judet, localitate, asteptat, by_name):
    assert ls.nume_primarie(judet, localitate, by_name) == asteptat


def test_prefixul_administrativ_dispare(by_name):
    """„Primăria Municipiul Ploiesti" e gresit gramatical (ar cere genitivul). Se scoate
    prefixul in loc sa se declineze: mai scurt, corect, si identic ca forma cu intrarile
    scrise de mana din config.py („Primăria Buzău")."""
    for forma in ("MUNICIPIUL PLOIESTI", "MUNICIPIUL PLOIESTI", "ORASUL PLOIESTI"):
        assert "Municipiul" not in ls.nume_primarie("PRAHOVA", forma, by_name)
        assert "Oras" not in ls.nume_primarie("PRAHOVA", forma, by_name)


def test_orastioara_nu_e_confundata_cu_oras(by_name):
    """Regresie deja platita o data in `_impact_tier` (review 2026-07-24): „ORASTIOARA DE SUS"
    e o COMUNA care CONTINE „ORAS". Prefixul se taie pe cuvant intreg, nu pe substring —
    altfel numele ar deveni „Primăria Tioara De Sus"."""
    n = ls.nume_primarie("HUNEDOARA", "ORASTIOARA DE SUS", by_name)
    assert n.startswith("Primăria Or"), n


def test_fara_dataset_cade_pe_comportamentul_vechi():
    """Un nume imperfect e mai bun decat o sursa pierduta: fara `localities.json`, functia
    trebuie sa se comporte ca formula veche, nu sa ridice."""
    assert ls.nume_primarie("PRAHOVA", "MUNICIPIUL PLOIESTI", {}) == "Primăria Ploiesti"


def test_localitate_necunoscuta_nu_arunca(by_name):
    assert ls.nume_primarie("BUZAU", "XYZ INEXISTENT", by_name) == "Primăria Xyz Inexistent"


def test_judetul_gresit_nu_imprumuta_alt_nume(by_name):
    """Potrivirea pe judet e obligatorie. O localitate cerută din judetul gresit trebuie sa
    cada pe `.title()`, NU sa ia inregistrarea omonima din alt judet — aceeasi regula care
    impiedica fotografia altui oras sa ajunga pe o stire locala."""
    corect = ls.nume_primarie("ALBA", "MUNICIPIUL SEBES", by_name)
    gresit = ls.nume_primarie("TULCEA", "MUNICIPIUL SEBES", by_name)
    assert corect == "Primăria Sebeș"
    assert gresit == "Primăria Sebes"


def test_sursele_gold_reale_au_diacritice(by_name):
    """Control pe datele reale, nu doar pe cazuri alese: niciuna din sursele active nu are voie
    sa poarte un prefix administrativ in nume."""
    src = ls.load_gold_sources("data/primarii_status.csv", 120)
    assert len(src) > 50, f"prea putine surse ({len(src)}) — CSV-ul lipseste?"
    rele = [s["name"] for s in src.values()
            if any(p in s["name"] for p in ("Municipiul", "Oras ", "Orasul", "Comuna "))]
    assert not rele, f"prefix administrativ ramas in: {rele[:3]}"
