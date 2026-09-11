"""Garda registrului de protectii (`specs/audit-unificat.tsv`).

Testele pozitive verifica registrul comis. Cele negative verifica GARDA: fiecare regula
primeste un rand construit anume ca s-o incalce, pentru ca o gardă care nu e vazuta
respingand nimic e indistinguibila de una moarta — chiar lectia mecanismului #32, unde un
audit intreg a inventariat ca poarta activa o ramura nemergeuita.
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools import audit_matrice as am  # noqa: E402


@pytest.fixture(scope="module")
def randuri() -> list[dict]:
    return am.citeste()


def test_registrul_comis_e_curat(randuri):
    assert am.verifica(randuri) == []


def test_unealta_iese_zero_pe_registrul_comis():
    rez = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "audit_matrice.py"), "verifica"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert rez.returncode == 0, rez.stdout + rez.stderr


def test_raportul_ruleaza():
    rez = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "audit_matrice.py"), "raport"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert rez.returncode == 0, rez.stdout + rez.stderr
    assert "mecanisme_vii" in rez.stdout


def test_fiecare_dovada_e_o_cale_reala(randuri):
    """Legatura registru -> repo. Fara ea registrul descrie un sistem care poate sa nu existe."""
    for r in randuri:
        for cale in am._cai(r):
            assert os.path.exists(os.path.join(ROOT, cale)), f"#{r['id']}: {cale} lipseste"


def test_tsv_are_acelasi_numar_de_coloane_pe_toate_randurile():
    with open(am.TSV, encoding="utf-8", newline="") as fh:
        randuri = list(csv.reader(fh, delimiter="\t"))
    latimi = {len(r) for r in randuri if r}
    assert latimi == {len(am.COLOANE)}, f"latimi neuniforme: {sorted(latimi)}"


def test_vocabularul_e_ascii_fara_diacritice():
    """Clasa de bug care a stricat Dashboard-ul original: `Ridicata` si `Ridicată` numarate
    ca doua valori distincte, deci 'Prioritate P0: 1' cand randurile marcate erau 2."""
    for camp, valori in am.VOCAB.items():
        for v in valori:
            assert v.isascii(), f"{camp}: valoarea {v!r} are diacritice"


def test_agregatele_se_calculeaza_din_date(randuri):
    ag = am.agregate(randuri)
    assert ag["mecanisme_in_registru"] == len(randuri)
    assert ag["mecanisme_vii"] + ag["mecanisme_absente"] == len(randuri)
    assert (
        ag["autoritate_efectiva"] + ag["autoritate_conditionata"] + ag["fara_autoritate"]
        == ag["mecanisme_vii"]
    )
    assert ag["fail_inchis"] + ag["fail_deschis"] == ag["mecanisme_vii"]


def test_fantoma_ramane_consemnata_ca_absenta(randuri):
    """#32 e singurul mecanism inventariat de auditul din 2026-09-05 care nu exista pe main.
    Randul ramane in registru DELIBERAT: sters, s-ar reinventaria la urmatorul audit."""
    fantoma = next(r for r in randuri if r["id"] == "32")
    assert fantoma["stare"] == "absent"
    assert fantoma["autoritate"] == "niciuna"
    assert int(fantoma["eroziune"]) == 0


def _rand_valid(**override) -> dict:
    baza = {
        "id": "99", "categorie": "guard", "mecanism": "test", "dovada": "generator/guard.py",
        "pozitie": "fetch", "poate_bloca": "da", "autoritate": "efectiva",
        "conditie_autoritate": "-", "mod": "preventiv", "esec": "inchis", "bypass": "nu",
        "eroziune": "1", "risc": "2", "stare": "activ", "nota": "rand de test",
    }
    return baza | override


def test_randul_de_referinta_chiar_trece():
    assert am.verifica([_rand_valid()]) == []


@pytest.mark.parametrize(
    "override,fragment",
    [
        ({"categorie": "inventata"}, "vocabularului"),
        ({"stare": "Activă"}, "vocabularului"),
        ({"eroziune": "7"}, "nu e intreg 0-5"),
        ({"dovada": "generator/nu_exista_asa_ceva.py"}, "dovada inexistenta"),
        ({"poate_bloca": "nu", "autoritate": "efectiva"}, "nu are autoritate"),
        ({"esec": "deschis"}, "fail-open nu opreste nimic"),
        ({"autoritate": "conditionata"}, "fara conditie_autoritate"),
        ({"conditie_autoritate": "ceva"}, "conditie_autoritate completata"),
        ({"stare": "absent"}, "inca declarat ca blocheaza"),
        ({"nota": "  "}, "nota goala"),
    ],
)
def test_garda_prinde_incalcarea(override, fragment):
    probleme = am.verifica([_rand_valid(**override)])
    assert any(fragment in p for p in probleme), f"{override} a trecut nedetectat: {probleme}"


def test_garda_prinde_id_duplicat():
    probleme = am.verifica([_rand_valid(), _rand_valid()])
    assert any("id duplicat" in p for p in probleme)


def test_mecanism_absent_cu_eroziune_e_respins():
    """Contradictia din matricea originala: mecanismul inexistent avea eroziune 4, cea mai
    mare din tot inventarul, si genera o actiune P0."""
    probleme = am.verifica([
        _rand_valid(stare="absent", poate_bloca="nu", autoritate="niciuna", eroziune="4")
    ])
    assert any("nu are ce eroda" in p for p in probleme)


# --- subcomanda `eroziune` -------------------------------------------------------------
#
# Garda esentiala de aici nu e „ruleaza", ci CONTRACTUL dintre ce declara unealta ca poate
# masura si ce raporteaza efectiv. Prima versiune a subcomenzii declara „duplicare" drept
# dimensiune masurata si emitea semnale pe ea, desi proxy-ul folosit (fisier de dovada comun)
# marca 20+ din 44 de mecanisme — zgomot, nu masuratoare. Corectia a fost facuta de mana;
# testul de mai jos o face mecanica, ca sa nu se poata reintroduce tacut.


def _sintetic(rid, dovada, *, poate_bloca="nu", autoritate="niciuna", bypass="nu",
              stare="activ"):
    return {"id": rid, "mecanism": f"mecanism {rid}", "dovada": dovada, "stare": stare,
            "poate_bloca": poate_bloca, "autoritate": autoritate, "bypass": bypass}


def test_dimensiunile_sunt_opt_si_fiecare_e_etichetata():
    assert len(am.DIMENSIUNI) == 8
    for nume, text in am.DIMENSIUNI.items():
        assert text.split(" ")[0] in ("MASURAT", "INDICATOR", "NEMASURAT"), nume


def test_nicio_dimensiune_declarata_nemasurata_nu_apare_ca_semnal(randuri):
    """Contractul: ce e declarat NEMASURAT nu are voie sa produca semnale."""
    nemasurate = [n for n, t in am.DIMENSIUNI.items() if t.startswith("NEMASURAT")]
    assert nemasurate, "testul ar fi vid daca toate ar fi masurate"
    for date in am.eroziune(randuri).values():
        for semnal in date["semnale"]:
            eticheta = semnal.split(":")[0].strip()
            assert eticheta not in nemasurate, (
                f"semnalul {semnal!r} raporteaza dimensiunea {eticheta!r}, declarata NEMASURAT"
            )


def test_eroziunea_nu_produce_scor_compozit(randuri):
    """Deliberat: un numar unic ar insuma cu zero patru dimensiuni necitibile din repo."""
    for date in am.eroziune(randuri).values():
        assert set(date) == {"mecanism", "semnale", "zile_de_la_ultima_atingere"}
        assert not isinstance(date.get("scor"), (int, float))


def test_semnalul_de_autoritate_e_derivat_din_registru(randuri):
    asteptat = {r["id"] for r in randuri if r["stare"] != "absent"
                and r["poate_bloca"] == "da" and r["autoritate"] != "efectiva"}
    obtinut = {rid for rid, d in am.eroziune(randuri).items()
               if any(s.startswith("autoritate:") for s in d["semnale"])}
    assert obtinut == asteptat


def test_semnalul_de_bypass_e_derivat_din_registru(randuri):
    asteptat = {r["id"] for r in randuri if r["stare"] != "absent" and r["bypass"] == "da"}
    obtinut = {rid for rid, d in am.eroziune(randuri).items()
               if any(s.startswith("bypass:") for s in d["semnale"])}
    assert obtinut == asteptat


def test_mecanismele_absente_nu_apar_in_eroziune(randuri):
    absente = {r["id"] for r in randuri if r["stare"] == "absent"}
    assert absente, "registrul trebuie sa pastreze mecanismul fantoma"
    assert not (absente & set(am.eroziune(randuri)))


def test_granularitatea_grupeaza_doar_dovezi_identice():
    """Falsul pozitiv care a stricat prima versiune: dovada COMUNA nu e dovada identica."""
    r = [_sintetic("1", "a.py"), _sintetic("2", "a.py"),
         _sintetic("3", "a.py;b.py"), _sintetic("4", "b.py;a.py"),
         _sintetic("5", "a.py;c.py"), _sintetic("6", "d.py")]
    assert am.granularitate_registru(r) == [["1", "2"], ["3", "4"]]


def test_granularitatea_ignora_mecanismele_absente_si_dovezile_goale():
    r = [_sintetic("1", "a.py"), _sintetic("2", "a.py", stare="absent"),
         _sintetic("3", "-"), _sintetic("4", "")]
    assert am.granularitate_registru(r) == []


def test_granularitatea_nu_e_raportata_ca_eroziune(randuri):
    """E o observatie despre REGISTRU; amestecata in semnale ar citi ca defect al sistemului."""
    ids = {x for grup in am.granularitate_registru(randuri) for x in grup}
    assert ids, "registrul comis are grupuri cu dovada identica; testul ar fi vid altfel"
    date = am.eroziune(randuri)
    for rid in ids:
        for semnal in date[rid]["semnale"]:
            assert "identic" not in semnal and "duplicare" not in semnal


def test_subcomanda_eroziune_ruleaza_si_isi_declara_limitele():
    rez = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "audit_matrice.py"), "eroziune"],
        capture_output=True, text=True, cwd=ROOT,
    )
    assert rez.returncode == 0, rez.stdout + rez.stderr
    assert "NEMASURAT" in rez.stdout
    assert "GRANULARITATEA REGISTRULUI (nu eroziune)" in rez.stdout
