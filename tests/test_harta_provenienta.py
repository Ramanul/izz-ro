"""Proveniența relatărilor pe hartă — decizia IZZ-0433 (17 oct 2026).

Harta rămâne colorată după LOCUL știrii; în panoul județului se spune din ce presă vin
relatările (locală / alt județ / fără județ de sediu) și despre ce alte județe a scris presa
județului. A doua culoare pe hartă („știri din județ" vs. „pentru județ") a fost respinsă pe
măsurătoare: 4,1% din relatări trec dintr-un județ în altul, iar „pleacă" e nenul în 9 din 42.

Testul EXTRAGE blocul `provenienta` din fișierul .js livrat și îl rulează în node, ca
test_harta_nivel_cumulativ.py: verifică exact codul care ajunge la cititor, nu o copie.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CALE_JS = ROOT / "static" / "harta-stiri" / "harta-stiri.js"

_spec = importlib.util.spec_from_file_location("bhd_prov", ROOT / "tools" / "build_harta_data.py")
bhd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bhd)

ARTICOLE = [
    # despre Covasna: 1 presa locala, 3 din Brasov, 1 nationala
    {"county": "COVASNA", "source_county": "COVASNA"},
    {"county": "COVASNA", "source_county": "BRASOV"},
    {"county": "COVASNA", "source_county": "BRASOV"},
    {"county": "COVASNA", "source_county": "BRASOV"},
    {"county": "COVASNA", "source_county": ""},
    # presa din Brasov despre Brasov si despre Mures
    {"county": "BRASOV", "source_county": "BRASOV"},
    {"county": "MURES", "source_county": "BRASOV"},
    # sursa nationala fara campul deloc (date mai vechi): nu e „alt judet"
    {"county": "MURES"},
]


def _ruleaza(apeluri: str, tmp_path) -> dict:
    sursa = CALE_JS.read_text(encoding="utf-8")
    bloc = re.search(r"// --- provenienta \(inceput\) ---[\s\S]*?// --- provenienta \(sfarsit\) ---", sursa)
    assert bloc, "nu am gasit blocul `provenienta` in harta-stiri.js - s-au schimbat marcajele"
    script = (bloc.group(0) + f"\nconst items = {json.dumps(ARTICOLE)};\n" + apeluri)
    cale = tmp_path / "harness.js"
    cale.write_text(script, encoding="utf-8")
    rez = subprocess.run(["node", str(cale)], capture_output=True, text=True, timeout=30)
    assert rez.returncode == 0, f"node a esuat: {rez.stderr}"
    return json.loads(rez.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node lipseste; testul ruleaza JS-ul livrat")
def test_provenienta_pe_trei_grupe(tmp_path):
    r = _ruleaza("const p = provenienta(items, 'COVASNA');"
                 "console.log(JSON.stringify({total: p.total, locala: p.locala, fara: p.fara,"
                 " alte: descrescator(p.alteJudete)}));", tmp_path)
    assert r == {"total": 5, "locala": 1, "fara": 1, "alte": [["BRASOV", 3]]}


@pytest.mark.skipif(shutil.which("node") is None, reason="node lipseste; testul ruleaza JS-ul livrat")
def test_plecate_numara_doar_alte_judete(tmp_path):
    r = _ruleaza("console.log(JSON.stringify({bv: descrescator(plecate(items, 'BRASOV')),"
                 " cv: descrescator(plecate(items, 'COVASNA')), gol: descrescator(plecate(items, null))}));",
                 tmp_path)
    assert r["bv"] == [["COVASNA", 3], ["MURES", 1]], "Brasov->Brasov nu e o stire „plecata"
    assert r["cv"] == [] and r["gol"] == []


@pytest.mark.skipif(shutil.which("node") is None, reason="node lipseste; testul ruleaza JS-ul livrat")
def test_sursa_fara_camp_nu_e_alt_judet(tmp_path):
    r = _ruleaza("const p = provenienta(items, 'MURES');"
                 "console.log(JSON.stringify({fara: p.fara, alte: descrescator(p.alteJudete)}));", tmp_path)
    assert r == {"fara": 1, "alte": [["BRASOV", 1]]}


def test_datele_poarta_judetul_redactiei_separat_de_al_faptei():
    """bizbrasov scrie despre Zalan (Covasna): stirea sta in COVASNA, redactia ramane BRASOV."""
    keys = list(bhd.load_json(bhd.MAP).get("judete") or {})
    _, by_name, parents = bhd.read_siruta({bhd.norm(k): k for k in keys})
    article = {"category": "local", "slug": "t", "source": "bizbrasov", "processed_by": "gemini",
               "title": "O femeie a fost atacată de urs pe o stradă din satul Zălan, județul Covasna",
               "teaser": ""}
    item = bhd.locate(article, keys, by_name, bhd.load_locality_points(), bhd.load_uat_ids(), parents)
    assert item["county"] == "COVASNA"
    assert item["source_county"] == "BRASOV"
    national = bhd.locate({**article, "source": "digi24"}, keys, by_name, bhd.load_locality_points(),
                          bhd.load_uat_ids(), parents)
    assert national["county"] == "COVASNA" and national["source_county"] == ""


def test_panoul_de_provenienta_exista_in_pagina():
    pagina = (ROOT / "static" / "harta-stiri" / "index.html").read_text(encoding="utf-8")
    assert 'id="panel-provenance"' in pagina
