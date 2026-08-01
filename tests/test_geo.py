"""Poarta geografica determinista: regiune istorica / judet / localitate.

Cazurile de mai jos nu sunt inventate — sunt exact articolele masurate pe 2026-07-25, cand
`regional` era gresit in 14 din 15 cazuri pentru ca AI-ul primea `regional|zonal|local` ca
etichete goale, fara nicio definitie, si ghicea.
"""
import pytest

from generator import config, geo, process


@pytest.mark.parametrize("text,astept", [
    # --- ce trebuie SA INTRE pe axa geografica
    ("Cluj-Napoca a inaugurat primul centru integrat", "local"),
    ("Primăria Focșani a aprobat bugetul pe 2026", "local"),
    ("Alertă aeriană în județul Tulcea", "zonal"),
    ("Consiliul Județean Vrancea a votat proiectul", "zonal"),
    ("Seceta cumplită din Bărăgan afectează fermierii", "regional"),
    ("Transilvania are cel mai mare grad de împădurire", "regional"),
    ("În Ardeal s-au înregistrat cele mai mari precipitații", "regional"),

    # --- ce trebuie sa RAMANA AFARA: astea sunt chiar scurgerile masurate
    ("Explozie la bordul unei nave cu GPL în Marea Neagră", None),
    ("Comisia Europeană a aprobat un nou pachet de sancțiuni", None),
    ("Un sat din Elveția a fost evacuat după o alunecare de teren", None),
    ("DNA a pus sechestru pe bunurile fostului ministru", None),
    ("Messi a marcat trei goluri în finala campionatului", None),
    ("Horoscopul zilei de vineri pentru toate zodiile", None),
    ("Cursul BNR: euro a crescut la 5,12 lei", None),
])
def test_clasificare(text, astept):
    assert geo.clasifica(text) == astept


def test_calificativul_bate_indexul():
    """Tulcea e SI judet SI municipiu. Textul spune care — fara asta, orice resedinta de
    judet ar trage stirea pe `local` chiar cand articolul zice explicit 'judetul'."""
    assert geo.clasifica("Alertă în județul Tulcea") == "zonal"
    assert geo.clasifica("Incendiu la Tulcea, în zona portului") == "local"


def test_calificativul_flexionat_e_recunoscut():
    """"in nordul judetULUI Tulcea" e la fel de frecvent ca "in judetul Tulcea". Fara
    genitiv, calificativul se rata si stirea cadea pe `local`, fiindca Tulcea e si oras.
    Gasit pe un articol real, 2026-08-01."""
    assert geo.clasifica("Locuitorii din nordul județului Tulcea au primit RO-Alert") == "zonal"
    assert geo.clasifica("Autoritățile județelor Cluj și Alba au decis") == "zonal"
    assert geo.clasifica("În comuna Ciugud s-a inaugurat o școală") == "local"


def test_forma_articulata_e_recunoscuta():
    """'a vizitat Clujul' trebuie sa se potriveasca; altfel ratam jumatate din presa."""
    assert geo.clasifica("Ministrul a vizitat Clujul săptămâna trecută") is not None


def test_castiga_cel_mai_specific():
    """Regula proprietarului: mai multe nume in text -> cel mai specific (2026-08-01)."""
    assert geo.clasifica("Autoritățile din județul Cluj și din Cluj-Napoca") == "local"


def test_cuvintele_comune_nu_sunt_localitati():
    """Exista comune numite Valea, Unirea, Spring. Fara garda, orice text care le contine
    ca simple cuvinte ar deveni `local`."""
    for t in ("Valea a fost inundată de ploi", "Piața Unirea din centru", "Spring Festival"):
        assert geo.clasifica(t) != "local", t


def test_text_gol_nu_arunca():
    assert geo.clasifica("") is None
    assert geo.clasifica(None) is None


def test_indexul_acopera_toate_judetele():
    """Toate cele 42 de judete trebuie sa fie in index — dar 19 dintre ele sunt stocate ca
    `local`, fiindca resedinta poarta acelasi nume (Botosani judet / Botosani oras). Acolo
    calificativul din text decide, ceea ce verificam explicit mai jos."""
    import csv
    from generator.util import strip_diacritics
    index = geo._index()
    with open(geo._CSV, encoding="utf-8-sig") as fh:
        judete = {strip_diacritics((r.get("Județ") or "").strip()).upper()
                  for r in csv.DictReader(fh)}
    judete.discard("")
    lipsa = [j for j in judete if j not in index]
    assert not lipsa, f"judete lipsa din gazetteer: {lipsa}"
    assert all(geo.clasifica(f"în județul {j.title()}") == "zonal" for j in judete)
    assert len(index) > 2000, f"doar {len(index)} nume — gazetteerul pare trunchiat"


def test_toate_regiunile_sunt_recunoscute():
    """MARAMURES e exceptie asumata: e SI regiune istorica SI judet. Regula proprietarului
    zice ca invinge cel mai specific, deci judetul — `zonal`, nu `regional`."""
    for regiune in geo.REGIUNI:
        astept = "zonal" if regiune == "MARAMURES" else "regional"
        assert geo.clasifica(f"Situația din {regiune.title()} rămâne tensionată") == astept, regiune


def test_monedele_si_cuvintele_scurte_nu_devin_localitati():
    """Exista comune Leu, Apa, Pui, Rus. Fara garda de lungime pe localitati, un curs
    valutar sau o stire despre Rusia ar deveni stire locala."""
    for t in ("Cursul Leu-euro a crescut", "Apa a fost oprită în tot cartierul",
              "Rus a fost numit director"):
        assert geo.clasifica(t) != "local", t


# --- integrarea in _resolve_category: partea care chiar opreste scurgerile ---

def _sursa_netematica():
    for sid, s in config.SOURCES.items():
        if s.get("category") not in config.PINNED_CATEGORIES:
            return s.get("category")
    raise AssertionError("config.SOURCES nu are nicio sursa netematica")


def test_ai_ul_nu_mai_poate_pune_o_stire_externa_pe_axa_geo():
    """Cazul real: AI-ul a pus un sat elvetian pe `regional`. Sursa nu e geografica si
    textul n-are niciun loc din Romania -> stirea iese de pe axa."""
    item = {"category": _sursa_netematica(), "title": "Un sat din Elveția a fost evacuat",
            "teaser": "Alunecare de teren în Alpi."}
    assert process._resolve_category(item, "regional") == "general"


def test_ai_ul_greseste_nivelul_iar_poarta_il_corecteaza():
    item = {"category": _sursa_netematica(), "title": "Alertă aeriană în județul Tulcea",
            "teaser": "Drona a intrat în spațiul aerian."}
    assert process._resolve_category(item, "regional") == "zonal"


def test_sursa_geografica_ramane_neatinsa():
    """Sursele pinned decid singure — poarta NU se aplica peste ele. Altfel 345 din 906
    de articole ar iesi de pe axa geografica; masurat 2026-08-01, e decizia owner-ului."""
    geo_cat = sorted(config.PINNED_CATEGORIES)[0]
    item = {"category": geo_cat, "title": "Horoscopul zilei", "teaser": "Zodiile."}
    assert process._resolve_category(item, "sport") == geo_cat


def test_categoria_tematica_nu_e_atinsa_de_poarta():
    item = {"category": _sursa_netematica(), "title": "Messi a marcat trei goluri",
            "teaser": "Finala campionatului."}
    assert process._resolve_category(item, "sport") == "sport"


def test_clusterul_C_e_clasificat_si_dupa_synthesis():
    """Modelul C scrie 'synthesis', nu 'teaser'. Daca poarta citea doar 'teaser', un
    cluster s-ar fi clasificat doar dupa titlu."""
    item = {"category": _sursa_netematica(), "title": "Incident aviatic",
            "synthesis": "Evenimentul a avut loc în județul Tulcea, aproape de deltă."}
    assert process._resolve_category(item, "local") == "zonal"
