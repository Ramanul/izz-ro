"""Teste offline pentru copertile din datele evenimentului (generator.eventdata)."""
from generator import eventdata, htmlart

_BY_NAME = {"sibiu": [{"label": "Sibiu", "judet": "Județul Sibiu", "qid": "Q7747",
                       "pop": 150000, "img": "Sibiu.jpg"}]}


def _art(**over):
    a = {"category": "local", "source": "pl_sibiu_sibiu",
         "title": "Vreme caldă în Sibiu, cu averse la munte", "teaser": ""}
    a.update(over)
    return a


def test_gate_cere_categorie_cuvant_si_loc_rezolvat():
    # sursa de primarie: judetul vine din slug (`pl_...`)
    loc = eventdata.gate(_art(), _BY_NAME)
    assert loc and loc["qid"] == "Q7747" and loc["display"] == "Sibiu"
    # ziar judetean declarat in config.SOURCES: locul vine din TITLU (lantul din geo.py)
    loc2 = eventdata.gate(_art(source="turnulsfatului",
                               title="Județul Sibiu va avea parte de vreme caldă"), _BY_NAME)
    assert loc2 and loc2["qid"] == "Q7747"
    # fara cuvinte de vreme -> None
    assert eventdata.gate(_art(title="Primăria a reparat drumul județean"), _BY_NAME) is None
    # categorie ne-geografica -> None, chiar cu cuvinte de vreme
    assert eventdata.gate(_art(category="sport"), _BY_NAME) is None
    # sursa fara judet (nationala, fara slug de primarie) -> None
    assert eventdata.gate(_art(source="digi24"), _BY_NAME) is None


def test_parse_open_meteo():
    payload = {"daily": {
        "time": ["2026-09-05", "2026-09-06"],
        "temperature_2m_max": [31.4, 24.0],
        "temperature_2m_min": [16.2, 13.0]}}
    zile = eventdata.parse_open_meteo(payload)
    assert len(zile) == 2
    assert zile[0] == {"zi": "05", "lit": "S", "max": 31, "min": 16}  # sâmbătă
    assert zile[1]["lit"] == "D" and zile[1]["max"] == 24


def test_prognoza_fail_safe_la_retea_picata(monkeypatch):
    def boom(url):
        raise OSError("open-meteo indisponibil")
    monkeypatch.setattr(eventdata, "_http_get", boom)
    assert eventdata.prognoza({"display": "Sibiu"}, 45.79, 24.12) is None


def test_coords_cache_hit_fara_retea(tmp_path):
    p = tmp_path / "coords.json"
    p.write_text('{"Q7747": [44.43, 26.1]}', encoding="utf-8")
    cache = eventdata._load_coords(str(p))
    assert cache == {"Q7747": [44.43, 26.1]}
    assert eventdata.coords_for("Q7747", cache, str(p)) == (44.43, 26.1)


def test_build_html_coperta_meteo_contine_datele():
    chart = {"tip": "meteo", "localitate": "Sibiu", "sursa": "open-meteo.com",
             "zile": [{"zi": "05", "lit": "S", "max": 31, "min": 16},
                      {"zi": "06", "lit": "D", "max": 24, "min": 13}]}
    html = htmlart.build_html(_art(event_chart=chart))
    assert "Sibiu" in html and "Prognoză" in html and "open-meteo.com" in html
    assert "31°" in html and "13°" in html


def test_build_html_fara_chart_ramane_neschimbat():
    plain = htmlart.build_html(_art(title="Primăria Sibiului a aprobat bugetul"))
    assert "open-meteo.com" not in plain
    # eticheta din template-urile clasice apare, subtitlul nu e prognoza
    assert "eticheta" in plain
