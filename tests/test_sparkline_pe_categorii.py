"""Liniile-tendință per categorie (render._sparkline_pe_categorii): forma, cifra zilei
și omiterea cinstită a categoriilor goale — o linie desenată fără date minte."""
from datetime import datetime, timedelta, timezone

from generator import render


def _a(cat: str, zile_ago: int, ora: int = 12) -> dict:
    dt = datetime.now(timezone.utc) - timedelta(days=zile_ago)
    dt = dt.replace(hour=ora, minute=0, second=0, microsecond=0)
    return {"category": cat, "published": dt.isoformat()}


CATEGORII = ["politic", "sport"]


def test_numara_pe_zi_si_determinism():
    articole = [_a("politic", 0), _a("politic", 0, 15), _a("politic", 2),
                _a("sport", 1)]
    out = render._sparkline_pe_categorii(articole, CATEGORII)
    assert out["politic"]["azi"] == 2
    assert out["politic"]["total"] == 3
    assert len(out["politic"]["puncte"].split()) == render._FEREASTRA_SPARK
    assert out["sport"]["azi"] == 0 and out["sport"]["total"] == 1
    assert out == render._sparkline_pe_categorii(articole, CATEGORII)


def test_categorie_fara_stiri_in_fereastra_lipseste():
    out = render._sparkline_pe_categorii([_a("sport", 1)], CATEGORII)
    assert "politic" not in out          # zero absolut: nicio forma, nu o linie goala
    assert "sport" in out


def test_stiri_vechi_peste_fereastra_nu_lichideaza_linia():
    out = render._sparkline_pe_categorii([_a("politic", 30)], CATEGORII)
    assert "politic" not in out


def test_toate_valorile_zero_deseneaza_linie_de_baza():
    # o categorie cu exact o stire acum 6 zile: linia exista, restul zilelor = 0
    out = render._sparkline_pe_categorii([_a("sport", 6)], CATEGORII)
    p = [tuple(x.split(",")) for x in out["sport"]["puncte"].split()]
    assert len(p) == render._FEREASTRA_SPARK
    ys = [float(y) for _, y in p]
    assert ys[-1] > ys[0]                # maximul (ultima zi) e sus, restul pe baza


def test_publicat_lipsa_sau_stricat_ignorat():
    articole = [{"category": "politic", "published": None},
                {"category": "politic", "published": "garbage"},
                _a("politic", 0)]
    out = render._sparkline_pe_categorii(articole, CATEGORII)
    assert out["politic"]["azi"] == 1
