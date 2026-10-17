"""Ruta de localitate din fetch_leadphotos (2026-10-17), offline.

Pazeste:
  1. poarta e `localities.usable` (CC BY permis, NC/ND respinse) — render.py tine CC BY doar pe
     pagina de articol (#205), deci bariera PD-only ramasese mai stricta decat politica;
  2. poza unei localitati se refoloseste FARA retea si FARA plafon (memo per QID);
  3. fiecare miss isi pastreaza motivul;
  4. curatarea cache-ului scoate articolele expirate, dar pastreaza memoria per localitate.
"""
import importlib.util
import io
import json
import os

from PIL import Image

spec = importlib.util.spec_from_file_location(
    "fetch_leadphotos", os.path.join(os.path.dirname(__file__), "..", "tools", "fetch_leadphotos.py"))
lp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lp)

REC = {"qid": "Q42", "img": "Floresti.jpg", "display": "Florești"}
ART = {"category": "local", "source": "pl_cluj_floresti", "title": "Ședință", "url": "https://x/1"}


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (1600, 1000), (20, 90, 160)).save(buf, format="JPEG")
    return buf.getvalue()


class _Resp:
    def __init__(self, data):
        self._d = data

    def read(self):
        return self._d


def _retea(monkeypatch, info, apeluri):
    def fake_info(f):
        apeluri.append(f)
        return info
    monkeypatch.setattr(lp, "commons_lead_info", fake_info)
    monkeypatch.setattr(lp.urllib.request, "urlopen", lambda *a, **k: _Resp(_jpeg()))
    monkeypatch.setattr(lp.localities, "locality_for_article", lambda a, by: REC)


def _info(lic, w=1600, h=1000):
    return {"thumb": "https://upload/x.jpg", "width": w, "height": h, "license": lic,
            "artist": "Autor", "page": "https://commons.wikimedia.org/wiki/File:Floresti.jpg"}


def test_ruta_localitatii_accepta_cc_by_sa(tmp_path, monkeypatch):
    monkeypatch.setattr(lp, "OUTDIR", str(tmp_path))
    _retea(monkeypatch, _info("CC BY-SA 3.0 ro"), [])
    hit, motiv = lp.lead_for_locality(ART, {}, {})
    assert motiv == "loc_ok" and hit["license"] == "CC BY-SA 3.0 ro"
    assert hit["kind"] == "locality" and hit["qid"] == "Q42" and hit["art"] == "leads/loc-Q42.jpg"


def test_NEGATIV_nc_si_nd_raman_respinse(tmp_path, monkeypatch):
    monkeypatch.setattr(lp, "OUTDIR", str(tmp_path))
    for lic in ("CC BY-NC 4.0", "CC BY-ND 4.0", "Copyrighted", ""):
        _retea(monkeypatch, _info(lic), [])
        hit, motiv = lp.lead_for_locality(ART, {}, {})
        assert hit is None and motiv == "loc_licenta", lic


def test_NEGATIV_poza_mica_sau_portret_are_motivul_ei(tmp_path, monkeypatch):
    monkeypatch.setattr(lp, "OUTDIR", str(tmp_path))
    _retea(monkeypatch, _info("CC0", w=800, h=1200), [])
    assert lp.lead_for_locality(ART, {}, {}) == (None, "loc_dimensiune_sau_format")


def test_a_doua_stire_din_aceeasi_localitate_nu_mai_cere_retea(tmp_path, monkeypatch):
    monkeypatch.setattr(lp, "OUTDIR", str(tmp_path))
    apeluri = []
    _retea(monkeypatch, _info("CC BY 4.0"), apeluri)
    memo = {}
    h1, _ = lp.lead_for_locality(ART, {}, memo)
    h2, m2 = lp.lead_for_locality({**ART, "url": "https://x/2"}, {}, memo)
    assert len(apeluri) == 1 and m2 == "loc_refolosit" and h2["art"] == h1["art"]


def test_index_localitati_refoloseste_doar_hiturile_cu_licenta_acceptata():
    cache = {
        "a": {"art": "leads/loc-Q1.jpg", "license": "CC BY-SA 4.0", "kind": "locality"},
        "b": {"art": "leads/loc-Q2.jpg", "license": "CC BY-NC 4.0", "kind": "locality"},
        "c": {"art": "leads/x.jpg", "license": "CC0", "name": "Ion Pop"},
        "d": {"miss": True, "v": 2},
    }
    assert set(lp.index_localitati(cache)) == {"Q1"}


def test_main_refoloseste_fara_plafon_si_scrie_motivul(tmp_path, monkeypatch):
    """Cu plafonul la ZERO, stirea din localitatea cunoscuta tot primeste poza (fara retea),
    iar cealalta ramane neinterogata. Apoi, cu plafon, miss-ul isi scrie motivele."""
    cache_p = tmp_path / "leadphotos.json"
    vechi = {"vechi": {"art": "leads/loc-Q42.jpg", "cover": "leads/loc-Q42.c.jpg",
                       "webp": "leads/loc-Q42.webp", "license": "CC BY 4.0", "artist": "A",
                       "page": "p", "name": "Florești", "kind": "locality"}}
    cache_p.write_text(json.dumps(vechi), encoding="utf-8")
    a1 = {**ART, "url": "https://x/a1", "title": "T1"}
    a2 = {"category": "politic", "source": "digi24", "url": "https://x/a2", "title": "T2",
          "entities": ["Ion Popescu"]}
    monkeypatch.setattr(lp, "CACHE", str(cache_p))
    monkeypatch.setattr(lp, "OUTDIR", str(tmp_path))
    monkeypatch.setattr(lp.state, "load", lambda: [a1, a2])
    monkeypatch.setattr(lp, "get_provider", lambda: None)
    monkeypatch.setattr(lp.localities, "load_dataset", lambda: {"x": 1})
    monkeypatch.setattr(lp.localities, "locality_for_article",
                        lambda a, by: REC if a is a1 else None)
    monkeypatch.setattr(lp.localities, "eligible", lambda a: a is a1)
    monkeypatch.setattr(lp, "commons_lead_info", lambda f: (_ for _ in ()).throw(AssertionError("retea!")))
    monkeypatch.setattr(lp, "MAX_LOOKUPS", 0)
    monkeypatch.setattr(lp, "MIN_ARTICOLE_CURATARE", 10 ** 6)
    assert lp.main() == 0
    out = json.loads(cache_p.read_text(encoding="utf-8"))
    aid1, aid2 = lp.htmlart.art_id(a1), lp.htmlart.art_id(a2)
    assert out[aid1]["art"] == "leads/loc-Q42.jpg" and out[aid1]["name"] == "Florești"
    assert aid2 not in out, "plafonul zero trebuia sa lase articolul neinterogat"

    monkeypatch.setattr(lp, "MAX_LOOKUPS", 5)
    monkeypatch.setattr(lp, "lead_for_article", lambda a, p: (None, "ent_fara_p18"))
    monkeypatch.setattr(lp.time, "sleep", lambda s: None)
    assert lp.main() == 0
    out = json.loads(cache_p.read_text(encoding="utf-8"))
    assert out[aid2] == {"miss": True, "v": lp.MISS_VERSION,
                         "motiv_loc": "loc_neeligibil", "motiv_ent": "ent_fara_p18"}


def test_curatarea_pastreaza_memoria_localitatilor():
    cache = {
        "viu": {"miss": True, "v": 3},
        "mort_miss": {"miss": True, "v": 2},
        "mort_entitate": {"art": "leads/x.jpg", "license": "CC0", "name": "Ion Pop"},
        "mort_localitate": {"art": "leads/loc-Q1.jpg", "license": "CC BY 4.0", "kind": "locality"},
    }
    assert lp.curata_cache(cache, {"viu"}) == 2
    assert set(cache) == {"viu", "mort_localitate"}
