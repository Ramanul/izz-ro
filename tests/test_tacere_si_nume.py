"""Două gărzi pe sinteza dialectică, din testul ca cititor pe live (8.11.2026).

Cazul real: „Donald l-a numit pe Stephen Miller șef de cabinet", 4 publicații care relatează
toate numirea, publicat drept „ireconciliabil" fiindcă modelul n-a listat niciun fapt comun și
sursele difereau doar la vârsta lui Miller (39 / 41). Titlul tăiase și numele de familie.

Ce fixează: (1) prenumele rămas singur în titlu amână articolul, cu reîncercare, dar nu și
instituțiile („Guvernul" din „Guvernul României") sau numele deja complete; (2) „ireconciliabil"
nu se publică la prima încercare când titlul e susținut propoziție cu propoziție de ≥2
publicații-origine; (3) o propoziție cu negație nu susține titlul — tăcerea legitimă rămâne;
(4) la a doua încercare tăcerea se publică, ca un cluster să nu fie reluat la nesfârșit.
"""
from generator import dialectic, process

CONTEXT_MILLER = ("Președintele american Donald Trump l-a numit joi pe Stephen Miller în funcția "
                  "de șef de cabinet. Potrivit unui oficial, Donald Trump a acceptat demisia lui Wiles.")


def test_prenumele_singur_e_nume_trunchiat():
    assert process._nume_trunchiat("Donald l-a numit pe Stephen Miller șef de cabinet",
                                   CONTEXT_MILLER) == "Donald Trump"


def test_numele_complet_sau_doar_familia_trec():
    assert process._nume_trunchiat("Donald Trump l-a numit pe Stephen Miller șef de cabinet",
                                   CONTEXT_MILLER) is None
    assert process._nume_trunchiat("Trump l-a numit pe Miller șef de cabinet", CONTEXT_MILLER) is None


def test_institutia_articulata_nu_e_prenume():
    ctx = ("Mâine, Guvernul României adoptă bugetul. Ministrul a spus că Guvernul României "
           "nu amână votul.")
    assert process._nume_trunchiat("Guvernul adoptă bugetul pe 2027", ctx) is None


def test_o_singura_aparitie_in_surse_nu_ajunge():
    ctx = "Președintele american Donald Trump a semnat decretul. Trump a plecat apoi la Miami."
    assert process._nume_trunchiat("Donald a semnat decretul", ctx) is None


def _bloc(propozitii: dict) -> dialectic.Block:
    surse = [dialectic.Source(idx=i, name=n, domain=f"{n.lower()}.ro", role=r, mode="text")
             for i, (n, r) in enumerate([("Alfa", "ROOT"), ("Beta", "INDEPENDENT_CONTRIBUTOR"),
                                         ("Gama", "CLONE")], start=1)]
    b = dialectic.Block(cid=0, text="", sources=surse)
    for cid, (nume, text) in propozitii.items():
        b.chunks[cid] = (frozenset({nume}), text)
    return b


TITLU = "Trump îl numește pe Stephen Miller la șefia cabinetului de la Casa Albă"


def test_titlul_sustinut_de_doua_origini():
    b = _bloc({"S1.1": ("Alfa", "Donald Trump l-a numit pe Stephen Miller șef de cabinet la Casa Albă."),
               "S2.1": ("Beta", "Stephen Miller a fost ales de Trump pentru șefia cabinetului, la Casa Albă."),
               "S1.2": ("Alfa", "Miller are 39 de ani."),
               "S2.2": ("Beta", "Miller are 41 de ani.")})
    assert process._origini_care_sustin_titlul(TITLU, b) == 2


def test_clona_nu_numara_ca_origine():
    b = _bloc({"S1.1": ("Alfa", "Donald Trump l-a numit pe Stephen Miller șef de cabinet la Casa Albă."),
               "S3.1": ("Gama", "Donald Trump l-a numit pe Stephen Miller șef de cabinet la Casa Albă.")})
    assert process._origini_care_sustin_titlul(TITLU, b) == 1


def test_negatia_nu_sustine_titlul():
    b = _bloc({"S1.1": ("Alfa", "Trump l-a numit pe Stephen Miller la șefia cabinetului de la Casa Albă."),
               "S2.1": ("Beta", "Trump nu l-a numit pe Stephen Miller la șefia cabinetului de la Casa Albă.")})
    assert process._origini_care_sustin_titlul(TITLU, b) == 1


def test_titlul_negativ_e_sustinut_de_propozitii_negative():
    titlu = "Guvernul nu va majora accizele la carburanți de la începutul anului"
    b = _bloc({"S1.1": ("Alfa", "Guvernul nu va majora accizele la carburanți de la începutul anului."),
               "S2.1": ("Beta", "Executivul a anunțat că nu va majora accizele la carburanți de la începutul anului.")})
    assert process._origini_care_sustin_titlul(titlu, b) == 2


def test_acronim_inainte_de_nume_conteaza_ca_mijloc_de_fraza():
    ctx = ("Mâine, președintele SUA Donald Trump vizitează Kievul. Liderul SUA Donald Trump "
           "a confirmat vizita.")
    assert process._nume_trunchiat("Donald vizitează Kievul mâine", ctx) == "Donald Trump"


def test_doua_puncte_despart_cuvinte_care_nu_formeaza_un_nume():
    assert process._nume_trunchiat("Casa Albă: Donald l-a numit pe Miller șef de cabinet",
                                   CONTEXT_MILLER) == "Donald Trump"


def test_la_a_doua_incercare_garda_de_nume_cedeaza():
    bloc = _bloc_miller()
    bloc.chunks["S1.3"] = (frozenset({"Alfa"}), "Potrivit presei, Donald Trump a acceptat demisia lui Wiles.")
    with dialectic.a_doua_incercare():
        out = process._aplica_dialectic(_rep(), _obj_tacere("Donald l-a numit pe Stephen Miller șef de cabinet"),
                                        bloc, _P())
    assert out is not None


def _obj_tacere(titlu):
    return {"title": titlu, "common_facts": [], "uncorroborated_claims": [],
            "divergences": [{"axis": "vârsta lui Miller", "positions": [
                {"claim": "Stephen Miller are 39 de ani.", "chunk_ids": ["S1.2"]},
                {"claim": "Stephen Miller are 41 de ani.", "chunk_ids": ["S2.2"]}]}]}


def _rep():
    return {"title": "x", "category": "extern", "sources": [], "original_link": "https://alfa.ro/1"}


def _bloc_miller():
    return _bloc({"S1.1": ("Alfa", "Donald Trump l-a numit pe Stephen Miller șef de cabinet la Casa Albă."),
                  "S2.1": ("Beta", "Stephen Miller a fost ales de Trump pentru șefia cabinetului, la Casa Albă."),
                  "S1.2": ("Alfa", "Stephen Miller are 39 de ani."),
                  "S2.2": ("Beta", "Stephen Miller are 41 de ani.")})


class _P:
    name = "fals"


def test_tacerea_cu_miez_comun_se_amana_la_prima_incercare():
    dialectic.reset_stats()
    rep = _rep()
    out = process._aplica_dialectic(rep, _obj_tacere(TITLU), _bloc_miller(), _P())
    assert out is None
    assert rep["_motiv_amanare"] == "tacere_miez_comun"
    assert "tacere_miez_comun" in process.MOTIVE_REINCERCABILE
    assert dialectic.stats().get("amanate_tacere_miez_comun") == 1


def test_la_a_doua_incercare_tacerea_se_publica():
    dialectic.reset_stats()
    with dialectic.a_doua_incercare():
        out = process._aplica_dialectic(_rep(), _obj_tacere(TITLU), _bloc_miller(), _P())
    assert out is not None
    assert out["dialectic"]["state"] == dialectic.STATE_SILENCE


def test_titlul_cu_prenume_singur_e_amanat_in_aplicare():
    rep = _rep()
    bloc = _bloc_miller()
    bloc.chunks["S1.3"] = (frozenset({"Alfa"}), "Potrivit presei, Donald Trump a acceptat demisia lui Wiles.")
    out = process._aplica_dialectic(rep, _obj_tacere("Donald l-a numit pe Stephen Miller șef de cabinet"),
                                    bloc, _P())
    assert out is None
    assert rep["_motiv_amanare"] == "titlu_nume_trunchiat"


def test_nota_de_reincercare_numeste_motivele_noi():
    for motiv in ("titlu_nume_trunchiat", "tacere_miez_comun"):
        nota = process._nota_reincercare(motiv, "Titlu respins")
        assert process._MESAJ_MOTIV[motiv] in nota
