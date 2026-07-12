"""Teste offline pentru partile pure ale pilotului de portrete (tools/fetch_portraits)."""
import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "fetch_portraits", os.path.join(os.path.dirname(__file__), "..", "tools", "fetch_portraits.py"))
fp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fp)


def test_norm_diacritics_insensitive():
    assert fp.norm("Nicuşor  Dan") == fp.norm("nicusor dan")


def test_license_gate_accepts_free_rejects_rest():
    for ok in ("CC BY-SA 4.0", "CC0", "Public domain", "Attribution"):
        assert fp.license_ok(ok), ok
    for bad in ("Fair use", "Copyrighted", "", None):
        assert not fp.license_ok(bad), bad


def _claims(human=True, position=True, img="Foto.jpg"):
    c = {}
    if human:
        c["P31"] = [{"mainsnak": {"datavalue": {"value": {"id": "Q5"}}}}]
    if position:
        c["P39"] = [{"mainsnak": {"datavalue": {"value": {"id": "Q30185"}}}}]
    if img:
        c["P18"] = [{"mainsnak": {"datavalue": {"value": img}}}]
    return c


def test_public_figure_requires_human_AND_position_or_fame():
    assert fp.is_public_figure(_claims())
    assert not fp.is_public_figure(_claims(human=False))                 # organizatie omonima
    assert not fp.is_public_figure(_claims(position=False))              # om obscur, fara functie
    assert fp.is_public_figure(_claims(position=False), sitelinks=20)    # sportiv/artist celebru
    assert not fp.is_public_figure(_claims(position=False), sitelinks=5) # omonim putin cunoscut
    assert not fp.is_public_figure(_claims(human=False), sitelinks=99)   # faima nu ocoleste testul de om


def test_portrait_file_extracts_p18():
    assert fp.portrait_file(_claims(img="X.jpg")) == "X.jpg"
    assert fp.portrait_file(_claims(img=None)) is None


def test_clean_html_strips_credit_markup():
    assert fp.clean_html('<a href="x">Foto</a> de <b>Ion</b>') == "Foto de Ion"


def test_slugish():
    assert fp.slugish("Nicușor Dan") == "nicusor-dan"
