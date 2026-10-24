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
