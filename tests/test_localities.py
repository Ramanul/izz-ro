"""Teste offline pentru rezolvarea localitatii unei stiri locale (generator/localities.py)."""
import pytest

from generator import localities as L


# --- parse_source_slug -------------------------------------------------------------

@pytest.mark.parametrize("slug,expected", [
    ("pl_vrancea_municipiul_focsani", ("vrancea", "focsani")),
    ("pl_alba_oras_teius", ("alba", "teius")),
    ("pl_alba_orasul_teius", ("alba", "teius")),
    ("pl_bacau_hemeius", ("bacau", "hemeius")),                    # comuna, fara prefix
    ("pl_bacau_comuna_hemeius", ("bacau", "hemeius")),
    ("pl_bistrita_nasaud_municipiul_bistrita", ("bistrita nasaud", "bistrita")),
    ("pl_caras_severin_oras_oravita", ("caras severin", "oravita")),
    ("pl_maramures_oras_valea_lui_mihai", ("maramures", "valea lui mihai")),
])
def test_parse_source_slug(slug, expected):
    assert L.parse_source_slug(slug) == expected


def test_parse_source_slug_multi_word_judet_without_prefix():
    """Judet compus + comuna, fara prefix administrativ care sa marcheze granita."""
    assert L.parse_source_slug("pl_satu_mare_halmeu") == ("satu mare", "halmeu")


def test_parse_source_slug_simple_judet_two_word_commune():
    """Regresie: judetul simplu nu trebuie sa inghita primul cuvant al comunei."""
    assert L.parse_source_slug("pl_prahova_valea_calugareasca") == ("prahova", "valea calugareasca")


@pytest.mark.parametrize("slug", ["", None, "digi24", "pl_", "pl_alba", "rss_alba_teius"])
def test_parse_source_slug_rejects_non_primarie(slug):
    assert L.parse_source_slug(slug) is None


def test_orastioara_is_not_treated_as_oras():
    """'ORASTIOARA DE SUS' contine 'ORAS' — potrivirea e pe cuvant intreg, nu substring."""
    assert L.parse_source_slug("pl_hunedoara_orastioara_de_sus") == ("hunedoara", "orastioara de sus")


# --- match: potrivirea de judet ----------------------------------------------------

DATASET = {
    "zarnesti": [
        {"qid": "Q1", "label": "Zărnești", "judet": "Județul Brașov", "img": "", "pop": 23000},
        {"qid": "Q2", "label": "Zărnești", "judet": "Județul Buzău",
         "img": "Crucea Comisoaiei.jpg", "pop": 2000},
    ],
    "focsani": [
        {"qid": "Q192265", "label": "Focșani", "judet": "Județul Vrancea",
         "img": "Focsani.jpg", "pop": 79315},
    ],
}


def test_match_never_falls_back_to_another_judet():
    """Regresia centrala: Zarnesti-Brasov nu are poza, Zarnesti-Buzau are.
    Fara aceasta regula, stirea din Brasov ar primi fotografia orasului din Buzau."""
    hit = L.match("BRASOV", "Zarnesti", DATASET)
    assert hit is not None and hit["qid"] == "Q1"
    assert not hit["img"]                        # corect: fara poza, NU poza altui oras


def test_match_unknown_judet_returns_none():
    assert L.match("CLUJ", "Zarnesti", DATASET) is None
    assert L.match("", "Zarnesti", DATASET) is None


def test_match_ignores_diacritics_and_judetul_prefix():
    hit = L.match("VRANCEA", "focsani", DATASET)
    assert hit and hit["qid"] == "Q192265"


def test_match_unknown_name_returns_none():
    assert L.match("VRANCEA", "Localitate Inexistenta", DATASET) is None


# --- usable: dimensiune + orientare + licenta --------------------------------------

@pytest.mark.parametrize("info,expected,why", [
    ({"width": 3840, "height": 2160, "license": "CC BY-SA 4.0"}, True, "caz nominal"),
    ({"width": 2592, "height": 1936, "license": "CC0"}, True, "PD ramane acceptat"),
    ({"width": 1672, "height": 987, "license": "CC BY 3.0"}, True, "CC-BY acceptat"),
    ({"width": 450, "height": 338, "license": "Public domain"}, False, "prea mica"),
    ({"width": 802, "height": 420, "license": "Copyrighted free use"}, False, "prea mica"),
    ({"width": 2592, "height": 3243, "license": "CC BY-SA 3.0"}, False, "portret"),
    ({"width": 2560, "height": 1920, "license": "GPL"}, False, "licenta nepotrivita"),
    ({"width": 3000, "height": 2000, "license": ""}, False, "licenta necunoscuta"),
    ({"width": 3000, "height": 2000, "license": "Fair use"}, False, "fair use"),
    ({"width": 3000, "height": 0, "license": "CC0"}, False, "inaltime lipsa"),
    (None, False, "fara info"),
])
def test_usable(info, expected, why):
    assert L.usable(info) is expected, why


def test_license_free_matches_measured_commons_strings():
    """Sirurile exacte returnate de Commons in masuratoarea pe cele 120 de primarii GOLD."""
    for ok in ("CC BY-SA 3.0", "CC BY-SA 4.0", "CC BY-SA 3.0 ro", "CC BY 3.0",
               "CC BY 2.0", "Public domain", "CC0", "Copyrighted free use"):
        assert L.license_free(ok), ok
    for bad in ("GPL", "Fair use", "All rights reserved", "", None):
        assert not L.license_free(bad), bad


@pytest.mark.parametrize("lic", [
    "CC BY-NC 4.0", "CC BY-ND 4.0", "CC BY-NC-SA 3.0", "CC BY-NC-ND 4.0",
    "CC BY NC 2.0", "cc-by-nd-3.0",
])
def test_license_free_rejects_non_commercial_and_no_derivatives(lic):
    """NC interzice folosirea comerciala, ND operele derivate -- iar pipeline-ul DECUPEAZA
    fiecare imagine, deci produce un derivat. Regexul le accepta (bug real, prins la review):
    `cc[ -]?by` fara granita se potrivea cu 'CC BY-NC 4.0'."""
    assert not L.license_free(lic), lic
    assert not L.usable({"width": 3840, "height": 2160, "license": lic}), lic


# --- locality_for_article: cand se declanseaza ruta --------------------------------

def test_locality_route_only_fires_for_primarie_sources():
    local = {"source": "pl_vrancea_municipiul_focsani", "category": "local"}
    assert L.locality_for_article(local, DATASET)["qid"] == "Q192265"
    for other in ({"source": "digi24", "category": "sport"},
                  {"source": "pl_", "category": "local"},
                  {"category": "local"}):
        assert L.locality_for_article(other, DATASET) is None


@pytest.mark.parametrize("category", ["politic", "sport", "extern", None])
def test_locality_route_requires_a_geographic_category(category):
    """Poarta geografica decide unde se INTAMPLA stirea, nu cine o publica: o primarie
    care scrie despre un subiect national iese din `local`, iar acolo poza localitatii
    ar fi o ilustratie arbitrara."""
    a = {"source": "pl_vrancea_municipiul_focsani", "category": category}
    assert L.eligible(a) is None
    assert L.locality_for_article(a, DATASET) is None


def test_eligible_accepts_both_geographic_categories():
    for cat in ("local", "judetean"):
        assert L.eligible({"source": "pl_vrancea_municipiul_focsani", "category": cat}) \
            == ("vrancea", "focsani")


def test_locality_without_photo_is_not_a_hit():
    """Localitate rezolvata dar fara P18 -> articolul pastreaza coperta generata."""
    assert L.locality_for_article(
        {"source": "pl_brasov_oras_zarnesti", "category": "local"}, DATASET) is None


def test_homonym_localities_have_distinct_qids():
    """Numele NU poate fi cheie de fisier: Zarnesti-Brasov si Zarnesti-Buzau sunt localitati
    diferite, cu poze diferite. Renditiile se numesc dupa QID tocmai ca sa nu se suprascrie
    (bug real: 4 comune Costesti scriau toate in `loc-costesti.jpg`)."""
    qids = {c["qid"] for c in DATASET["zarnesti"]}
    assert len(qids) == 2, "fixture-ul trebuie sa contina doua localitati omonime"
    assert L.match("BRASOV", "Zarnesti", DATASET)["qid"] \
        != L.match("BUZAU", "Zarnesti", DATASET)["qid"]


def test_dataset_missing_file_is_fail_safe():
    assert L.load_dataset("/nonexistent/localities.json") == {}
