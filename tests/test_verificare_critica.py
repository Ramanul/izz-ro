"""Teste de verificare critică pentru cerințele din USER_REQUEST:
1. Pasarea obligatorie a parametrului 'summary' alături de 'title' și 'category' în generarea vizuală.
2. Clasificator bazat pe dicționare de cuvinte-cheie (Sănătate, Auto/Trafic, Carieră/Educație, Energie/Economic, Cultură/Turism).
3. Stilul default exclusiv pe grafică editorială neutră (geometrie caldă), INTERZICÂND circuitele PCB sau valurile sci-fi pe știri non-tech.
4. Regex extins pentru instituții cu re.IGNORECASE și suport pentru adjective/diacritice (ex: 'poliția rutieră', 'gyergyószentmiklós').
5. Randare full-bleed (fără șabloane tăiate) dacă articolul dispune de o fotografie reală validă în 'image_url'.
"""
from generator import htmlart, render
from generator.art_generativ import clasifica_domeniu, genereaza_scena_generativa


# -----------------------------------------------------------------------------
# 1 & 2. Clasificator de domenii și pasarea lui 'summary'
# -----------------------------------------------------------------------------

def test_pasare_summary_si_clasificare_sanatate():
    res = clasifica_domeniu(
        title="Noi măsuri anunțate pentru spitale",
        summary="Medicii și pacienții beneficiază de tratamente noi de cardiologie",
        category="social"
    )
    assert res == "sanatate"


def test_clasificare_auto_trafic():
    res = clasifica_domeniu(
        title="Trafic blocat pe DN1 din cauza unui accident",
        summary="Polițiștii și șoferii recomandă rute ocolitoare pe autostradă",
        category="eveniment"
    )
    assert res == "auto_trafic"


def test_clasificare_cariera_educatie():
    res = clasifica_domeniu(
        title="Rezultate la examenul de bacalaureat",
        summary="Elevii și profesorii de la mai multe licee cer suplimentarea de burse",
        category="social"
    )
    assert res == "cariera_educatie"


def test_clasificare_energie_economic():
    res = clasifica_domeniu(
        title="Prețul la gaze naturale și curent electric",
        summary="Facturile la energie cresc conform noilor reglementări ale ANRE",
        category="actualitate"
    )
    assert res == "energie_economic"


def test_clasificare_cultura_turism():
    res = clasifica_domeniu(
        title="Festivalul de teatru și film din Sibiu",
        summary="Mii de turiști au rezervat cazare la hotelurile din zonă",
        category="eveniment"
    )
    assert res == "cultura_turism"


def test_clasificare_tech_ai():
    res = clasifica_domeniu(
        title="Noul microcip dezvoltat de Nvidia",
        summary="Procesoarele hardware accelerează modelele de inteligență artificială",
        category="stiinta"
    )
    assert res == "tech_ai"


# -----------------------------------------------------------------------------
# 3. Interzicerea circuitelor PCB și a valurilor sci-fi pe știri non-tech
# -----------------------------------------------------------------------------

def test_stiri_non_tech_primesc_exclusiv_geometrie_calda():
    # Cazuri non-tech variate
    articole_non_tech = [
        {"title": "Tratament nou la spitalul universitar", "summary": "Medicii au finalizat studiul clinic", "category": "sanatate"},
        {"title": "Accident pe șosea cu mașini implicate", "summary": "Circulația pe drum este deviată", "category": "auto"},
        {"title": "Profesorii cer salarii mai mari în școli", "summary": "Elevii susțin evaluarea națională", "category": "educatie"},
        {"title": "Expoziție de artă la muzeul național", "summary": "Turiștii vizitează monumentul istoric", "category": "cultura"},
        {"title": "Declarații politice în parlament", "summary": "Dezbateri aprinse pe tema legii", "category": "politic"},
        {"title": "Victoria echipei naționale", "summary": "Jucătorii au obținut calificarea", "category": "sport"},
    ]
    for a in articole_non_tech:
        scena = genereaza_scena_generativa(
            a,
            seed=b"\x01\x02\x03\x04\x05\x06\x07\x08",
            title=a["title"],
            category=a["category"],
            summary=a["summary"]
        )
        assert scena["stil"] == "warm_geometry", (
            f"Articolul non-tech '{a['title']}' a primit stilul '{scena['stil']}', interzis pe non-tech!"
        )
        assert "circuit" not in scena["stil"]
        assert "wireframe" not in scena["stil"]
        assert "parametric" not in scena["stil"]


def test_stirile_tech_pot_primi_stiluri_tehnologice():
    a = {"title": "Lansare procesor AI cu arhitectură nouă", "category": "tech", "summary": "Noul cip integrează tranzistori avansați"}
    scena = genereaza_scena_generativa(
        a,
        seed=b"\x01\x02\x03\x04\x01\x06\x07\x08",
        title=a["title"],
        category=a["category"],
        summary=a["summary"]
    )
    assert scena["stil"] in ("circuit_matrix", "wireframe_mesh", "parametric_waves")


# -----------------------------------------------------------------------------
# 4. Regex extins instituții (re.IGNORECASE, adjective, diacritice maghiare)
# -----------------------------------------------------------------------------

def test_institutie_politia_rutiera_cu_minuscula():
    art = {"title": "poliția rutieră a anunțat controale ample în trafic"}
    assert htmlart._carlig_tematic(art) == "Poliția rutieră"


def test_institutie_politia_rutiera_cu_adjectiv():
    art = {"title": "Poliția Rutieră a intervenit la locul accidentului"}
    assert htmlart._carlig_tematic(art) == "Poliția Rutieră"


def test_institutie_cu_diacritice_maghiare_si_minuscule():
    art = {"title": "Primăria Gyergyószentmiklós a aprobat bugetul pe anul viitor"}
    assert htmlart._carlig_tematic(art) == "Primăria Gyergyószentmiklós"


def test_nume_localitate_maghiara_direct():
    art = {"title": "Festival cultural de amploare la Gyergyószentmiklós"}
    assert htmlart._carlig_tematic(art) == "Gyergyószentmiklós"


# -----------------------------------------------------------------------------
# 5. Randare full-bleed când articolul dispune de fotografie reală în 'image_url'
# -----------------------------------------------------------------------------

def test_articol_cu_image_url_forteaza_fullbleed():
    a = {
        "title": "Eveniment capturat în fotografie de presă",
        "category": "eveniment",
        "slug": "eveniment-foto",
        "image_url": "https://images.unsplash.com/photo-123456789.jpg"
    }
    s = htmlart.stil_inline(a)
    a["art_style"] = s
    assert s.get("full_bleed") is True
    assert s.get("image_url") == "https://images.unsplash.com/photo-123456789.jpg"

    # Verificare randare macro card
    card_macro = render._env().get_template("_card.html").module.card
    html_card = str(card_macro(a))
    assert 'class="card-media card-media--fullbleed"' in html_card
    assert 'https://images.unsplash.com/photo-123456789.jpg' in html_card
    # Asigurăm că nu apar șabloanele decupate (editorial, inversat, banda, arc)
    assert 'class="art art--' not in html_card

    # Verificare randare directă macro art
    art_macro = render._env().get_template("_art.html").module.art
    html_art = str(art_macro(a))
    assert 'class="art art--fullbleed' in html_art
    assert 'class="art-fullbleed-img"' in html_art
    assert 'https://images.unsplash.com/photo-123456789.jpg' in html_art
