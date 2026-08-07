"""Rubrica geografica se decide din TEXT, la orice sursa (owner 2026-08-02): LOCAL =
unde se intampla, nu cine publica. Vezi process._resolve_category."""
from generator import config
from generator.process import _resolve_category


def test_local_source_no_place_leaves_to_ai_topic():
    # Ziar judetean, dar textul (gol aici) nu numeste niciun loc -> pleaca pe tema AI.
    item = {"category": "local", "source": "stiridecluj"}
    assert _resolve_category(item, "sport") == "sport"


def test_non_local_source_follows_ai_category():
    item = {"category": "general", "source": "digi24"}
    assert _resolve_category(item, "economic") == "economic"


def test_non_local_source_invalid_ai_falls_back_to_source():
    item = {"category": "politic", "source": "g4media"}
    assert _resolve_category(item, "inexistent") == "politic"


def test_pinned_categories_are_subset_of_categories():
    assert config.PINNED_CATEGORIES <= set(config.CATEGORIES)


# --- sportul nu intra pe axa geografica, chiar cand textul numeste locul -------------------
# Conventia e verificata pe patru site-uri comparabile, nu presupusa (vezi comentariul din
# process._resolve_category). Textele de mai jos sunt din corpusul real, 2026-08-07.

def test_meciul_nu_devine_stire_locala_desi_numeste_orasul():
    """„Farul Constanta" e numele echipei; gazetteer-ul vede orasul. Modelul vede sportul."""
    item = {"category": "sport", "source": "prosport",
            "title": "Gigi Becali i-a criticat dur pe jucătorii FCSB după remiza cu Farul",
            "teaser": "Patronul a reproșat atitudinea echipei după 2-2 cu Farul Constanța."}
    assert _resolve_category(item, "sport") == "sport"


def test_sportul_dintr_un_ziar_local_pleaca_tot_pe_sport():
    """Cazul care demonteaza regula pe sursa: 63 din 159 de articole cu iconita de sport de pe
    axa geografica vin din ziare LOCALE, nu din presa sportiva. Monitorul de Cluj insusi isi
    pune „CFR pierde cu 0-5" la Sport, nu la Administratie."""
    item = {"category": "local", "source": "zcj",
            "title": "CFR Cluj a pierdut cu 0-5 meciul împotriva norvegienilor de la Tromso",
            "teaser": "Formația din Cluj-Napoca a suferit cea mai drastică înfrângere europeană."}
    assert _resolve_category(item, "sport") == "sport"


def test_impactul_local_al_unui_meci_ramane_local():
    """Linia fina pe care o trag si comparabilele: subiectul e transportul, nu meciul. Modelul
    nu alege `sport` aici, deci axa geografica isi pastreaza articolul. Fara cazul asta,
    regula ar fi „sportul nu e local", ceea ce e prea larg."""
    item = {"category": "local", "source": "zcj",
            "title": "Meciul CFR Cluj - FC Alashkert schimbă traseul autobuzelor",
            "teaser": "Liniile 25 și 46 din Cluj-Napoca sunt deviate în seara meciului."}
    assert _resolve_category(item, "social") in {"local", "zonal", "regional"}


def test_stirea_geografica_obisnuita_nu_e_atinsa_de_regula_de_sport():
    """Garda se aplica DOAR cand modelul a zis `sport`. Restul axei geografice ramane intact."""
    item = {"category": "local", "source": "bzi",
            "title": "Opt adolescenți au speriat localnicii din cartierul Galata",
            "teaser": "Un grup a creat panică pe Calea Galata din Iași în noaptea de 4 august."}
    assert _resolve_category(item, "social") in {"local", "zonal", "regional"}
