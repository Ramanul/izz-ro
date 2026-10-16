"""Plasari gresite pe /harta/ confirmate pe live (map.json din 2026-10-16) — regresii.

Doua cauze, in `tools/build_harta_data.py`:
1. `source_county()` ignora judetul DECLARAT in `config.SOURCES` (bihon -> BIHOR etc.), deci 14
   din 20 de ziare judetene erau tratate ca surse fara judet;
2. fara judet, castiga localitatea cu numele cel mai LUNG din text, fara context: strada
   Decebal bate „Primaria Giroc", „ferestrelor" -> Ferestre (DAMBOVITA), primarul Baluta ->
   comuna Baluta (MEHEDINTI).

Textele sunt cele reale din `data/articles.json` (titlu + teaser), cu SIRUTA reala: un set
sintetic de cinci localitati n-ar fi prins nimic din ce a stricat harta.
Cazul Vanatori: judetul e lasat liber (None), doar MEHEDINTI e interzis.
"""
from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("bhd_ctx", ROOT / "tools" / "build_harta_data.py")
bhd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bhd)


@lru_cache(maxsize=1)
def _geo():
    keys = list(bhd.load_json(bhd.MAP).get("judete") or {})
    _, by_name, parents = bhd.read_siruta({bhd.norm(k): k for k in keys})
    return keys, by_name, bhd.load_locality_points(), bhd.load_uat_ids(), parents


def _locate(source, title, teaser):
    keys, by_name, points, uat_ids, parents = _geo()
    article = {"category": "local", "slug": "t", "source": source, "processed_by": "gemini",
               "title": title, "teaser": teaser}
    return bhd.locate(article, keys, by_name, points, uat_ids, parents)


CAZURI = [
    ('ziuadevest',
     'Primăria Giroc pregătește cinci străzi pentru asfaltare',
     'Administrația locală din Giroc a demarat lucrările de infrastructură rutieră și profilare a carosabilului pe străzile Remus, Decebal, Bucegi, Piersicului și Oltului, în vederea asfaltării.',
     'TIMIS', 'GIROC'),
    ('bihon',
     'Lucrările la noul spital din Oradea avansează prin montarea instalațiilor',
     'Proiectul noii unități medicale din Oradea a depășit faza de structură, fiind deja instalate sute de ferestre, zeci de kilometri de cabluri electrice și mii de metri pătrați de tubulatură tehnică.',
     'BIHOR', None),
    ('opiniatm',
     'UPT și Teatrul Național Timișoara încheie un parteneriat strategic',
     'Universitatea Politehnica Timișoara și Teatrul Național „Mihai Eminescu” au oficializat o colaborare pe termen lung menită să conecteze mediul academic tehnic cu cel cultural.',
     'TIMIS', None),
    ('b365',
     'Locatarii din Berceni cer intervenția primarului Băluță după ce un foișor a fost ocupat de oameni fără adăpost',
     'Locuitorii unui bloc de pe strada Șura Mare din Sectorul 4 solicită măsuri urgente primarului Daniel Băluță, acuzând că zona din jurul unui foișor a devenit loc de adăpost pentru numeroase persoane.',
     'BUCURESTI', None),
    ('ziuadevest',
     'Municipiul Lugoj a primit trei autobuze noi printr-un parteneriat local',
     'Administrația locală din Lugoj, condusă de primarul Călin Dobra, a preluat în parcul auto trei autobuze achiziționate în cooperare cu comuna Coșteiu pentru extinderea transportului public.',
     'TIMIS', 'LUGOJ'),
    ('bihon',
     'Primăria Oradea explică lucrările de remediere din Parcul Brătianu',
     'Locuitorii din Oradea au criticat calitatea lucrărilor recente din Parcul I.C. Brătianu, modernizat cu fonduri de 4,5 milioane de euro. Reprezentanții primăriei au precizat că intervențiile actuale reprezintă remedieri solicitate pentru remedierea unor neconformități.',
     'BIHOR', None),
    ('newsbv',
     'Brigada 2 Vânători de Munte execută exercițiul militar SARMIS 26',
     'În perioada 17-30 octombrie 2026, militarii din Brigada 2 Vânători de Munte „Sarmizegetusa” desfășoară un amplu exercițiu tactic în mai multe poligoane pentru creșterea capacității de reacție operativă.',
     None, None),
    ('zcj',
     'IRUM Reghin lansează un nou tractor forestier la München',
     'Compania românească deținută de familia Oltean își extinde prezența internațională prin prezentarea unui utilaj forestier multifuncțional proiectat și fabricat în Transilvania.',
     'MURES', 'REGHIN'),
    ('mytex',
     'Uzina IAR Ghimbav va fi inclusă în noul Grup Aeronautic Național creat de Guvern',
     'Producătorul aeronautic din Brașov va intra într-o structură administrativă unificată, conform programului de guvernare 2026-2028. Noua entitate urmărește dezvoltarea industriei de aviație civilă și militară din România.',
     'BRASOV', 'GHIMBAV'),
]


@pytest.mark.parametrize("source,title,teaser,judet,localitate", CAZURI,
                         ids=[c[1][:40] for c in CAZURI])
def test_plasare_pe_harta(source, title, teaser, judet, localitate):
    item = _locate(source, title, teaser)
    assert item is not None, title
    if judet:
        assert item["county"] == judet, (item["county"], item["locality"])
    else:
        assert item["county"] != "MEHEDINTI", (item["county"], item["locality"])
    if localitate:
        assert item["locality"] == localitate, (item["county"], item["locality"])


def test_marca_de_strada_si_de_persoana_nu_fac_un_loc():
    padded = " PRIMARIA GIROC PREGATESTE STRADA DECEBAL CU PRIMARULUI DANIEL BALUTA "
    assert bhd._marca("GIROC", padded) == 2
    assert bhd._marca("DECEBAL", padded) == -2
    # a doua mentiune fara marca nu spala prima, care e clar o persoana
    assert bhd._marca("BALUTA", " PRIMARULUI BALUTA SI PRIMARULUI DANIEL BALUTA ") == -2


def test_cuvantul_comun_scris_cu_litera_mica_nu_e_nume_propriu():
    cased = bhd.plat_cu_majuscule("după ce un foișor a fost demolat în Berceni")
    assert not bhd._ca_nume_propriu("FOISOR", cased)
    assert bhd._ca_nume_propriu("BERCENI", cased)
    # textele oficiale scrise integral cu majuscule raman nume proprii
    assert bhd._ca_nume_propriu("HUSI", bhd.plat_cu_majuscule("SUCURSALA HUŞI ANUNȚĂ"))
