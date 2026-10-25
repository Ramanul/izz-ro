"""Primăriile din județele bilingve (`ro_hu`) chiar ajung pe site.

DE CE EXISTA (2026-10-24). Pe 2026-09-06, sursele oficiale din cele 8 județe cu populație
maghiară au primit `lang="ro_hu"`, ca garda lingvistică să nu mai carantineze anunțuri
maghiare legitime. Calea oficială (fără AI) sărea însă orice sursă cu `source_lang != "ro"`,
deci TOATE cele 101 surse au dispărut: 0 articole din ele în starea din 24.10.2026, față de
1348 din cele 445 de surse oficiale `ro`. Pe o probă reală (dry-run, 24.10) erau 37 din cele
46 de amânări ale rulării — „oficial_sarit", repetat la fiecare rulare.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator import config  # noqa: E402
from generator.process import process_official  # noqa: E402


def _item(titlu, descriere=""):
    link = "https://www.targu-mures.ro/anunt"
    return {"source": "pl_mures_municipiul_targu_mures", "source_name": "Primăria Târgu Mureș",
            "source_lang": "ro_hu", "original_title": titlu, "title": titlu,
            "description": descriere, "src_extra": 0, "category": "local",
            "url": link, "original_link": link,
            "published": "2026-10-24T09:00:00+00:00", "model": None}


def test_anunt_in_romana_din_sursa_bilingva_se_publica():
    out = process_official([_item("Anunț privind închiderea circulației pe strada Mihai Viteazul")])
    assert len(out) == 1 and out[0]["processed_by"] == "official"


def test_anunt_bilingv_se_publica():
    out = process_official([_item("Hirdetmény / Anunț: ședința consiliului local")])
    assert len(out) == 1


def test_anunt_exclusiv_maghiar_se_sare_fara_traducere():
    assert process_official([_item("Közlemény a városi tanács üléséről és a határozatokról")]) == []


def test_sursele_ro_hu_oficiale_exista_si_trec_prin_calea_asta():
    """Premisa testelor de mai sus: sursele `ro_hu` sunt chiar oficiale, deci intră aici."""
    oficiale = [k for k, v in config.SOURCES.items() if v.get("lang") == "ro_hu"]
    assert oficiale and all(k.startswith(("pl_", "cj_", "pr_")) for k in oficiale)
