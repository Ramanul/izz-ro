"""Atribuirea judetului cand sursa si textul nu sunt de acord.

DE CE EXISTA (audit 2026-08-20): `tools/build_harta_data.py` facea `county = tc or sc`, adica
judetul numit in TEXT batea mereu judetul SURSEI. Pentru un site de stiri e corect — un ziar
regional relateaza si din judetele vecine. Pentru un anunt OFICIAL nu e: o primarie publica
despre teritoriul ei, iar alt oras numit in text e context.

Cazul care a scos-o la iveala, gasit de `tools/integration_check.py`: anuntul Primariei Ploiesti
despre restrictiile de la Stadionul „Ilie Oana" ajungea pe harta in BUCURESTI, fiindca teaserul
zice „FC Petrolul Ploiesti si Rapid Bucuresti".

MASURAT inainte de schimbare, pe 505 articole: sursa si textul diverg in 26 de cazuri, din care
24 la site-uri de stiri (unde textul e corect) si 2 la surse oficiale (ambele gresite).
Regula inversa, „sursa castiga mereu", ar fi stricat 24 de atribuiri ca sa repare 2.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("bhd", ROOT / "tools" / "build_harta_data.py")
bhd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bhd)


def _judet(article: dict, keys: set) -> str:
    """Reproduce decizia din `build_harta_data`, pe cele doua semnale."""
    text = " ".join(filter(None, [article.get("title"), article.get("teaser")]))
    sc = bhd.source_county(str(article.get("source") or ""), keys)
    tc = bhd.explicit_county(text, keys)
    oficial = article.get("processed_by") == "official"
    return (sc or tc) if oficial else (tc or sc)


KEYS = {"PRAHOVA", "BUCURESTI", "NEAMT", "BACAU", "OLT", "DOLJ"}


def test_anunt_oficial_ramane_in_judetul_institutiei():
    """Cazul Ilie Oana: primaria din Ploiesti, echipa oaspete din Bucuresti."""
    a = {
        "source": "pl_prahova_municipiul_ploiesti",
        "processed_by": "official",
        "title": "Restricții de circulație în zona Stadionului „Ilie Oană”",
        "teaser": "Primăria Municipiului Ploiești informează că, pentru partida dintre "
                  "FC Petrolul Ploiești și Rapid București, vor fi instituite restricții.",
    }
    assert _judet(a, KEYS) == "PRAHOVA", "un oras pomenit in text nu muta anuntul primariei"


def test_site_de_stiri_urmeaza_TEXTUL_nu_judetul_redactiei():
    """Un ziar de OLTENIA care scrie despre Dolj ramane atribuit corect la Dolj.

    „Jurnalul Olteniei" acopera o REGIUNE de cinci judete, nu judetul Olt. Pana la
    auditul din 2026-08-21 `source_county()` ii scotea OLT din numele sursei, ca subsir;
    vezi `test_harta_judet_din_sursa.py`. Aici asertiunea tine si azi, dar din alt motiv:
    textul numeste explicit Dolj, iar `tc` bate `sc` la presa.
    """
    a = {
        "source": "jurnalulolteniei",
        "processed_by": "gemini",
        "title": "AJPIS Dolj virează peste 13 milioane de lei",
        "teaser": "Agenția Județeană pentru Plăți și Inspecție Socială Dolj a virat sumele.",
    }
    assert _judet(a, KEYS) == "DOLJ", "regula pentru oficiale nu are voie sa atinga presa"


def test_oficial_fara_judet_in_text_ramane_pe_sursa():
    a = {"source": "pl_neamt_municipiul_roman", "processed_by": "official",
         "title": "Anunț promovare grad profesional", "teaser": "Primăria organizează examen."}
    assert _judet(a, KEYS) == "NEAMT"


def test_stire_fara_judet_de_sursa_ramane_pe_text():
    a = {"source": "digi24", "processed_by": "gemini",
         "title": "Accident pe DN1", "teaser": "Evenimentul a avut loc în județul Prahova."}
    assert _judet(a, KEYS) == "PRAHOVA"
