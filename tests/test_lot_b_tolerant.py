"""Un obiect JSON stricat nu mai amână tot lotul B, iar fiecare pierdere are un motiv numărat.

DE CE EXISTA (2026-10-24). Pe rulările CI din 22–23.10, „Amânate (buget NEepuizat — altă
cauză)" a fost 87–112 din 415–486 de iteme noi, cu bugetul AI nefolosit (27–36 din 40).
`process_batch` parsa răspunsul strict: un singur obiect stricat pierdea toate cele 10
articole ale lotului, fără nicio urmă în log. Sinteza dialectică primise deja parsare
tolerantă (#512) după o liniuță rătăcită măsurată pe Gemini Flash Lite; calea B rămăsese
pe parserul vechi. Contoarele fac cauza vizibilă în `build.json` → `model_b`.
"""
import json

import pytest

from generator import process


class _Raw:
    name = "fake"

    def __init__(self, raw):
        self._raw = raw

    def complete(self, system, user):
        if isinstance(self._raw, Exception):
            raise self._raw
        return self._raw


def _item(i):
    return {"url": f"https://ziar.ro/{i}", "original_link": f"https://ziar.ro/{i}",
            "source": "ziar", "source_name": "Ziar", "category": "general", "source_lang": "ro",
            "original_title": f"Consiliul local {i} a aprobat bugetul pentru drumuri",
            "description": f"Consiliul local {i} a aprobat bugetul pentru drumuri județene."}


def _obj(i):
    return {"id": i, "title": f"Consiliul local {i} a aprobat bugetul pentru drumuri",
            "teaser": f"Consiliul local {i} a aprobat bugetul pentru drumuri județene.",
            "category": "general", "entities": [], "icon": None}


@pytest.fixture(autouse=True)
def _curat():
    process.reset_stats_b()
    yield
    process.reset_stats_b()


def test_un_obiect_stricat_nu_mai_ia_lotul_cu_el():
    obiecte = [json.dumps(_obj(i), ensure_ascii=False) for i in range(10)]
    obiecte[4] = obiecte[4].replace('"teaser"', '- "teaser"')        # liniuța rătăcită
    obiecte[7] = obiecte[7][:-1] + ',}'                               # virgulă înainte de }
    obiecte[9] = '{"id": 9, "title": "rupt'                           # trunchiat de tot
    raw = "[" + ",\n".join(obiecte) + "]"
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)                       # premisa: parserul strict pierde tot lotul
    out = process.process_batch([_item(i) for i in range(10)], _Raw(raw))
    assert sorted(int(a["url"].rsplit("/", 1)[1]) for a in out) == list(range(9))
    st = process.stats_b()
    assert st["loturi_reparate"] == 1 and st["nemapate"] == 1 and st["publicate"] == 9


def test_lotul_pierdut_de_tot_se_numara_pe_cauza():
    process.process_batch([_item(i) for i in range(3)], _Raw("nu e json deloc"))
    process.process_batch([_item(i) for i in range(2)], _Raw(TimeoutError("apel picat")))
    st = process.stats_b()
    assert st == {"lot_esuat_json": 3, "lot_esuat_apel": 2}


def test_obiect_fara_rezumat_si_raspuns_valid_numarate_separat():
    raw = json.dumps([_obj(0), {"id": 1, "title": "Doar titlu", "teaser": ""}],
                     ensure_ascii=False)
    out = process.process_batch([_item(0), _item(1)], _Raw(raw))
    assert len(out) == 1
    assert process.stats_b() == {"fara_titlu_sau_rezumat": 1, "publicate": 1}


def test_id_duplicat_arunca_ambele_obiecte_si_id_strain_se_numara():
    """„Ultimul câștigă" ar da unei știri titlul scris pentru vecina ei (Argon R7)."""
    raw = json.dumps([_obj(0), _obj(1), {**_obj(1), "title": "Alt titlu pentru același id"},
                      {**_obj(2), "id": 2.0}, {**_obj(3), "id": " 3 "}, _obj(17)],
                     ensure_ascii=False)
    out = process.process_batch([_item(i) for i in range(4)], _Raw(raw))
    assert sorted(int(a["url"].rsplit("/", 1)[1]) for a in out) == [0, 2, 3]
    st = process.stats_b()
    assert st["id_duplicat"] == 1 and st["id_strain"] == 1 and st["nemapate"] == 1


def test_enter_literal_intr_un_sir_nu_mai_pierde_lotul():
    raw = json.dumps([_obj(0), _obj(1)], ensure_ascii=False).replace(
        "drumuri județene.", "drumuri\njudețene.", 1)
    out = process.process_batch([_item(0), _item(1)], _Raw(raw))
    assert len(out) == 2 and "loturi_reparate" not in process.stats_b()


def test_reparatia_liniutei_atinge_doar_chei():
    def repara(text):
        for rx, rep in process._REPARATII_JSON:
            text = rx.sub(rep, text)
        return text
    assert repara('{"id": 1, - "teaser": "x"}') == '{"id": 1, "teaser": "x"}'
    # ghilimea neescapată dintr-un citat: fragmentul e stricat, dar textul nu se rescrie
    citat = '{"id": 1, "teaser": "A declarat, - "Nu plec" și a ieșit"}'
    assert repara(citat) == citat


def test_amanarile_se_despart_pe_locul_in_care_au_ramas(monkeypatch):
    from generator import main
    monkeypatch.setattr(main, "itemele_fara_substanta", lambda items: [items[4]])
    main._COMPOZITIE.clear()
    main._COMPOZITIE.update(sinteza={"u0", "u1"}, b={"u2", "u3"}, oficial={"u5"})
    iteme = [{"url": f"u{i}"} for i in range(7)]
    out = main.motive_amanare(iteme, handled={"u1", "u3"})
    # u4 e respins definitiv (nu e amânat); u6 n-a fost repartizat nicăieri
    assert out == {"sinteza_amanata": 1, "b_neiesit": 1, "oficial_sarit": 1, "nerepartizat": 1}
    assert sum(out.values()) == main.numara_amanate(iteme, {"u1", "u3"})
