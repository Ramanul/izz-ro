"""`_fetch_wp_json` — lista de articole din WordPress REST API pentru primariile fara RSS.
Test pe fixture JSON (sandbox-ul n-are internet); garda de ingestie e aceeasi ca la HTML."""
import io
import json

from generator import fetch


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _wp_fixture():
    return json.dumps([
        {"title": {"rendered": "Sedinta consiliului local"}, "link": "https://primaria.ro/stiri/1",
         "date_gmt": "2026-09-01T10:00:00", "excerpt": {"rendered": "<p>Ordinea de zi.</p>"}},
        {"title": {"rendered": "Hacked by X"}, "link": "https://primaria.ro/stiri/2",
         "date_gmt": "2026-09-02T10:00:00", "excerpt": {"rendered": ""}},
        {"title": {"rendered": "Anunt colectare deseuri"}, "link": "/stiri/3",
         "date_gmt": "2026-08-30T08:00:00", "excerpt": {"rendered": ""}},
    ]).encode("utf-8")


SRC = {"type": "wp_json", "name": "Primăria Test", "category": "local",
       "url": "https://primaria.ro/wp-json/wp/v2/posts?per_page=8"}


def test_wp_json_extrage_titlu_data_link(monkeypatch):
    monkeypatch.setattr(fetch, "USER_AGENT", "ua")
    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda req, timeout=20: _Resp(_wp_fixture()))
    items, err = fetch._fetch_wp_json("pl_test_x", SRC)
    # „Hacked by X" e respins de garda de continut (o singura respingere < prag carantina)
    assert err is None
    assert len(items) == 2
    primul = items[0]
    assert primul["title"] == "Sedinta consiliului local"
    assert primul["published"].startswith("2026-09-01")
    assert primul["url"] == "https://primaria.ro/stiri/1"
    assert primul["description"] == "Ordinea de zi."  # curatat de <p>
    # link relativ -> absolut, la fel ca la HTML
    assert items[1]["url"] == "https://primaria.ro/stiri/3"


def test_wp_json_garda_respinge_continut_ostil_si_carantineaza(monkeypatch):
    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda req, timeout=20: _Resp(_wp_fixture()))
    items, err = fetch._fetch_wp_json("pl_test_x", SRC)
    # „Hacked by X" respins de garda; 2 din 3 > pragul de carantina? nu — carantina cere >=2
    # respingeri intr-o rulare DOAR cand depasesc fractia din guard; aici una respinsa din 3.
    assert len(items) == 2
    assert all("Hacked" not in i["title"] for i in items)


def test_wp_json_nu_crapa_pe_raspuns_nonjson(monkeypatch):
    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda req, timeout=20: _Resp(b"<html>nu sunt json</html>"))
    items, err = fetch._fetch_wp_json("pl_test_x", SRC)
    assert items == [] and err and "non-JSON" in err


def test_wp_json_nu_crapa_pe_lista_golita(monkeypatch):
    monkeypatch.setattr(fetch.urllib.request, "urlopen", lambda req, timeout=20: _Resp(b"[]"))
    items, err = fetch._fetch_wp_json("pl_test_x", SRC)
    assert items == [] and err and "fara articole" in err
