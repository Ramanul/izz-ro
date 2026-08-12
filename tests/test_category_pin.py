"""Rubrica geografica se decide din TEXT, la orice sursa (owner 2026-08-02): LOCAL =
unde se intampla, nu cine publica. Vezi process._resolve_category."""
import pytest

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
    assert _resolve_category(item, "social") in {"local", "judetean", "regional"}


# --- locul e NUMIT in text, dar e stirea DESPRE el? --------------------------------------
# Regula are doua trepte si ambele sunt masurate (2704 articole, 2026-08-07). Textele si
# `entities` de mai jos sunt VERBATIM din corpus. Vezi process._locul_e_subiectul.

def test_stire_nationala_dintr_un_ziar_local_pleaca_de_pe_axa_geografica():
    """Cazul-samanta: „Fitch mentine ratingul Romaniei" publicat de un ziar din Brasov.
    Textul numeste Romania si Bucurestiul, dar modelul n-a pus niciun loc din gazetteer
    printre entitatile cheie -> stirea nu e despre un loc, e economie."""
    item = {"category": "general", "source": "bizbrasov",
            "title": "Fitch menține ratingul BBB- al României cu perspectivă negativă",
            "teaser": "Agenția internațională Fitch a decis păstrarea ratingului suveran al "
                      "României la limita categoriei recomandate investitorilor, evitând "
                      "retrogradarea sub pragul de investment grade la București."}
    assert _resolve_category(item, "economic", ["Fitch", "România"]) == "economic"


def test_stire_externa_dintr_un_ziar_local_pleaca_de_pe_axa_geografica():
    item = {"category": "general", "source": "bzi",
            "title": "Stare de urgență decretată în Ceuta în urma unui flux masiv de migranți",
            "teaser": "Enclava spaniolă Ceuta se confruntă cu o criză determinată de trecerea "
                      "ilegală a mii de persoane din Maroc, iar autoritățile de la București "
                      "urmăresc situația."}
    assert _resolve_category(item, "extern", ["Ceuta", "Maroc"]) == "extern"


def test_locul_confirmat_de_entitati_ramane_pe_axa_geografica():
    """Cealalta jumatate a regulii: cand modelul CHIAR spune ca stirea e despre locul ala,
    articolul ramane local. Fara testul asta, regula ar putea trece stergand tot."""
    item = {"category": "local", "source": "bizbrasov",
            "title": "Polițiștii brașoveni au cumpărat limonadă de la un stand infantil",
            "teaser": "O patrulă de poliție din Brașov s-a oprit pentru a sprijini inițiativa "
                      "unor copii care deschiseseră un punct de vânzare a limonadei."}
    assert _resolve_category(item, "social", ["Brasov"]) in {"local", "judetean", "regional"}


@pytest.mark.parametrize("titlu,teaser,ent", [
    # locul e INGHITIT in numele institutiei, deci potrivirea exacta pe entitati il rateaza
    ("Muzeul de Artă Populară din Constanța organizează un atelier de icoane",
     "Instituția din Constanța va găzdui vineri un atelier de pictură pe sticlă.",
     ["Muzeul de Artă Populară Constanța", "Nicula"]),
    ("Patru intervenții ale Salvamont Suceava în mai puțin de o săptămână",
     "Salvatorii montani din Suceava au intervenit în patru cazuri turistice.",
     ["Salvamont Suceava"]),
])
def test_locul_din_TITLU_nu_are_nevoie_de_coroborare(titlu, teaser, ent):
    """Treapta 1, si e cea care opreste regula sa faca prapad. Masurat: aplicata si peste
    titluri, coroborarea ar taia 152 de articole din compartimentul ala, aproape toate
    corecte, fiindca locul sta in numele institutiei. Compartimentul are 10% eroare — nu-l
    reparam cu o regula care ii strica 20%."""
    item = {"category": "local", "source": "dobrogeaonline", "title": titlu, "teaser": teaser}
    assert _resolve_category(item, "social", ent) in {"local", "judetean", "regional"}


def test_fara_entitati_filtrul_nu_sterge():
    """Fail-open declarat: un filtru fara date nu are voie sa decida. 6 din 264 de articole
    din compartimentul 2 n-au entitati deloc."""
    item = {"category": "local", "source": "bizbrasov",
            "title": "Incendiu într-o hală",
            "teaser": "Pompierii au intervenit la o hală din Brașov, fără victime."}
    assert _resolve_category(item, "social", None) in {"local", "judetean", "regional"}


def test_stirea_geografica_obisnuita_nu_e_atinsa_de_regula_de_sport():
    """Garda se aplica DOAR cand modelul a zis `sport`. Restul axei geografice ramane intact."""
    item = {"category": "local", "source": "bzi",
            "title": "Opt adolescenți au speriat localnicii din cartierul Galata",
            "teaser": "Un grup a creat panică pe Calea Galata din Iași în noaptea de 4 august."}
    assert _resolve_category(item, "social") in {"local", "judetean", "regional"}
