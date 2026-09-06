"""Teste offline pentru copertile din datele evenimentului (generator.eventdata)."""
import json

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


# --------------------------------------------------------- felia 2: cutremur --
def _art_cutremur(**over):
    a = {"category": "judetean", "source": "vrancena_expres",
         "title": "Două cutremure slabe s-au produs în județul Vrancea",
         "teaser": "Seisme de 3,2 și 3,4 grade, resimțite dimineața.",
         "published": "2026-08-31T06:00:00+00:00"}
    a.update(over)
    return a


def test_poarta_cutremur_cere_categoria_si_cuvantul():
    assert eventdata._CUTREMUR.search("Două cutremure slabe și un seism resimțit")
    assert not eventdata._CUTREMUR.search("Primăria a reparat drumul")
    # categorie ne-geografica -> None chiar cu cuvantul in titlu (fara retea: gate-ul
    # taie inainte de interogare)
    assert eventdata.cutremur(_art_cutremur(category="sport")) is None


def test_parse_emsc_din_payload_real():
    payload = {"features": [
        {"properties": {"mag": 3.4, "time": "2026-08-31T02:00:00+00:00"},
         "geometry": {"coordinates": [26.79, 45.76, -98.0]}},
        {"properties": {"mag": None, "time": "2026-08-30T01:00:00+00:00"},
         "geometry": {"coordinates": [26.5, 45.6, 10.0]}}]}
    evs = eventdata.parse_emsc(payload)
    assert len(evs) == 1  # fara magnitudine -> aruncat
    assert evs[0]["mag"] == 3.4 and evs[0]["lat"] == 45.76 and evs[0]["adancime"] == 98


def test_cutremur_alege_maximul_si_face_failsafe(monkeypatch):
    payload = {"features": [
        {"properties": {"mag": 3.2, "time": "2026-08-31T01:00:00+00:00"},
         "geometry": {"coordinates": [26.8, 45.84, -84]}},
        {"properties": {"mag": 3.4, "time": "2026-08-31T02:00:00+00:00"},
         "geometry": {"coordinates": [26.79, 45.76, -98]}}]}
    monkeypatch.setattr(eventdata, "_http_get", lambda url: json.dumps(payload).encode())
    ch = eventdata.cutremur(_art_cutremur())
    assert ch and ch["mag"] == 3.4 and ch["tip"] == "cutremur" and ch["sursa"] == "EMSC"
    # retea cazuta -> None, nu exceptie
    def boom(url):
        raise OSError("emsc picat")
    monkeypatch.setattr(eventdata, "_http_get", boom)
    assert eventdata.cutremur(_art_cutremur()) is None


def test_build_html_coperta_cutremur_are_harta_si_atribuirea():
    chart = {"tip": "cutremur", "mag": 3.4, "lat": 45.76, "lon": 26.79,
             "adancime": 98, "data": "2026-08-31", "sursa": "EMSC"}
    html = htmlart.build_html(_art_cutremur(event_chart=chart))
    assert "tile.openstreetmap.org" in html
    assert "OpenStreetMap" in html and "EMSC" in html
    assert "M 3,4" in html  # virgula zecimala romaneasca


def test_fereastra_cutremur_inconjoara_publicarea():
    a = _art_cutremur(published="2026-08-31T06:00:00+00:00")
    t0, t1 = eventdata._fereastra_cutremur(a)
    assert t0 == "2026-08-29" and t1 == "2026-09-01"


# ------------------------------------------------------ tari + cutremur extern --
def test_tara_recunoaste_numele_cu_si_fara_diacritice():
    assert eventdata.tara(_art_cutremur(title="Cutremur puternic în Nepal"))["en"] == "Nepal"
    # Turcia fara sedila (forma fara diacritice) trebuie gasita la fel ca Turcia
    assert eventdata.tara(_art_cutremur(title="Cutremur în Turcia"))["ro"] == "Turcia"
    # granita de cuvant + cel mai lung nume bate: Nigeria nu trebuie sa iasa Niger
    assert eventdata.tara(_art_cutremur(title="Inundații în Nigeria"))["en"] == "Nigeria"
    assert eventdata.tara(_art_cutremur(title="Cutremur în Niger"))["en"] == "Niger"


def test_cutremur_extern_foloseste_cutia_tarii(monkeypatch):
    vazut = {}

    def fake_get(url):
        vazut["url"] = url
        return json.dumps({"features": [
            {"properties": {"mag": 4.1, "time": "2026-09-01T00:00:00+00:00"},
             "geometry": {"coordinates": [84.0, 27.0, 10]}},
            {"properties": {"mag": 5.2, "time": "2026-08-31T02:52:00+00:00"},
             "geometry": {"coordinates": [85.515, 28.271, 0]}}]}).encode()
    monkeypatch.setattr(eventdata, "_http_get", fake_get)
    a = {"category": "extern", "source": "stirileprotv", "published": "2026-09-02T10:00:00+00:00",
         "title": "Cutremurul de 5,2 care a declanșat viitura în Nepal", "teaser": ""}
    ch = eventdata.cutremur(a)
    assert ch and ch["mag"] == 5.2 and ch["loc"] == "Nepal"
    assert "minlatitude=25.67" in vazut["url"] and "minmagnitude=4.0" in vazut["url"]


def test_template_cutremur_afiseaza_tara_din_chart():
    chart = {"tip": "cutremur", "mag": 5.2, "lat": 28.27, "lon": 85.51,
             "adancime": 10, "data": "2026-08-31", "sursa": "EMSC", "loc": "Nepal"}
    a = {"category": "extern", "source": "stirileprotv", "title": "Viitură în Nepal",
         "teaser": "", "published": "2026-09-02"}
    html = htmlart.build_html(a, )
    assert "NEPAL" not in html  # fara chart ramane template-ul clasic
    html2 = htmlart.build_html({**a, "event_chart": chart})
    assert "Nepal" in html2 and "M 5,2" in html2
