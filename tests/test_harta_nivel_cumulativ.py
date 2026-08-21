"""Nivelurile hartii sunt CUMULATIVE, nu trei cutii disjuncte.

De ce exista (2026-08-20): `filtered()` din `static/harta-stiri/harta-stiri.js` compara
`geo_level` cu nivelul ales prin EGALITATE STRICTA. Dar `geo_level` e rubrica editoriala a
articolului (/local/, /judetean/, /regional/), nu o precizie geografica -- poarta acelasi nume,
nu promite acelasi lucru. Consecinta, masurata pe map.json v4 (488 de articole): doar 4 aveau
geo_level "regional", deci modul Regional afisa 4 stiri din 488 si 5 din 7 regiuni apareau
GOALE -- Muntenia 0 cu 78 de stiri in ea, Oltenia 2 din 25. Un selector numit "nivel geografic"
promite continere: cine alege Oltenia vrea tot ce s-a intamplat in Oltenia.

Regula corecta: pastreaza articolul daca nivelul lui e egal sau MAI FIN decat cel ales.
    regional (1) < judetean (2) < local (3)

Testul NU reimplementeaza regula -- aia ar verifica o copie contra altei copii. EXTRAGE
`LEVEL_RANK` si `matchesLevel` din fisierul .js livrat si le ruleaza in node, deci verifica
exact codul care ajunge in browserul cititorului. Acelasi tipar ca test_calc_salariu.py.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALE_JS = os.path.join(RADACINA, "static", "harta-stiri", "harta-stiri.js")

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node lipseste; testul ruleaza JS-ul livrat, nu o copie")


def _bloc_de_nivel() -> str:
    """Decupeaza din fisierul livrat tabelul de rang si predicatul de nivel.

    Daca marcajele se schimba, testul cade zgomotos aici in loc sa treaca pe alt bloc."""
    with open(CALE_JS, "r", encoding="utf-8") as fh:
        sursa = fh.read()
    rang = re.search(r"const LEVEL_RANK = \{[^}]*\};", sursa)
    assert rang, "nu am gasit LEVEL_RANK in harta-stiri.js - s-au schimbat marcajele"
    fn = re.search(r"function matchesLevel\(item, level\) \{[\s\S]*?\n  \}", sursa)
    assert fn, "nu am gasit matchesLevel in harta-stiri.js - s-au schimbat marcajele"
    return rang.group(0) + "\n" + fn.group(0)


def _ruleaza(cazuri: list, tmp_path) -> list:
    script = (
        _bloc_de_nivel() + "\n"
        + f"const cazuri = {json.dumps(cazuri)};\n"
        + "console.log(JSON.stringify(cazuri.map(c => matchesLevel(c[0], c[1]))));\n"
    )
    cale = tmp_path / "harness.js"
    cale.write_text(script, encoding="utf-8")
    rez = subprocess.run(["node", str(cale)], capture_output=True, text=True, timeout=30)
    assert rez.returncode == 0, f"node a esuat: {rez.stderr}"
    return json.loads(rez.stdout)


NIVELURI = ["all", "regional", "judetean", "local"]

# (articol, {nivel: vizibil}) - tabelul complet, 4 feluri de articol x 4 niveluri.
TABEL = [
    ({"geo_level": "regional"},
     {"all": True, "regional": True,  "judetean": False, "local": False}),
    ({"geo_level": "judetean"},
     {"all": True, "regional": True,  "judetean": True,  "local": False}),
    ({"geo_level": "local"},
     {"all": True, "regional": True,  "judetean": True,  "local": True}),
    # Rubricile fara nivel geografic raman in afara oricarui nivel, exact ca inainte.
    ({"geo_level": "extern", "category": "extern"},
     {"all": True, "regional": False, "judetean": False, "local": False}),
]


@pytest.mark.parametrize("articol,asteptat", TABEL, ids=[t[0].get("geo_level") for t in TABEL])
def test_tabelul_de_niveluri(articol, asteptat, tmp_path):
    cazuri = [[articol, nivel] for nivel in NIVELURI]
    obtinut = _ruleaza(cazuri, tmp_path)
    for nivel, real in zip(NIVELURI, obtinut):
        assert real is asteptat[nivel], (
            f"articol {articol} la nivelul {nivel}: asteptat {asteptat[nivel]}, obtinut {real}")


def test_continerea_e_stricta(tmp_path):
    """local in judetean in regional. Asta E promisiunea pe care egalitatea stricta o incalca."""
    articole = [{"geo_level": g} for g in ("regional", "judetean", "local")]
    cazuri = [[a, n] for n in ("regional", "judetean", "local") for a in articole]
    v = _ruleaza(cazuri, tmp_path)
    reg, jud, loc = v[0:3], v[3:6], v[6:9]
    for i in range(3):
        assert not (jud[i] and not reg[i]), "un articol vizibil la judetean lipseste de la regional"
        assert not (loc[i] and not jud[i]), "un articol vizibil la local lipseste de la judetean"
    assert sum(reg) == 3 and sum(jud) == 2 and sum(loc) == 1


def test_geo_level_lipsa_cade_pe_categorie(tmp_path):
    """Vechiul `item.geo_level || item.category` se pastreaza: datele mai vechi nu se strica."""
    obtinut = _ruleaza([[{"category": "local"}, "regional"],
                        [{"category": "local"}, "local"],
                        [{"category": "regional"}, "local"]], tmp_path)
    assert obtinut == [True, True, False]
