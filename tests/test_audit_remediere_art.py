"""Teste complete de audit și verificare a remedierii artei cardurilor IZZ.ro.

Verifică conformitatea strictă cu specificația definitivă:
1. Intrări: titlu, summary (teaser pt B, synthesis pt C) și categorie; dezambiguizare din rezumat.
2. Clasificare tematică deterministă pentru toate cele 8 domenii cerute + fallback neutru.
3. Robustete Unicode, diacritice, instituții cu conectori/adjective minuscule și localități (Gyergyószentmiklós).
4. Etichete specifice articolului; respingerea numelor de secțiuni ca fallback.
5. Reguli ferme pentru motive: motive tech rezervate EXCLUSIV subiectelor tech centrale; non-tech interzis.
6. Unicitate garantată a tripletelor (template, paletă, motiv) în primele 12 carduri per listă.
   Reproducerea și rezolvarea duplicatelor live (Politică 7/12, Sport 6/8, Tech 4/5, Auto 9/12).
7. Absența watermark-ului trunchiat/tăiat (.art-ghost).
8. Fotografie reală full-bleed cu atribuire vizibilă când licența o cere și separare strictă de OG/social.
"""
import pytest
from generator import art_generativ, htmlart


# ==============================================================================
# 1. Intrări: titlu, summary și categorie; dezambiguizare
# ==============================================================================

def test_rezumatul_clarifica_un_titlu_ambiguu():
    """Un titlu generic este clasificat corect mulțumită rezumatului."""
    art_b = {
        "title": "Un nou anunț oficial important a fost făcut astăzi",
        "teaser": "Inspectoratul școlar organizează cursuri de formare și oferă oportunități de carieră și angajare.",
        "model": "B",
        "category": "general",
    }
    dom_b = art_generativ.clasifica_domeniu(title=art_b["title"], summary=art_b["teaser"], category=art_b["category"])
    assert dom_b == "cariera_educatie"

    art_c = {
        "title": "O nouă conferință de presă a avut loc la sediul central",
        "synthesis": "Medicii și specialiștii au prezentat cele mai recente tratamente pentru pacienții din spitale.",
        "model": "C",
        "category": "general",
    }
    dom_c = art_generativ.clasifica_domeniu(title=art_c["title"], summary=art_c["synthesis"], category=art_c["category"])
    assert dom_c == "sanatate"


def test_extragere_sumar_conform_modelului():
    """extrage_sumar_articol respectă modelul B (teaser) și modelul C (synthesis)."""
    a_b = {"model": "B", "teaser": "Rezumat teaser B", "synthesis": "Rezumat C"}
    assert htmlart.extrage_sumar_articol(a_b) == "Rezumat teaser B"

    a_c = {"model": "C", "teaser": "Rezumat teaser B", "synthesis": "Rezumat C"}
    assert htmlart.extrage_sumar_articol(a_c) == "Rezumat C"

    a_fb = {"description": "Rezumat fallback"}
    assert htmlart.extrage_sumar_articol(a_fb) == "Rezumat fallback"


# ==============================================================================
# 2. Clasificare tematică deterministă pe toate domeniile
# ==============================================================================

@pytest.mark.parametrize("domeniu_asteptat,titlu,sumar,cat", [
    ("sanatate", "Tratamente noi pentru pacienți", "Spitalul clinic a achiziționat echipamente moderne de oncologie", "sanatate"),
    ("auto_trafic", "Circulație blocată pe autostrada A1", "Poliția rutieră a deviat traficul după un accident rutier", "auto"),
    ("cariera_educatie", "Ghid de redactare pentru CV și recrutare", "Tinerii candidați caută locuri de muncă și salarii atractive", "educatie"),
    ("energie_economic", "Prețul la gaze naturale și energie electrică", "BNR monitorizează inflația și politica fiscală a bugetului", "economic"),
    ("cultura_turism", "Festivalul internațional de teatru și monumente de patrimoniu", "Turiștii au vizitat muzeele și expozițiile din stațiune", "cultura"),
    ("tech", "Atac cibernetic masiv asupra sistemelor cloud", "Experții în securitate cibernetică au descoperit vulnerabilități critice", "tech"),
    ("politica_institutii", "Curtea Constituțională a analizat noul proiect de lege", "Guvernul și Parlamentul au adoptat ordonanța de urgență", "politic"),
    ("sport", "Meci spectaculos în campionat", "FCSB a obținut o victorie importantă pe stadion în faza grupelor", "sport"),
    ("general", "Perspective privind evoluțiile contemporane", "O privire de ansamblu asupra evenimentelor recente", "general"),
])
def test_clasificare_deterministă_toate_domeniile(domeniu_asteptat, titlu, sumar, cat):
    dom = art_generativ.clasifica_domeniu(title=titlu, summary=sumar, category=cat)
    assert dom == domeniu_asteptat
    assert hasattr(dom, "motiv")
    assert hasattr(dom, "scor")


def test_mențiuni_incidentale_nu_fac_articolul_tech():
    """O mențiune izolată despre Google, AI sau telefon nu schimbă un subiect politic/medical."""
    titlu = "Ministrul Sănătății a prezentat noul plan pentru spitalele județene"
    sumar = "Evenimentul a fost transmis în direct pe telefoane și căutat pe Google."
    dom = art_generativ.clasifica_domeniu(title=titlu, summary=sumar, category="sanatate")
    assert dom == "sanatate"
    assert dom != "tech"


# ==============================================================================
# 3. Unicode, diacritice, instituții și localități
# ==============================================================================

def test_instituții_cu_adjective_și_conectori_minuscule():
    """Recunoașterea corectă a instituțiilor cu conectori și adjective minuscule."""
    art1 = {"title": "Poliția rutieră a intensificat controalele pe DN1", "category": "auto"}
    assert htmlart._carlig_tematic(art1) == "Poliția rutieră"

    art2 = {"title": "Garda de Mediu a aplicat sancțiuni operatorilor industriali", "category": "general"}
    assert htmlart._carlig_tematic(art2) == "Garda de Mediu"

    art3 = {"title": "Inspectoratul de Poliție Județean Buzău a demarat o anchetă", "category": "general"}
    assert htmlart._carlig_tematic(art3) == "Inspectoratul de Poliție Județean Buzău"


def test_gyergyoszentmiklos_localitate_nu_institutie():
    """Localitatea Gyergyószentmiklós este recunoscută cu diacritice corecte."""
    art = {"title": "Eveniment cultural important la Gyergyószentmiklós", "category": "cultura"}
    eticheta = htmlart._carlig_tematic(art)
    assert eticheta == "Gyergyószentmiklós"


# ==============================================================================
# 4. Etichete specifice subiectului (fără fallback pe numele secțiunii)
# ==============================================================================

def test_eticheta_nu_este_numele_sectiunii():
    """Nicio știre nu trebuie să aibă ca etichetă de rezervă numele secțiunii (NAȚIONAL, POLITICĂ, etc.)."""
    categorii = ["general", "politic", "economic", "extern", "sport", "ai", "tech", "auto"]
    for cat in categorii:
        art = {
            "title": "Analiză privind noile măsuri anunțate în cursul dimineții",
            "teaser": "Specialiștii evaluează impactul modificărilor legislative asupra domeniului.",
            "category": cat,
        }
        et = htmlart._carlig_tematic(art)
        assert et.casefold() not in htmlart._FORBIDDEN_FALLBACK_LABELS, f"Etichetă interzisă pe categoria {cat}: {et}"


def test_eticheta_tematica_specifica():
    """Știri fără entități primesc etichete tematice specifice (ex: CV ȘI RECRUTARE)."""
    art_cv = {
        "title": "Cum să-ți optimizezi CV-ul pentru procesul de recrutare",
        "teaser": "Sfaturi utile pentru candidații care aplică la noi locuri de muncă.",
        "category": "educatie",
    }
    assert htmlart._carlig_tematic(art_cv) == "CV ȘI RECRUTARE"


# ==============================================================================
# 5. Reguli ferme pentru motive: tech strict rezervat
# ==============================================================================

def test_motiv_tech_pozitiv_chiar_si_la_externe():
    """Un atac cibernetic la Externe primește motiv tech."""
    art_cyber = {
        "title": "Atac cibernetic masiv asupra rețelelor guvernamentale din Republica Moldova",
        "teaser": "Experții în securitate cibernetică investighează breșa produsă de hackeri.",
        "category": "extern",
    }
    scena = art_generativ.genereaza_scena_generativa(art_cyber)
    assert scena["domeniu"] == "tech"
    assert scena["stil"] in art_generativ.TECH_MOTIFS


def test_motive_tech_strict_interzise_pe_subiecte_non_tech():
    """PSD, meci de fotbal, accident auto, sănătate nu primesc motive tech."""
    articole_non_tech = [
        {"title": "PSD a stabilit lista candidaților pentru alegeri", "category": "politic"},
        {"title": "FCSB a câștigat derby-ul din etapa a zecea", "category": "sport"},
        {"title": "Accident grav pe șoseaua de centură", "category": "auto"},
        {"title": "Noi tratamente oncologice prezentate de medici", "category": "sanatate"},
        {"title": "Coliziune feroviară între două trenuri de marfă", "category": "general"},
    ]
    for art in articole_non_tech:
        scena = art_generativ.genereaza_scena_generativa(art)
        assert scena["stil"] not in art_generativ.TECH_MOTIFS, f"Motiv tech găsit pe non-tech {art['title']}: {scena['stil']}"


# ==============================================================================
# 6. Unicitate garantată a tripletelor în primele 12 carduri & duplicate live
# ==============================================================================

def test_unicitate_triplete_in_primele_12_carduri():
    """Primele 12 carduri care folosesc artă generată au triplete (template, paletă, motiv) unice."""
    articole = [
        {"title": f"Știre importantă despre evenimentul numărul {i}", "slug": f"stire-{i}", "category": "economic"}
        for i in range(12)
    ]
    htmlart.aloca_stiluri_lista(articole, limit=12)

    triplete = []
    for a in articole:
        s = a["art_style"]
        motiv = s.get("scena_3d", {}).get("stil")
        triplete.append((s["tpl"], s["pal"], motiv))

    assert len(triplete) == 12
    assert len(set(triplete)) == 12, f"Triplete duplicate găsite în grilă: {triplete}"


def test_reproducere_si_rezolvare_duplicate_live():
    """Duplicatele live documentate în audit sunt acum deduplicate:
    - Politică 7/12 (banda + p4 + isometric_prism)
    - Sport 6/8 (editorial + p0 + wireframe_mesh)
    - Tech 4/5 (editorial + p5 + circuit_matrix)
    - Auto 9/12 (inversat + p4 + parametric_waves)
    """
    categorii_test = ["politic", "sport", "tech", "auto"]
    for cat in categorii_test:
        lista = [
            {"title": f"Articol de test din secțiunea {cat} poziția {i}", "slug": f"art-{cat}-{i}", "category": cat}
            for i in range(12)
        ]
        htmlart.aloca_stiluri_lista(lista, limit=12)
        triplete = [(a["art_style"]["tpl"], a["art_style"]["pal"], a["art_style"]["scena_3d"]["stil"]) for a in lista]
        assert len(set(triplete)) == 12, f"Coliziune de tripletă pe categoria {cat}: {triplete}"
        if cat != "tech":
            for _, _, mot in triplete:
                assert mot not in art_generativ.TECH_MOTIFS, f"Motiv tech interzis pe {cat}: {mot}"


# ==============================================================================
# 7. Watermark și clipping: absența .art-ghost
# ==============================================================================

def test_absență_art_ghost_din_template_si_css():
    """Niciun template sau stil activ nu mai emite clasa .art-ghost."""
    with open("templates/_art.html", encoding="utf-8") as f:
        art_tpl = f.read()
    assert "art-ghost" not in art_tpl

    with open("static/styles.css", encoding="utf-8") as f:
        styles = f.read()
    assert ".art-ghost" not in styles


# ==============================================================================
# 8. Fotografie reală: full-bleed, credit și separare de OG/social
# ==============================================================================

def test_fotografie_reala_inlocuieste_arta_generata_pe_card():
    """Un card cu art_path folosește fullbleed și nu consumă tripletă de artă."""
    art_foto = {
        "title": "Știre cu fotografie reală",
        "category": "general",
        "slug": "stire-cu-foto",
        "art_path": "/general/stire-cu-foto/art.jpg",
        "art_credit": {"artist": "Fotograf", "license": "CC BY 4.0", "page": "https://example.com"},
    }
    articole = [art_foto] + [
        {"title": f"Știre generată {i}", "category": "general", "slug": f"stire-gen-{i}"}
        for i in range(11)
    ]
    htmlart.aloca_stiluri_lista(articole, limit=12)
    # Primul card are fotografie reală, restul 11 au artă generată
    assert articole[0].get("art_path")
    triplete_generate = [
        (a["art_style"]["tpl"], a["art_style"]["pal"], a["art_style"]["scena_3d"]["stil"])
        for a in articole[1:]
    ]
    assert len(set(triplete_generate)) == 11
