"""Clasa D din fetch_eventphotos: fotografii oficiale de la eveniment, doar neutre (2026-10-17).

Fixture-urile copiaza metadatele REALE gasite de sonda pe Commons in aceeasi zi (Casa Alba,
kremlin.ru, Parlamentul European, Comisia Europeana), inclusiv cazurile care trebuie respinse:
un graffiti CC BY-SA „own work" gasit cautand „Putin", parada de Ziua Victoriei, o intalnire
cu „presedintele" Osetiei de Sud ocupate si licenta proprie a Multimedia Centre al PE.
"""
import datetime
import importlib.util
import io
import os

from PIL import Image

spec = importlib.util.spec_from_file_location(
    "fetch_eventphotos", os.path.join(os.path.dirname(__file__), "..", "tools", "fetch_eventphotos.py"))
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

WH = {"filename": "P20261012JB-0014.jpg", "license": "Public domain", "artist": "The White House",
      "categorii": "Executive Office of the President files|White House Flickr files uploaded by OptimusPrimeBot",
      "descriere": "President Donald J. Trump disembarks Marine One at Joint Base Andrews, Maryland on Monday, October 12, 2026",
      "data": "2026-10-12", "width": 3500, "height": 2333, "thumb": "https://u/wh.jpg", "page": "https://c/wh"}
GRAFFITI = {**WH, "filename": "FUCK PUTIN spray-painted on a sidewalk.jpg", "license": "CC BY-SA 4.0",
            "artist": "Own work", "categorii": "Graffiti", "descriere": "Putin"}
PARADA = {**WH, "filename": "2026 Moscow Victory Day Parade 03.jpg", "license": "CC BY 4.0",
          "artist": "Office of the President of Russia", "categorii": "Files from Kremlin.ru, 2026",
          "descriere": "Before the parade Putin greeted the foreign leaders"}
OSETIA = {**PARADA, "filename": "Marat Kambolov in July 2026.jpg",
          "descriere": "Meeting with Acting President of South Ossetia; Vladimir Putin and Alan Gagloyev met in the Kremlin"}
KREMLIN_OK = {**PARADA, "filename": "Vladimir Putin and Mahathir Mohamad talks.jpg",
              "descriere": "Vladimir Putin had a meeting with Prime Minister of Malaysia"}
EP_PROPRIE = {**WH, "license": "European Parliament", "artist": "European Parliament",
              "categorii": "Files from the European Parliament Multimedia Centre",
              "descriere": "Roberta METSOLA, EP President welcomes Mark CARNEY"}
EP_OK = {**EP_PROPRIE, "license": "CC BY 4.0"}
EC_OK = {**WH, "license": "CC BY 4.0", "artist": "Europäische Kommission - Audiovisueller Dienst",
         "categorii": "Admin reviewed EC-Audiovisual Center images|Media from the European Commission",
         "descriere": "Participation of Ursula von der Leyen, President of the European Commission, in the EPP Study Days"}


def test_lista_alba_e_pe_sursa_si_pe_licenta():
    assert ev.sursa_oficiala(WH)["id"] == "casa-alba"
    assert ev.sursa_oficiala(KREMLIN_OK)["id"] == "kremlin"
    assert ev.sursa_oficiala(EP_OK)["id"] == "parlamentul-european"
    assert ev.sursa_oficiala(EC_OK)["id"] == "comisia-europeana"
    assert ev.sursa_oficiala(GRAFFITI) is None, "o poza «own work» nu e sursa oficiala"
    assert ev.sursa_oficiala(EP_PROPRIE) is None, "licenta proprie a PE nu e CC BY"
    assert ev.sursa_oficiala({**WH, "license": "CC BY 4.0"}) is None, "Casa Alba se accepta doar ca PD"


def test_fara_propaganda():
    assert ev.e_neutra(WH, "Donald Trump")
    assert ev.e_neutra(KREMLIN_OK, "Vladimir Putin")
    assert ev.e_neutra(EC_OK, "Ursula von der Leyen")
    assert not ev.e_neutra(PARADA, "Vladimir Putin"), "parada"
    assert not ev.e_neutra(OSETIA, "Vladimir Putin"), "teritoriu ocupat"
    assert not ev.e_neutra({**WH, "descriere": "President Trump at a campaign rally in Ohio"}, "Donald Trump")


def test_NEGATIV_omul_din_titlu_trebuie_sa_fie_in_poza():
    assert not ev.e_neutra(WH, "Ursula von der Leyen")


def test_fereastra_si_formatul():
    pub = "2026-10-13T08:00:00+00:00"
    assert [c["filename"] for c in ev.candidati_oficiali([WH], "Donald Trump", pub)] == [WH["filename"]]
    assert ev.candidati_oficiali([{**WH, "data": "2026-10-01"}], "Donald Trump", pub) == [], "prea veche"
    assert ev.candidati_oficiali([{**WH, "width": 2333, "height": 3500}], "Donald Trump", pub) == [], "portret"
    assert ev.candidati_oficiali([{**WH, "width": 900, "height": 600}], "Donald Trump", pub) == [], "prea mica"


def test_data_din_importurile_flickr():
    assert ev._meta_date({"DateTimeOriginal": {"value": "Taken on 12 October 2026, 17:25:53"}}) == "2026-10-12"


def test_reincercare_o_data_pe_zi_trei_zile():
    a = {"published": "2026-10-15T08:00:00+00:00"}
    azi = datetime.date(2026, 10, 17)
    assert ev._poate_reincerca_oficial(None, a, azi)
    assert not ev._poate_reincerca_oficial({"incercat": "2026-10-17"}, a, azi)
    assert ev._poate_reincerca_oficial({"incercat": "2026-10-16"}, a, azi)
    assert not ev._poate_reincerca_oficial(None, a, datetime.date(2026, 10, 19))


def test_foto_oficiala_cap_coada(tmp_path, monkeypatch):
    buf = io.BytesIO()
    Image.new("RGB", (1600, 1000), (40, 40, 40)).save(buf, format="JPEG")

    class R:
        def read(self):
            return buf.getvalue()
    monkeypatch.setattr(ev.lp, "OUTDIR", str(tmp_path))
    monkeypatch.setattr(ev, "cauta", lambda q, recente=False, limita=8: [GRAFFITI, PARADA, WH])
    monkeypatch.setattr(ev.urllib.request, "urlopen", lambda *a, **k: R())
    monkeypatch.setattr(ev.htmlart, "subiect_titlu", lambda a, *r: ("donald trump", {"name": "Donald Trump"}))
    monkeypatch.setattr(ev.photojudge, "photo_fits", lambda *a, **k: True)
    a = {"title": "Donald Trump a plecat spre Ohio", "url": "u", "published": "2026-10-13T08:00:00+00:00"}
    memo = {}
    e, motiv, retea = ev.foto_oficiala(a, None, memo)
    assert motiv == "oficial_ok" and retea
    assert e["kind"] == "oficial" and e["sursa"] == "Casa Albă" and e["license"] == "Public domain"
    assert e["page"] == WH["page"] and e["data_poza"] == "2026-10-12"
    _e2, _m2, retea2 = ev.foto_oficiala({**a, "url": "u2"}, None, memo)
    assert not retea2, "acelasi om, aceeasi zi: a doua stire nu mai cere retea"
