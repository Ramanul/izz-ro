"""Judetul dedus din NUMELE sursei — cele doua feluri in care gresea.

DE CE EXISTA (audit 2026-08-21, pe map.json cu 482 de articole):

1. `source_county()` cauta numele judetului ca SUBSIR in id-ul sursei. „jurnalulOLTeniei",
   „cronicaOLTeniei" si „stirileOLTeniei" contin literele OLT, deci tot ce publicau cele trei
   ziare de OLTENIA — o REGIUNE de cinci judete — ajungea in judetul Olt: Craiova (Dolj) de
   cinci ori, Rovinari si Termocentrala Turceni (Gorj), „Spitalul Regional Craiova". Singurul
   OLT corect era Caracal, care chiar e in Olt.

2. Chiar cu sursa corect identificata, judetul redactiei nu e judetul faptei: „Un sofer baut a
   lovit 12 masini cu un autobuz in Medias" venea de la alba24 si ajungea in ALBA, desi Medias
   e in Sibiu — unde acelasi eveniment era corect fixat de alte patru surse.

MASURAT A/B pe acelasi corpus: 12 articole mutate, toate 12 corecte, 0 scoase de pe harta,
0 aparute. `county_only` 95 -> 83, `coordinates` 380 -> 392.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("bhd", ROOT / "tools" / "build_harta_data.py")
bhd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bhd)

KEYS = ["ALBA", "ARAD", "BIHOR", "BRASOV", "CLUJ", "DOLJ", "GORJ", "MARAMURES",
        "OLT", "PRAHOVA", "SIBIU", "TIMIS"]

# by_name / points minimale, in forma pe care o construieste `read_siruta` + `load_locality_points`.
_LOCALITATI = [
    ("MEDIAS", "SIBIU", "143628"),
    ("CRAIOVA", "DOLJ", "054979"),
    ("ROVINARI", "GORJ", "081806"),
    ("SLATINA", "OLT", "125534"),
]
BY_NAME: dict[str, list[dict]] = {}
for _nume, _judet, _siruta in _LOCALITATI:
    BY_NAME.setdefault(_nume, []).append({"name": _nume, "county": _judet, "siruta": _siruta})
POINTS = {bhd.siruta_key(s): {"x": 1.0, "y": 2.0} for _, _, s in _LOCALITATI}


def _locate(**article):
    article.setdefault("category", "local")
    article.setdefault("slug", "test")
    return bhd.locate(article, KEYS, BY_NAME, POINTS)


# --- 1. numele regiunii nu e judet ------------------------------------------------

def test_numele_unei_regiuni_nu_produce_judet():
    """„Oltenia" e o regiune de cinci judete, nu judetul Olt."""
    for sursa in ("jurnalulolteniei", "cronicaolteniei", "stirileolteniei"):
        assert bhd.source_county(sursa, KEYS) is None, f"{sursa} nu are voie sa dea un judet"


def test_judetul_care_e_SI_regiune_nu_se_pierde():
    """MARAMURES e si regiune, si judet — mascarea regiunilor nu are voie sa-l inghita."""
    assert bhd.source_county("emaramures", KEYS) == "MARAMURES"


def test_sursele_cu_judet_real_in_nume_raman_neatinse():
    for sursa, judet in (("alba24", "ALBA"), ("bizbrasov", "BRASOV"),
                         ("criticarad", "ARAD"), ("gazetadecluj", "CLUJ")):
        assert bhd.source_county(sursa, KEYS) == judet


def test_stire_din_craiova_la_un_ziar_de_oltenia_ajunge_in_dolj():
    """Cazul complet: fara fix ajungea in OLT, fiindca sursa contine literele OLT."""
    item = _locate(source="jurnalulolteniei", processed_by="gemini",
                   title="Consiliul Local Craiova votează noul Plan Urbanistic General",
                   teaser="Ședința are loc săptămâna viitoare.")
    assert item["county"] == "DOLJ"
    assert item["locality"] == "CRAIOVA"


# --- 2. localitatea din text bate judetul redactiei --------------------------------

def test_localitate_neambigua_din_alt_judet_bate_judetul_sursei():
    """Cazul Medias: ziar din Alba, accident in Sibiu, niciun judet numit in text."""
    item = _locate(source="alba24", processed_by="gemini",
                   title="Un șofer băut a lovit 12 mașini cu un autobuz în Mediaș",
                   teaser="Patru persoane au fost rănite în accident.")
    assert item["county"] == "SIBIU", "judetul redactiei nu e judetul faptei"
    assert item["locality"] == "MEDIAS"
    assert item["confidence"] == "siruta", "judetul vine de la localitate, nu de la sursa"


def test_localitatea_din_judetul_sursei_nu_declanseaza_mutarea():
    """Cand textul numeste o localitate CHIAR din judetul sursei, nimic nu se schimba."""
    item = _locate(source="pr_olt", processed_by="gemini",
                   title="Lucrări la parcul central din Slatina", teaser="Termen: octombrie.")
    assert item["county"] == "OLT"
    assert item["locality"] == "SLATINA"


def test_sursa_oficiala_nu_e_mutata_de_o_localitate_din_text():
    """O primarie scrie despre teritoriul ei; alt oras din text e context, nu locul faptei."""
    item = _locate(source="pl_alba_oras_zlatna", processed_by="official",
                   title="Anunț de licitație pentru modernizarea drumului comunal",
                   teaser="Ofertele se depun la sediul primăriei; câștigătorul din Craiova.")
    assert item["county"] == "ALBA", "regula sursei oficiale ramane neatinsa"


def test_judetul_numit_in_text_ramane_mai_tare_decat_localitatea():
    """Cand textul numeste explicit un judet, el decide — nu se intra pe calea noua."""
    item = _locate(source="alba24", processed_by="gemini",
                   title="Investiții în județul Alba", teaser="Un furnizor din Mediaș a câștigat.")
    assert item["county"] == "ALBA"
