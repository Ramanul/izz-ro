"""Teste offline pentru partile pure ale fetcher-ului de lead-photos."""
import importlib.util
import json
import os

from PIL import Image

from generator import localities, render

spec = importlib.util.spec_from_file_location(
    "fetch_leadphotos", os.path.join(os.path.dirname(__file__), "..", "tools", "fetch_leadphotos.py"))
lp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lp)


def test_public_domain_gate_excludes_cc_by():
    for ok in ("CC0", "cc-zero", "Public domain", "PD", "PD-old"):
        assert lp.is_public_domain(ok), ok
    for bad in ("CC BY 4.0", "CC BY-SA 4.0", "Copyrighted", "Fair use", "", None):
        assert not lp.is_public_domain(bad), bad


def test_landscape_gate():
    assert lp.is_landscape(1200, 800)      # 1.5 -> landscape
    assert lp.is_landscape(1000, 800)      # 1.25 -> landscape (>=1.2)
    assert not lp.is_landscape(800, 800)   # patrat
    assert not lp.is_landscape(600, 900)   # portret
    assert not lp.is_landscape(0, 0)


def test_qualifies_accepts_landscape_and_vertical_with_compatible_license():
    assert lp.qualifies({"width": 1600, "height": 900, "license": "Public domain"})
    assert lp.qualifies({"width": 1600, "height": 900, "license": "CC BY 4.0"})       # CC BY permis
    assert lp.qualifies({"width": 800, "height": 1200, "license": "CC0"})             # portret vertical permis
    assert lp.qualifies({"width": 800, "height": 1200, "license": "CC BY-SA 4.0"})    # portret CC BY-SA permis
    assert not lp.qualifies({"width": 1600, "height": 900, "license": "Copyrighted"}) # licenta interzisa
    assert not lp.qualifies({"width": 200, "height": 1000, "license": "CC0"})         # raport extrem (<0.5)
    assert not lp.qualifies({"width": 0, "height": 0, "license": "CC0"})


def test_crop_to_with_focus_y_centers_on_face():
    # Imagine verticala 800x1600
    src = Image.new("RGB", (800, 1600), (255, 255, 255))
    # Decupaj la 960x504 cu focalizare pe treimea superioara (focus_y=0.25)
    out = lp.crop_to(src, 960, 504, focus_y=0.25)
    assert out.size == (960, 504)


def test_crop_to_produces_exact_dims_without_distortion():
    src = Image.new("RGB", (2000, 1000), (10, 20, 30))   # 2:1
    for w, h in [(1200, 630), (960, 504)]:
        out = lp.crop_to(src, w, h)
        assert out.size == (w, h)
    # sursa mai mica decat tinta -> tot produce exact dimensiunile (upscale, fara crash)
    small = Image.new("RGB", (400, 300), (0, 0, 0))
    assert lp.crop_to(small, 1200, 630).size == (1200, 630)


def test_save_renditions_writes_valid_cover_art_webp(tmp_path, monkeypatch):
    import io
    monkeypatch.setattr(lp, "OUTDIR", str(tmp_path))
    buf = io.BytesIO()
    Image.new("RGB", (1600, 1000), (30, 90, 160)).save(buf, format="JPEG")
    rend = lp._save_renditions(buf.getvalue(), "test-entity")
    assert rend == {"cover": "leads/test-entity.c.jpg", "art": "leads/test-entity.jpg",
                    "webp": "leads/test-entity.webp"}
    assert Image.open(tmp_path / "test-entity.c.jpg").size == (lp.COVER_W, lp.COVER_H)
    assert Image.open(tmp_path / "test-entity.jpg").size == (lp.ART_W, lp.ART_H)
    assert (tmp_path / "test-entity.webp").exists()


def test_is_tragic_or_negative_detects_tragedies_and_crimes():
    garda = localities.is_tragic_or_negative
    assert garda("Accident grav cu două victime pe DN2")
    assert garda("Bărbat arestat după un omor în localitate")
    assert garda("Percheziții DNA la sediul primăriei")
    assert garda("Incendiu puternic izbucnit la o gospodărie")
    assert not garda("Primăria modernizează parcul central")
    assert not garda("Investiții în infrastructura rutieră și apă")


def test_garda_negativa_merge_si_fara_diacritice():
    garda = localities.is_tragic_or_negative
    assert garda("Barbat retinut, dus in catuse la Bacau")
    assert garda("Doi morți după percheziția din Slobozia")
    assert garda("Bărbat reţinut cu cedilă veche")
    assert not garda("Dna primar a inaugurat parcul")
    assert not garda("Clădire amortizată contabil, incriminare respinsă")


def _poza_locala() -> dict:
    return {"kind": "locality", "art": "a.jpg", "cover": "c.jpg"}


def test_randarea_scoate_poza_de_localitate_din_cache_de_pe_stirea_tragica():
    a = {"title": "Accident mortal în centrul comunei", "category": "local"}
    assert render._lead_pentru(a, {"x": _poza_locala()}, "x") is None


def test_randarea_pastreaza_poza_de_localitate_pe_stirea_obisnuita():
    a = {"title": "Primăria modernizează parcul central", "category": "local"}
    assert render._lead_pentru(a, {"x": _poza_locala()}, "x") == _poza_locala()


def test_garda_de_randare_nu_atinge_portretul_din_titlu():
    a = {"title": "Ministrul comentează accidentul de pe DN2", "category": "politica"}
    portret = {"kind": "entity", "art": "a.jpg", "cover": "c.jpg"}
    assert render._lead_pentru(a, {"x": portret}, "x") == portret


def test_focus_y_foloseste_incadrarea_portretului_real(monkeypatch, tmp_path):
    portrete = tmp_path / "portraits.json"
    portrete.write_text(json.dumps({"ion tiriac": {"img": "portraits/ion.jpg"},
                                    "ana sus": {"img": "portraits/ana.jpg"}}), encoding="utf-8")
    monkeypatch.setattr(lp.render, "PORTRAITS_JSON", str(portrete))
    monkeypatch.setattr(lp.htmlart, "incadrare_portrete", lambda: {
        "portraits/ion.jpg": {"poz": "50% 29%"}, "portraits/ana.jpg": {"poz": "50% 3%"}})
    vertical = {"width": 800, "height": 1200}
    assert lp._get_focus_y("Ion Țiriac", vertical) == 0.29
    assert lp._get_focus_y("Ana Sus", vertical) == 0.15   # plafonat, nu taie capul
    assert lp._get_focus_y("Nimeni Cunoscut", vertical) == 0.28
    assert lp._get_focus_y("Ion Țiriac", {"width": 1600, "height": 900}) is None


def test_lead_for_locality_rejects_tragic_news(monkeypatch):
    art_tragic = {"title": "Accident mortal pe șoseaua de centură", "source": "pl_cluj_floresti", "category": "local"}
    hit, motiv = lp.lead_for_locality(art_tragic, {})
    assert hit is None
    assert motiv == "loc_exclus_tematic"


def test_lead_for_locality_accepts_clean_news(monkeypatch):
    art_curat = {"title": "Inaugurarea noului centru cultural", "source": "pl_cluj_floresti", "category": "local"}
    rec = {"qid": "Q42", "display": "Florești", "img": "Floresti.jpg"}
    monkeypatch.setattr(lp.localities, "locality_for_article", lambda a, by: rec)
    monkeypatch.setattr(lp, "commons_lead_info", lambda f: {"thumb": "http://x", "width": 1400, "height": 900, "license": "CC0", "artist": "A", "page": "p"})
    monkeypatch.setattr(lp.localities, "usable", lambda i: True)
    monkeypatch.setattr(lp.urllib.request, "urlopen", lambda *a, **k: type("Resp", (), {"read": lambda self: b"fake-jpg-content-over-3000-bytes" * 200})())
    monkeypatch.setattr(lp, "_save_renditions", lambda data, slug, **kw: {"art": "a", "cover": "c", "webp": "w"})
    hit, motiv = lp.lead_for_locality(art_curat, {})
    assert motiv == "loc_ok"
    assert hit["name"] == "Florești"
