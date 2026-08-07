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


def test_sursa_geografica_fara_loc_pleaca_pe_tema():
    """LOCAL = unde se intampla, nu cine publica (owner 2026-08-02). Un horoscop de la un
    ziar judetean nu are niciun loc in text -> pleaca de pe axa geografica pe tema aleasa de AI.
    Masurat pe corpus: 324 din 940 de articole geografice pleaca asa, majoritatea corect
    (horoscop, stiri nationale, externe filate gresit ca 'zonal' de sursa)."""
    geo_cat = sorted(config.PINNED_CATEGORIES)[0]
    item = {"category": geo_cat, "title": "Horoscopul zilei", "teaser": "Zodiile."}
    assert process._resolve_category(item, "sport") == "sport"


def test_sursa_geografica_cu_loc_ia_nivelul_din_text():
    """Un ziar judetean (sursa 'zonal') care scrie despre o comuna anume ajunge 'local' —
    nivelul vine din TEXT, nu din sursa. Inima regulii owner 2026-08-02."""
    item = {"category": "zonal", "title": "Restrictii de circulatie in Cluj-Napoca",
            "teaser": "Primaria a anuntat restrictii pe perioada festivalului."}
    assert process._resolve_category(item, "zonal") == "local"


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


# --- Satele, deschise DOAR de judetul sursei (SIRUTA Slice 2) -------------------------
#
# De ce nu sunt in indexul global: numele de sat se repeta intre judete (POIANA x38,
# "SATU NOU" x42), iar masurat pe corpus adaugarea chiar si a celor unice global a facut 49
# de articole `local` gresit — „Saturn retrograd" (Saturn e sat in Constanta), horoscopul,
# „FCSB vs FK Auda". Toate veneau de la surse NATIONALE, care n-au judet: de aici regula.

def test_satul_nu_conteaza_fara_judetul_sursei():
    """Exact articolul real de la Ziua de Cluj, fara sa stim ca sursa e din Cluj."""
    assert geo.clasifica("Incendiu la o cabană din apropierea localității Nicula") is None


def test_satul_face_stirea_locala_cand_judetul_se_potriveste():
    assert geo.clasifica("Incendiu la o cabană din apropierea localității Nicula", "CLUJ") == "local"


def test_satul_altui_judet_nu_deschide_poarta():
    assert geo.clasifica("Incendiu la o cabană din apropierea localității Nicula", "TIMIS") is None


@pytest.mark.parametrize("text", [
    "Saturn retrograd aduce schimbări pentru toate zodiile",
    "Horoscopul zilei de vineri pentru toate zodiile",
    "FCSB a pierdut meciul cu FK Auda",
])
def test_falsurile_masurate_raman_afara_la_sursele_nationale(text):
    """Sursa nationala -> judet None -> poarta satelor nu se deschide niciodata."""
    assert geo.clasifica(text, geo.judet_sursa("protv")) is None


def test_judetul_din_text_bate_satul_omonim():
    """SIRUTA are sate cu numele judetului lor. Fara garda, „judetul Galati" devenea stire
    LOCALA: masurat, 3 din 15 schimbari erau exact asta (Galati, Brasov, Vaslui)."""
    assert geo.clasifica("Județul Galați a aprobat rectificarea bugetului", "GALATI") == "zonal"
    assert geo.clasifica("Județul Brașov se află sub avertizare cod galben", "BRASOV") == "zonal"


@pytest.mark.parametrize("cheie,astept", [
    ("zcj", "CLUJ"),                                  # declarat in config (cheia nu-l spune)
    ("emaramures", "MARAMURES"),
    ("pl_cluj_municipiul_cluj_napoca", "CLUJ"),       # dedus din cheie
    ("cj_vaslui", "VASLUI"),
    ("protv", None),                                  # sursa nationala
])
def test_judet_sursa(cheie, astept):
    assert geo.judet_sursa(cheie) == astept


def test_toate_ziarele_judetene_declara_un_judet_cunoscut():
    """Un `judet` scris gresit in config n-ar da eroare — poarta pur si simplu n-ar deschide
    nimic, tacut. Asta il prinde."""
    for cheie, sursa in config.SOURCES.items():
        declarat = sursa.get("judet")
        if not declarat:
            continue
        judet = geo.judet_sursa(cheie)
        assert judet in geo._sate(), f"{cheie}: judetul '{declarat}' nu exista in sate_judet.csv"


def test_gazetteerul_de_sate_acopera_toate_judetele():
    sate = geo._sate()
    assert len(sate) == 42, f"asteptam 42 de judete, avem {len(sate)}"
    assert sum(len(v) for v in sate.values()) > 10000


@pytest.mark.parametrize("nume", ["ADRIAN", "MARIUS", "IRINA", "SATURN", "VENUS", "ROMANA",
                                  "NEAGRA", "DUNAREA", "DACIA", "GEORGE COSBUC"])
def test_prenumele_si_omonimele_nu_sunt_sate_potrivibile(nume):
    """Toate sunt sate reale in SIRUTA, si toate apar in corpus cu ALT sens — „Adrian
    Codirlasu" (19 aparitii intr-o saptamana), „Politia Romana" (12), „Marea Neagra" (10),
    „Saturn retrograd" (4). Un ziar judetean care scrie despre un om pe nume Adrian n-are
    voie sa publice o stire locala din asta."""
    assert not any(nume in sate for sate in geo._sate().values())


def test_un_prenume_omonim_nu_face_stirea_locala():
    text = "Adrian Ropotan a suferit o fractură deschisă după un accident rutier"
    assert geo.clasifica(text, "MURES") is None      # ADRIAN e sat in Mures, dar aici e om


# ---------------------------------------------------------------- nume ambigue (UAT)
# Aceleasi omonime, dar la nivelul indexului global de UAT-uri, unde stergerea numelui nu e
# o optiune: Romanul e municipiu cu primarie care publica pe izz.ro, Voluntari e oras de
# 40.000. Masurat pe corpus 2026-08-03: 49 de articole erau `local` din motive de genul asta.

@pytest.mark.parametrize("text", [
    "Analiză privind eșecul strategic al lui Vladimir Putin în invazia Ucrainei",
    "Traian Băsescu critică gestionarea crizei energetice",
    "Curtea de Casație din Franța a respins recursul",
    "Românii pot vota designul viitoarelor bancnote euro emise de Banca Centrală Europeană",
    "Oana Roman și-a expus noua siluetă într-un costum de baie",
    "Filarmonica George Enescu a prezentat stagiunea 2026-2027",
    "Denis Drăguș a bifat o nouă reușită la Trabzonspor",
    "Marius Baciu refuză să demisioneze de la FCSB",
    "O treaptă de rachetă SpaceX se va prăbuși pe Lună",
    "Trei zodii au parte de succes major după Luna Plină",
    "ÎNSCRIERI - SÂMBĂTA 22.08.2026, evaluare medicală gratuită",
    "Actrița Maia Morgenstern participă la eveniment",
])
def test_numele_ambigue_fara_marca_geografica_nu_sunt_locuri(text):
    """Toate numele astea sunt localitati reale in index, dar aici sunt o persoana, o zi, un
    satelit natural sau o institutie. Fara marca geografica in text nu deschid axa."""
    assert geo.clasifica(text) is None


@pytest.mark.parametrize("text,nivel", [
    ("Primăria Municipiului Roman organizează concurs de recrutare", "local"),
    ("Incendiu la Roman, într-o hală de producție", "local"),
    ("Lucrări de reabilitare în comuna Vladimir", "local"),
    ("Autobuz nou din Voluntari către Otopeni", "local"),
    ("Drum județean modernizat în localitatea Cristian", "local"),
])
def test_numele_ambigue_cu_marca_geografica_raman_locuri(text, nivel):
    """Cealalta jumatate a regulii, si motivul pentru care numele NU se sterg din index:
    marcate geografic, sunt exact ce par."""
    assert geo.clasifica(text) == nivel


def test_marca_geografica_nu_se_aplica_numelor_neambigue():
    """Garda e strict pe `_AMBIGUE`. „Universitatea Cluj" n-are nicio prepozitie inainte si
    trebuie sa ramana zonal — masurat, 890 din 1606 de potriviri din corpus n-au marca."""
    assert geo.clasifica("Universitatea Cluj a pierdut meciul") == "zonal"
    assert geo.clasifica("Salvamont Neamț a intervenit de patru ori") == "zonal"
    # Suceava e SI judet SI municipiu, deci indexul da corect `local` — l-am pus aici din
    # greseala prima data. Ramane ca exemplu: garda nu-l atinge, nivelul vine din index.
    assert geo.clasifica("ISU Suceava a deschis un punct de prim ajutor") == "local"


def test_lista_ambigua_chiar_exista_in_index():
    """Doua lucruri deodata.

    Unu: un nume scris gresit in `_AMBIGUE` n-ar da eroare — n-ar filtra nimic, tacut.

    Doi, si mai important: invariantul asta e MOTIVUL pentru care bucla satelor din
    `clasifica` nu verifica `_AMBIGUE`. Fiind toate si UAT-uri, garda `index.get()` de acolo
    le taie oricum. Daca cineva adauga in `_AMBIGUE` un nume care e DOAR sat, testul pica
    aici — si atunci bucla satelor chiar are nevoie de propria garda.
    """
    index = geo._index()
    lipsa = sorted(n for n in geo._AMBIGUE if n not in index)
    assert not lipsa, f"nume din _AMBIGUE care nu sunt in indexul de UAT-uri: {lipsa}"


# ------------------------------------- UAT-uri inghitite intr-un nume propriu compus cunoscut
# A treia clasa, cu al treilea mecanism, si diferenta fata de cele doua de mai jos/sus e
# MASURATA: la regiuni discriminatorul e „cuvant cu majuscula lipit inainte", si aici ar face
# rau — pe corpus, tiparul ala la UAT-uri inseamna aproape mereu institutie plus locul ei
# („Primaria Brasov", „Consiliul Judetean Cluj"), adica exact stirile locale corecte.
# De-asta lista e enumerativa, cu ablatie per membru. Vezi `geo._COMPUSE_NEGEO`.

@pytest.mark.parametrize("text", [
    "Donald Trump anulează atacurile asupra Iranului, anunță Casa Albă",
    "Casa Albă finalizează un cadru de supraveghere pentru inteligența artificială",
    "Gala UFC organizată la Casa Albă de ziua lui Trump a generat pierderi",
    "Curtea de Apel București a blocat suspendarea permiselor pentru amenzi neplătite",
    "Fost judecător critică răspunsul Curții de Apel București în cazul Robert Negoiță",
    "Bursa de Valori București a închis ședința de marți în scădere",
    "Evoluția Bursei de Valori București, discutată de investitorul Marius Alexe",
])
def test_uat_in_compus_negeo_nu_e_geografie(text):
    """Cele trei compuse masurate: 24 de articole plecau pe rubrica geografica gresita."""
    assert geo.clasifica(text) is None


@pytest.mark.parametrize("text,nivel", [
    # Sondele din WS-0030: ruta prin `_AMBIGUE` le-ar fi pierdut pe toate patru, fiindca
    # `_MARCA_GEO` n-are JUDETEAN si nici PREFECTURA, iar ultima n-are nimic inainte.
    ("Consiliul Județean Alba a aprobat bugetul rectificat", "zonal"),
    ("Prefectura Alba a convocat comitetul pentru situații de urgență", "zonal"),
    ("Inspectoratul Școlar Județean Alba a publicat rezultatele", "zonal"),
    ("Alba a fost lovită de o furtună puternică", "zonal"),
    ("Un șofer din Alba a fost condamnat după ce a condus băut", "zonal"),
    # Prefixul e specific: alte institutii cu acelasi nume de UAT raman geografie.
    ("Primăria București a lansat licitația pentru modernizarea parcului", "local"),
    ("Curtea de Conturi București a finalizat controlul la trei primării", "local"),
])
def test_uat_fara_compusul_cunoscut_ramane_geografie(text, nivel):
    """Garda e strict pe prefixul masurat, nu pe nume. Altfel ar taia stirile reale din Alba
    si din Bucuresti — motivul pentru care ruta „baga ALBA in `_AMBIGUE`" a fost respinsa."""
    assert geo.clasifica(text) == nivel


def test_compusele_negeo_chiar_exista_in_index():
    """Un nume scris gresit in `_COMPUSE_NEGEO` n-ar da eroare — n-ar filtra nimic, tacut.
    Acelasi invariant ca la `_AMBIGUE`, din acelasi motiv."""
    index = geo._index()
    lipsa = sorted(n for n in geo._COMPUSE_NEGEO if n not in index)
    assert not lipsa, f"nume din _COMPUSE_NEGEO care nu sunt in indexul de UAT-uri: {lipsa}"


# ------------------------------------------------ regiuni folosite ca nume proprii compuse
# Aceeasi clasa cu `_AMBIGUE`, dar mecanismul TREBUIE sa fie altul, si asta e masurat pe tot
# corpusul (2026-08-03, 1714 articole): cerand o marca geografica se pierde un articol corect
# („Capitala DE Moldova") si cade „in REGIUNEA Banatului". Regiunile apar legitim fara
# prepozitie. Discriminatorul e cuvantul cu majuscula lipit inainte.
#
# Premisa cu care a pornit ancheta era doar pe jumatate adevarata si merita scris: din 9
# articole `regional` gresite, UNUL era marca comerciala (cazul-samanta de mai jos) si SASE
# erau statul vecin. Cine relaxeaza garda asta trebuie sa se uite intai la Republica Moldova.

@pytest.mark.parametrize("text", [
    "Banca Transilvania oferă reduceri la zborurile AnimaWings",
    "Grupul Banca Transilvania a lansat un nou parteneriat strategic",
    "Universitatea Transilvania a deschis înscrierile",
    "Republica Moldova instituie restricții și scumpește motorina",
    "Guvernul Republicii Moldova a instituit stare de alertă energetică",
    "Piața Agro Transilvania a fost închisă temporar",
    "Autostrada A3 Transilvania rămâne neterminată",
    "Festivalul Internațional de Film Transilvania începe vineri",
])
def test_regiunea_ca_nume_propriu_compus_nu_e_geografie(text):
    assert geo.clasifica(text) is None


@pytest.mark.parametrize("text", [
    "Prognoza meteo pentru Transilvania și zonele montane",
    "Transilvania a fost lovită de o furtună puternică",
    "Cod galben de caniculă emis pentru regiunea Oltenia",
    "Turiștii au ajuns în Banat la sfârșitul săptămânii",
])
def test_folosirea_geografica_a_regiunii_ramane_regional(text):
    assert geo.clasifica(text) == "regional"


@pytest.mark.parametrize("text", [
    "Toată Oltenia se află sub cod roșu de caniculă",
    "Regiunea Banatului a înregistrat cele mai mari temperaturi",
    "Nordul Banatului rămâne fără curent electric",
])
def test_substantivele_geo_relationale_nu_declanseaza_garda(text):
    """Whitelist-ul `_GEO_RELATIONAL`. Pe corpusul de azi niciunul dintre cele 10 cuvinte nu
    precede un nume de regiune, deci nu schimba nicio clasificare reala — exista ca sa nu se
    strice tocmai forma cea mai geografica cu putinta cand apare."""
    assert geo.clasifica(text) == "regional"


# ------------------------------------------------------- „Moldova" statul vs „Moldova" regiunea
# Ratarea pe care garda de mai sus o lasa in urma prin constructie: ea se uita la cuvantul lipit
# inainte, deci prinde „Republica Moldova" dar nu „Moldova" singur. Cele trei texte de mai jos
# sunt VERBATIM din corpus (2026-08-07) — erau singurele trei articole din 2704 a caror rubrica
# depindea de potrivirea pe nume, si toate trei erau gresite.

@pytest.mark.parametrize("text", [
    # marca in TITLU
    "Moldova și Ucraina iau măsuri pentru nivelul scăzut al Nistrului. "
    "Guvernele de la Chișinău și Kiev colaborează pentru strategii de urgență.",
    # marca abia in TEASER, la distanta — de-asta garda cauta in tot textul, nu intr-o fereastra
    "Premierul Vasile Tofan explică venirea delegației talibane în Moldova. "
    "Șeful guvernului de la Chișinău a declarat că instituțiile statului au tratat eronat cererile.",
    # marca doar la GENITIV: forma nearticulata „Republica Moldova" nu apare deloc in text
    "Maia Sandu avertizează asupra riscului unei crize de apă și energie în Moldova. "
    "Președinta Republicii Moldova a solicitat cetățenilor un consum responsabil.",
    "Alegerile parlamentare din Moldova au fost câștigate de partidul pro-european, "
    "potrivit rezultatelor anunțate la Chișinău.",
])
def test_statul_moldova_nu_primeste_rubrica_geografica_romaneasca(text):
    """Cad pe `None` si de acolo pe rubrica tematica. NU pe `extern` — ruta aia e inchisa de
    proprietar (IZZ-0137), iar testul asta nu o redeschide."""
    assert geo.clasifica(text) is None


@pytest.mark.parametrize("text", [
    "Cod galben de caniculă și disconfort termic în județele din Moldova",
    "Moldova a fost lovită de o furtună puternică în cursul nopții",
    "Prognoza meteo pentru Moldova și zonele montane din estul țării",
])
def test_regiunea_romaneasca_moldova_ramane_regional(text):
    """Fara marca de tara, garda nu are voie sa se declanseze — altfel ar taia exact rubrica
    pe care exista sa o apere. Astea sunt formele reale din corpus, nu sonde inventate."""
    assert geo.clasifica(text) == "regional"


def test_marca_de_tara_nu_fura_un_nivel_mai_specific_din_romania():
    """Cazul care ar fi trecut neobservat: textul are marca de tara, dar stirea se intampla
    intr-un loc din Romania. Garda respinge doar potrivirea pe „Moldova", nu clasificarea —
    `CEAHLAU` castiga si articolul ramane `local`. Verbatim din corpus."""
    text = ("Turist din Republica Moldova salvat de pe Ceahlău de către salvamontiști. "
            "Bărbatul de 41 de ani a fost preluat de echipajul din Neamț.")
    assert geo.clasifica(text) == "local"


@pytest.mark.parametrize("text", [
    "În Ardeal s-au înregistrat cele mai mari precipitații",
    "Turiștii au ajuns În Banat la sfârșitul săptămânii",
])
def test_prepozitia_locativa_cu_majuscula_nu_declanseaza_garda(text):
    """La inceput de fraza, „In" arata pentru garda exact ca „Banca": cuvant cu majuscula
    lipit inainte. De aceea garda intreaba si `_MARCA_GEO` inainte sa respinga. Regresia a
    fost prinsa de `test_clasificare`, care exista dinainte — nu de corpus, unde forma e rara.
    """
    assert geo.clasifica(text) == "regional"


@pytest.mark.xfail(reason="Conectorul cu litera mica trece de garda: garda cere un cuvant cu "
                          "MAJUSCULA lipit inainte, iar „de\" nu e asa. Masurat, „Gazeta de "
                          "Transilvania\" e singura aparitie de tipul asta din corpus, si "
                          "articolul ei e oricum `local`, deci impactul de azi e zero. "
                          "Pinuit ca sa nu treaca drept necunoscut.",
                   strict=True)
def test_conectorul_cu_litera_mica_trece_de_garda_INCA():
    assert geo.clasifica("Gazeta de Transilvania a publicat un articol despre buget") is None


@pytest.mark.xfail(reason="_ARTICOL nu acopera genitivul feminin: "
                          "„Transilvaniei\"/„Moldovei\"/„Olteniei\" nu se potrivesc deloc. "
                          "Impact zero pe corpusul de azi (cele 2 articole sunt deja `zonal` "
                          "din nume de judet), dar „nordul Transilvaniei\" e o formulare "
                          "frecventa in presa si e invizibila pentru poarta. Felie separata.",
                   strict=True)
def test_genitivul_feminin_al_regiunii_nu_se_potriveste_INCA():
    assert geo.clasifica("Nordul Transilvaniei rămâne fără curent") == "regional"


def test_garda_de_regiune_nu_atinge_celelalte_niveluri():
    """Garda se evalueaza DOAR pe potriviri `regional`. „Primăria Giurgiu" si „Universitatea
    Cluj" sunt exact tiparul pe care il respinge — cuvant cu majuscula inainte — si trebuie
    sa treaca neatinse, altfel poarta ar pierde masiv la zonal si local (masurat: 890 din
    1606 de potriviri din corpus n-au nicio marca)."""
    assert geo.clasifica("Primăria Giurgiu a semnat contractul") == "local"
    assert geo.clasifica("Universitatea Cluj a pierdut meciul") == "zonal"


def test_capitala_de_moldova_supravietuieste_gardei():
    """Regresia pe care mecanismul `_MARCA_GEO` ar fi produs-o daca era refolosit aici: „de"
    nu e prepozitie locativa, deci acel filtru ar fi taiat singurul articol din corpus in care
    `regional` era corect. Testul apara alegerea, nu doar rezultatul."""
    assert geo.clasifica(
        "Locomotivele circulă pe magistralele care conectează Capitala de Moldova "
        "și vestul țării") == "regional"


# --- badge-ul de pe coperta: judetul in locul categoriei (decizie proprietar 2026-08-04) ---

def test_badge_zonal_arata_judetul_cu_diacritice():
    """Cheia sursei da judetul, iar afisarea trece prin `eticheta_judet` — deci „Maramureș",
    nu „MARAMURES". Fara pasul asta badge-ul ar fi iesit fara diacritice pe coperta."""
    assert geo.judet_copertei({"category": "zonal", "source": "emaramures"}) == "Maramureș"


def test_badge_local_arata_judetul():
    assert geo.judet_copertei({"category": "local", "source": "bzi"}) == "Iași"


def test_badge_regional_ramane_pe_categorie_chiar_cu_judet_derivabil():
    """`regional` acopera mai multe judete: un badge de judet ar fi FALS, nu doar lipsa.
    Sursa de mai jos ARE judet derivabil — regula taie dupa categorie, nu dupa disponibilitate."""
    assert geo.judet_sursa("emaramures") == "MARAMURES"
    assert geo.judet_copertei({"category": "regional", "source": "emaramures"}) == ""


def test_badge_categoriile_negeografice_nu_iau_judet():
    """La `auto`/`sport`/`extern` locul nu e subiectul, desi sursa e un ziar judetean."""
    assert geo.judet_copertei({"category": "auto", "source": "alba24"}) == ""


def test_badge_fara_judet_derivabil_cade_pe_categorie():
    """40 din 435 `zonal` si 161 din 398 `local` n-au judet — acolo badge-ul ramane cum era."""
    assert geo.judet_copertei({"category": "local", "source": "sursa-inexistenta"}) == ""
    assert geo.judet_copertei({"category": "zonal"}) == ""
