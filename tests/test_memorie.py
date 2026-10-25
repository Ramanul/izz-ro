"""E4 — memoria subiectelor și Garda Memoriei (`generator/memorie.py`)."""
from datetime import datetime, timezone

from generator import memorie


def _rep(story, titlu, fapt, ent, d="2026-06-10", milestone=True, hedged=False, state="SYNTHESIS_VALID"):
    return {"story_id": story, "title": titlu, "published": f"{d}T10:00:00+00:00",
            "original_link": f"https://a.ro/{story}", "entities": ent, "model": "C",
            "dialectic": {"v": "e2-v1", "state": state, "milestone": milestone,
                          "common": [{"text": fapt, "src": ["Alfa", "Beta"], "hedged": hedged}]}}


LEGE = _rep("st-1", "Legea pălincii, promulgată", "Președintele a promulgat legea producției casnice de pălincă.",
            ["Nicușor Dan", "Parlamentul", "pălincă"])


def test_garda_lasa_doar_decizii_incheiate_fara_stari_judiciare():
    assert memorie.eligibil(LEGE)
    assert not memorie.eligibil(_rep("st-2", "Primar reținut", "Primarul a fost reținut de procurori.", ["X"]))
    assert not memorie.eligibil(_rep("st-3", "Condamnare definitivă", "Fostul ministru a fost condamnat definitiv.", ["Y"]))
    assert not memorie.eligibil(_rep("st-4", "t", "f", ["Z"], milestone=False))
    assert not memorie.eligibil(_rep("st-5", "t", "Bugetul a fost aprobat.", ["Z"], hedged=True))
    assert not memorie.eligibil(_rep("st-6", "t", "Bugetul a fost aprobat.", ["Z"], state="SINGLE_ORIGIN"))


def test_corectia_sau_retragerea_scoate_randul_si_din_memorie(tmp_path):
    cale = str(tmp_path / "m.json")
    acum = datetime(2026, 10, 23, tzinfo=timezone.utc)
    r = memorie.actualizeaza([LEGE], {}, cale=cale, acum=acum)
    assert r["adaugate"] == 1 and r["total"] == 1
    r = memorie.actualizeaza([], {"corrections": {"https://a.ro/st-1": {"title": "x"}}}, cale=cale, acum=acum)
    assert r["total"] == 0 and r["scoase"] == 1


def test_pastrarea_e_finita_12_luni(tmp_path):
    cale = str(tmp_path / "m.json")
    memorie.actualizeaza([_rep("st-v", "t", "Bugetul a fost aprobat.", ["Bihor"], d="2025-09-01")], {},
                         cale=cale, acum=datetime(2026, 10, 23, tzinfo=timezone.utc))
    assert memorie.incarca(cale) == []


def test_memoria_apare_doar_dincolo_de_fereastra_si_pe_acelasi_subiect(tmp_path):
    cale = str(tmp_path / "m.json")
    memorie.actualizeaza([LEGE], {}, cale=cale, acum=datetime(2026, 10, 23, tzinfo=timezone.utc))
    reg = memorie.incarca(cale)
    azi = {"story_id": "st-nou", "published": "2026-10-23T08:00:00+00:00",
           "title": "Producția casnică de pălincă scutită de accize intră în vigoare",
           "entities": ["Nicușor Dan", "pălincă", "Guvernul"]}
    gasite = memorie.din_memorie(azi, reg, ttl_zile=12)
    assert [e["story"] for e in gasite] == ["st-1"]
    assert memorie.din_memorie(dict(azi, entities=["Nicușor Dan", "Guvernul"]), reg, 12) == []   # o singură entitate specifică
    assert memorie.din_memorie(dict(azi, published="2026-06-15T08:00:00+00:00"), reg, 12) == []  # încă în fereastră


def test_entitatile_generice_nu_leaga_subiecte_diferite(tmp_path):
    """Argon R5: („Guvernul", „România") sau („PSD", „PNL") sunt în jumătate din știri."""
    cale = str(tmp_path / "m.json")
    vechi = _rep("st-g", "Guvernul a aprobat bugetul", "Guvernul a aprobat bugetul pe anul viitor.",
                 ["Guvernul", "România", "PSD", "PNL"])
    memorie.actualizeaza([vechi], {}, cale=cale, acum=datetime(2026, 10, 23, tzinfo=timezone.utc))
    azi = {"published": "2026-10-23T08:00:00+00:00", "title": "Guvernul a aprobat bugetul rectificat",
           "entities": ["Guvernul", "România", "PSD", "PNL"]}
    assert memorie.din_memorie(azi, memorie.incarca(cale), 12) == []


def test_aceleasi_persoane_alt_subiect_nu_se_leaga(tmp_path):
    cale = str(tmp_path / "m.json")
    memorie.actualizeaza([LEGE], {}, cale=cale, acum=datetime(2026, 10, 23, tzinfo=timezone.utc))
    azi = {"published": "2026-10-23T08:00:00+00:00", "title": "Vizită oficială la Varșovia",
           "entities": ["Nicușor Dan", "pălincă"]}
    assert memorie.din_memorie(azi, memorie.incarca(cale), 12) == []


def test_vocabularul_contraventional_si_de_integritate_e_exclus():
    for fapt in ("Fostul director a fost audiat după percheziții.",
                 "Agenția a constatat conflictul de interese al primarului.",
                 "ANPC a amendat compania cu 50.000 de lei."):
        assert not memorie.eligibil(_rep("st-x", "t", fapt, ["X", "Y"])), fapt
    assert memorie.eligibil(_rep("st-ccr", "CCR a admis sesizarea",
                                 "Curtea Constituțională a admis sesizarea privind ordonanța.", ["CCR", "Guvernul"]))
