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


def _claims(human=True, position=True, img="Foto.jpg", types=None):
    c = {}
    ids = list(types or [])
    if human:
        ids.append("Q5")
    if ids:
        c["P31"] = [{"mainsnak": {"datavalue": {"value": {"id": q}}}} for q in ids]
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


def test_entity_types_collects_all_p31():
    c = _claims(human=False, position=False, types=["Q515", "Q1549591"])
    assert fp.entity_types(c) == {"Q515", "Q1549591"}
    assert fp.entity_types({}) == set()


def test_photo_worthy_covers_people_and_safe_entities():
    # persoana publica -> ca inainte
    assert fp.is_photo_worthy(_claims())
    # entitate din SAFE_TYPES (oras), notorie -> acceptata
    assert fp.is_photo_worthy(_claims(human=False, position=False, types=["Q515"]), sitelinks=30)
    # aceeasi entitate, dar obscura (putine sitelinks) -> respinsa (evita omonime)
    assert not fp.is_photo_worthy(_claims(human=False, position=False, types=["Q515"]), sitelinks=3)
    # tip in AFARA whitelist-ului (ex. concept abstract), oricat de notoriu -> respins
    assert not fp.is_photo_worthy(_claims(human=False, position=False, types=["Q12345678"]), sitelinks=99)
    # persoana obscura fara functie ramane respinsa (regresie is_public_figure)
    assert not fp.is_photo_worthy(_claims(position=False), sitelinks=5)


def test_sports_teams_are_excluded_to_avoid_misleading_celebration_photos():
    # cluburi/echipe sportive: P18 e frecvent o poza de sarbatoare -> inselatoare pe
    # stirile "Y a batut X". Respinse chiar notorii (jucatorii raman eligibili ca oameni).
    for team_type in ("Q476028", "Q847017", "Q12973014"):  # club fotbal / club sportiv / echipa
        assert team_type not in fp.SAFE_TYPES, team_type
        assert not fp.is_photo_worthy(
            _claims(human=False, position=False, types=[team_type]), sitelinks=99), team_type


def test_portrait_file_extracts_p18():
    assert fp.portrait_file(_claims(img="X.jpg")) == "X.jpg"
    assert fp.portrait_file(_claims(img=None)) is None


def test_clean_html_strips_credit_markup():
    assert fp.clean_html('<a href="x">Foto</a> de <b>Ion</b>') == "Foto de Ion"


def test_slugish():
    assert fp.slugish("Nicușor Dan") == "nicusor-dan"
