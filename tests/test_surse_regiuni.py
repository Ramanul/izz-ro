"""Gruparea /surse/ pe regiune istorica > judet (decizia ownerului 2026-08-02: 7 regiuni).

Regula care conteaza: nicio sursa nu dispare din catalog. Gruparea e o REORGANIZARE a
afisarii, nu un filtru — daca un judet nu se poate deduce, sursa ramane in lista plata.
"""
from generator import config, geo
from generator.render import _grupeaza_pe_regiuni, _source_catalog


def test_judetul_se_deduce_din_cheia_sursei():
    assert geo.judet_din_cheie("cj_cluj") == "CLUJ"
    assert geo.judet_din_cheie("pr_buzau") == "BUZAU"
    # judete din doua cuvinte: potrivirea trebuie sa fie pe numele cel mai lung
    assert geo.judet_din_cheie("pl_bistrita_nasaud_municipiul_bistrita") == "BISTRITA-NASAUD"
    assert geo.judet_din_cheie("pl_satu_mare_oras_ardud") == "SATU MARE"
    assert geo.judet_din_cheie("pl_caras_severin_oras_bocsa") == "CARAS-SEVERIN"


def test_sursele_fara_judet_in_cheie_raman_negrupate():
    """Ziarele nu codeaza un judet — nu trebuie sa fie inventat unul pentru ele."""
    for cheie in ("zcj", "bzi", "digi24", "protv", ""):
        assert geo.judet_din_cheie(cheie) is None


def test_sapte_regiuni_de_afisare_crisana_si_maramures_la_transilvania():
    assert len(geo.ORDINE_REGIUNI_AFISARE) == 7
    assert geo.regiune_afisare("BIHOR") == "TRANSILVANIA"      # Crisana comasata
    assert geo.regiune_afisare("MARAMURES") == "TRANSILVANIA"  # Maramures comasat
    assert geo.regiune_afisare("SUCEAVA") == "BUCOVINA"        # Bucovina ramane separata
    assert geo.regiune_afisare("TULCEA") == "DOBROGEA"
    assert geo.regiune_afisare("JUDET-INEXISTENT") is None


def test_clasificarea_articolelor_ramane_pe_noua_regiuni():
    """Comasarea e DOAR pentru afisare; `REGIUNI` alimenteaza clasificarea si nu se atinge."""
    assert "CRISANA" in geo.REGIUNI and "MARAMURES" in geo.REGIUNI
    assert geo.clasifica("Autoritatile din Crisana au anuntat masuri") == "regional"


def test_etichetele_judetelor_au_diacritice():
    assert geo.eticheta_judet("BISTRITA-NASAUD") == "Bistrița-Năsăud"
    assert geo.eticheta_judet("CARAS-SEVERIN") == "Caraș-Severin"
    assert geo.eticheta_judet("VALCEA") == "Vâlcea"
    assert geo.eticheta_judet("BUCURESTI") == "București"
    assert geo.eticheta_judet(None) == ""


def test_arborele_pastreaza_ordinea_si_numara_corect():
    arbore = _grupeaza_pe_regiuni({
        "CLUJ": {"with_stats": [{"name": "A"}], "without_stats": [{"name": "B"}]},
        "TULCEA": {"with_stats": [], "without_stats": [{"name": "C"}]},
        "ALBA": {"with_stats": [], "without_stats": [{"name": "D"}]},
    })
    assert [r["label"] for r in arbore] == ["Transilvania", "Dobrogea"]
    transilvania = arbore[0]
    assert transilvania["count"] == 3
    assert [c["label"] for c in transilvania["counties"]] == ["Alba", "Cluj"]  # alfabetic


def test_un_judet_necunoscut_nu_pierde_sursa():
    arbore = _grupeaza_pe_regiuni({
        "JUDET-INVENTAT": {"with_stats": [], "without_stats": [{"name": "X"}]},
    })
    assert arbore and arbore[-1]["label"] == "Alte județe"
    assert arbore[-1]["count"] == 1


def test_catalogul_nu_pierde_nicio_sursa():
    catalog, total, _ = _source_catalog([])
    assert total == len(config.SOURCES)
    numarate = 0
    for g in catalog:
        numarate += len(g["with_stats"]) + len(g["without_stats"])
        for r in g.get("regions", []):
            for c in r["counties"]:
                numarate += len(c["with_stats"]) + len(c["without_stats"])
    assert numarate == total


def test_primariile_chiar_ajung_in_arbore_nu_in_lista_plata():
    catalog, _, _ = _source_catalog([])
    local = next(g for g in catalog if g["key"] == "local")
    assert local["regions"], "sursele locale trebuie grupate pe regiuni"
    assert not local["without_stats"], "nicio primarie nu trebuie sa ramana negrupata"
