"""Calculatorul de salariu, verificat contra TABELULUI din art. 77 Cod Fiscal.

De ce exista (2026-08-15): `static/calc-salariu.js` calcula deducerea personala cu
`Math.floor((brut - salariuMinim) / 50)`. Tabelul din art. 77 alin. (4) deschide insa fiecare
transa la +1 leu, nu la +0:

    salariul minim                          20,00%
    salariul minim + 1 leu   ... + 50 lei   19,50%
    salariul minim + 51 lei  ... + 100 lei  19,00%
    salariul minim + 101 lei ... + 150 lei  18,50%

Cu `floor`, un brut de „minim + 1 leu" primea 20,00% in loc de 19,50%: deducere prea mare,
impozit prea mic, net afisat prea mare. Cele doua formule coincid DOAR pe multiplii exacti de
50 de lei peste minim, deci greseala lovea 49 din 50 de valori posibile, pe un calculator
public. Sursa tabelului: https://www.noulcodfiscal.ro/titlu-4/capitol-3/articol-77.html

Testele NU reimplementeaza formula — aia ar fi circular, ar verifica copia contra copiei. Ele
EXTRAG blocul de calcul din fisierul .js livrat si il ruleaza in node, deci verifica exact
codul care ajunge in browserul cititorului.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

RADACINA = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALE_JS = os.path.join(RADACINA, "static", "calc-salariu.js")

# Salariul minim brut folosit in exemple. Nu e hardcodat in JS (vine din `data-salariu-minim`),
# deci testul il trimite explicit si nu se strica atunci cand se schimba minimul pe economie.
MINIM = 4325

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node lipseste; testul ruleaza JS-ul livrat, nu o copie")


def _sursa() -> str:
    with open(CALE_JS, "r", encoding="utf-8") as fh:
        return fh.read()


def _bloc_de_calcul() -> str:
    """Decupeaza din fisierul livrat exact codul care calculeaza taxele.

    Doua functii complete, fara DOM: `sumaNeimpozabila` (facilitatea OUG 89/2025) si
    `calculeaza` (CAS/CASS/deducere/impozit), de la prima pana la `return {...};` plus
    acolada de inchidere a lui `calculeaza`. Daca marcajele se schimba, testul cade
    zgomotos aici in loc sa treaca pe un bloc gresit."""
    m = re.search(
        r"(function sumaNeimpozabila.*?var net = brut - cas - cass - impozit;"
        r"\s*return \{[^}]*\};\s*\})",
        _sursa(), re.S)
    assert m, "nu am gasit blocul de calcul in calc-salariu.js — s-au schimbat marcajele"
    return m.group(1)


def _ruleaza(cazuri: list, tmp_path) -> list:
    """Ruleaza blocul real in node pentru fiecare (brut, salariuMinim, inPerioada)."""
    script = (
        _bloc_de_calcul() + "\n"
        + f"const cazuri = {json.dumps(cazuri)};\n"
        + "console.log(JSON.stringify(cazuri.map(c => calculeaza(c[0], c[1], c[2]))));\n"
    )
    cale = tmp_path / "harness.js"
    cale.write_text(script, encoding="utf-8")
    rez = subprocess.run(["node", str(cale)], capture_output=True, text=True, timeout=30)
    assert rez.returncode == 0, f"node a esuat: {rez.stderr}"
    return json.loads(rez.stdout)


# --- tabelul din lege, rand cu rand -------------------------------------------------------

# (brut, procentul din tabel) pentru zero persoane in intretinere.
TABEL = [
    (MINIM,        20.0),   # exact salariul minim
    (MINIM + 1,    19.5),   # prima transa se deschide la +1 leu, nu la +50
    (MINIM + 50,   19.5),   # ...si se inchide la +50
    (MINIM + 51,   19.0),   # a doua transa
    (MINIM + 100,  19.0),
    (MINIM + 101,  18.5),
    (MINIM + 150,  18.5),
    (MINIM + 2000,  0.0),   # plafonul de acordare: 40 de trepte a 0,5pp
]


@pytest.mark.parametrize("brut,procent", TABEL)
def test_deducerea_respecta_tabelul_din_lege(brut, procent, tmp_path):
    asteptat = round(MINIM * procent / 100)
    got = _ruleaza([[brut, MINIM]], tmp_path)[0]
    assert got["deducere"] == asteptat, (
        f"la brut={brut} (minim{brut - MINIM:+d}) tabelul cere {procent}% = {asteptat} lei, "
        f"codul da {got['deducere']} lei")


def test_floor_ar_pica_pe_deschiderea_transei(tmp_path):
    """Testul care prinde exact regresia reparata: `floor` da 20% la minim+1 leu.

    Daca cineva pune `Math.floor` la loc, testul de mai sus pica — asta il documenteaza."""
    got = _ruleaza([[MINIM + 1, MINIM]], tmp_path)[0]
    cu_floor = round(MINIM * 20 / 100)      # 865 — ce dadea codul vechi
    cu_ceil = round(MINIM * 19.5 / 100)     # 843 — ce cere tabelul
    assert got["deducere"] != cu_floor
    assert got["deducere"] == cu_ceil


def test_peste_plafon_deducerea_e_zero(tmp_path):
    got = _ruleaza([[MINIM + 2001, MINIM]], tmp_path)[0]
    assert got["deducere"] == 0


# --- art. 77 alin. (2): plafonul pe venitul impozabil -------------------------------------

def test_deducerea_nu_depaseste_venitul_impozabil(tmp_path):
    """Alin. (2): deducerea se acorda in limita venitului impozabil lunar realizat.

    Fara plafon, la brut=1000 se afisa „Deducere personala: 865 lei" peste un venit impozabil
    de 650 — randul se contrazicea cu cel de deasupra."""
    brut = 1000
    venit_impozabil = brut - round(brut * 0.25) - round(brut * 0.10)  # 650
    got = _ruleaza([[brut, MINIM]], tmp_path)[0]
    assert got["deducere"] <= venit_impozabil
    assert got["deducere"] == venit_impozabil


def test_baza_impozabila_nu_devine_negativa(tmp_path):
    got = _ruleaza([[1000, MINIM]], tmp_path)[0]
    assert got["baza"] >= 0
    assert got["impozit"] == 0


# --- coerenta interna ---------------------------------------------------------------------

def test_netul_scade_monoton_cu_brutul(tmp_path):
    """O treapta de deducere nu are voie sa faca netul sa scada cand brutul creste.

    Cazurile nu trimit `inPerioada` (falsy), deci verifica calea fara facilitatea OUG
    89/2025 — cea valabila in afara ferestrei legale sau peste minimul pe economie."""
    cazuri = [[MINIM + i, MINIM] for i in range(0, 401, 7)]
    rez = _ruleaza(cazuri, tmp_path)
    neturi = [r["net"] for r in rez]
    for i in range(1, len(neturi)):
        assert neturi[i] >= neturi[i - 1], (
            f"netul scade intre brut={cazuri[i-1][0]} ({neturi[i-1]}) si "
            f"brut={cazuri[i][0]} ({neturi[i]})")


def test_sursa_livrata_foloseste_ceil(tmp_path):
    """Garda de regresie pe sursa, nu pe rezultat: `floor` a fost aici o luna."""
    sursa = _sursa()
    assert "Math.ceil((brut - salariuMinim) / 50)" in sursa
    assert "Math.floor((brut - salariuMinim) / 50)" not in sursa


# --- facilitatea OUG 89/2025: 200 lei neimpozabili, 01.07 - 31.12.2026 ---------------------

def test_facilitatea_200_lei_la_salariul_minim(tmp_path):
    """Cazul eligibil, cifrele legii: 4.325 brut -> CAS 1.031, CASS 413, impozit 182,
    net 2.699 (fara facilitate: 2.616). Verificat contra estimarilor publicate la intrarea
    in vigoare (fgo.ro BI 06/2025, avocatnet.ro 1 iul 2026: ~2.699 lei net)."""
    got = _ruleaza([[MINIM, MINIM, True]], tmp_path)[0]
    assert got["neimpozabil"] == 200
    assert got["cas"] == 1031
    assert got["cass"] == 413
    assert got["impozit"] == 182
    assert got["net"] == 2699


def test_dupa_inchiderea_ferestrei_calculul_revine_la_regula_generala(tmp_path):
    """La 1 ianuarie 2027 facilitatea dispare: pagina nu are voie sa mai afiseze 2.699.
    Perioada e verificata la runtime (`inPerioadaFacilitate`), testul prinde exact traseul."""
    got = _ruleaza([[MINIM, MINIM, False]], tmp_path)[0]
    assert got["neimpozabil"] == 0
    assert got["net"] == 2616


def test_peste_salariul_minim_nicio_facilitate(tmp_path):
    """Dreptul e legat de salariul minim: un brut cu 1 leu peste minim nu primeste nimic."""
    got = _ruleaza([[MINIM + 1, MINIM, True]], tmp_path)[0]
    assert got["neimpozabil"] == 0


def test_sub_minim_suma_se_diminueaza_proportional(tmp_path):
    """Sub minim, suma se diminueaza proportional cu venitul realizat (estimare declarata
    in nota paginii): la jumatate din minim, 200 * 2162 / 4325 = 99,97 -> 100 lei."""
    got = _ruleaza([[MINIM // 2, MINIM, True]], tmp_path)[0]
    assert got["neimpozabil"] == 100


def test_grindul_legal_la_iesirea_din_facilitate(tmp_path):
    """La minim+1 leu suma neimpozabila dispare si netul POATE scada — discontinuitate din
    lege, nu bug de rotunjire. Testul o documenteaza ca atare."""
    inauntru = _ruleaza([[MINIM, MINIM, True]], tmp_path)[0]["net"]
    afara = _ruleaza([[MINIM + 1, MINIM, True]], tmp_path)[0]["net"]
    assert inauntru == 2699
    assert afara < inauntru


def test_monoton_in_interiorul_ferestrei_facilitatei(tmp_path):
    """Cu facilitatea activa, netul creste monoton cat timp brutul ramane sub minim."""
    cazuri = [[MINIM - 300 + i, MINIM, True] for i in range(0, 301, 7)]
    rez = _ruleaza(cazuri, tmp_path)
    neturi = [r["net"] for r in rez]
    for i in range(1, len(neturi)):
        assert neturi[i] >= neturi[i - 1], (
            f"netul scade sub facilitare intre brut={cazuri[i-1][0]} ({neturi[i-1]}) si "
            f"brut={cazuri[i][0]} ({neturi[i]})")
