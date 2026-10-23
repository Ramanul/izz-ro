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


def test_memoria_apare_doar_dincolo_de_fereastra_si_pe_aceleasi_entitati(tmp_path):
    cale = str(tmp_path / "m.json")
    memorie.actualizeaza([LEGE], {}, cale=cale, acum=datetime(2026, 10, 23, tzinfo=timezone.utc))
    reg = memorie.incarca(cale)
    azi = {"story_id": "st-nou", "published": "2026-10-23T08:00:00+00:00",
           "entities": ["Parlamentul", "pălincă", "Guvernul"]}
    gasite = memorie.din_memorie(azi, reg, ttl_zile=12)
    assert [e["story"] for e in gasite] == ["st-1"]
    assert memorie.din_memorie(dict(azi, entities=["Guvernul"]), reg, 12) == []          # o singură entitate
    assert memorie.din_memorie(dict(azi, published="2026-06-15T08:00:00+00:00"), reg, 12) == []  # încă în fereastră
