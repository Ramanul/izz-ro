"""Teste pentru verificarile mecanice de sinteza si pentru jurnalul de suprapunere.

De ce exista: `generator/verifica_sinteza.py` si `generator/raport_copiere.py` sunt
plasa de siguranta pentru §2.2/§2.3/§2.5/§2.7 din REGULI-SINTEZA.md, adica exact
regulile cu expunere juridica. Pana la fisierul asta aveau ZERO teste (masurat
2026-08-20). Cod de plasa de siguranta fara teste e o plasa despre care nimeni nu
mai stie daca e intinsa.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


from generator import raport_copiere
from generator.verifica_sinteza import (
    citate_inventate,
    cifre_straine,
    rezerva_pierduta,
    suprapunere_sursa,
    verifica,
)

RADACINA = Path(__file__).resolve().parents[1]


# ---- §2.3 citate -------------------------------------------------------------

def test_citat_real_nu_e_semnalat():
    sursa = "Primarul a spus ca lucrarile incep luni si tin doua luni."
    assert citate_inventate('El a declarat: „lucrarile incep luni”', sursa) == []


def test_citat_inventat_e_semnalat():
    sursa = "Primarul a spus ca lucrarile incep luni."
    gasite = citate_inventate('El a declarat: „vom termina pana la Craciun”', sursa)
    assert len(gasite) == 1


def test_diacriticele_nu_transforma_un_citat_corect_in_inventat():
    # Modelul adauga diacritice pe care feedurile de primarie nu le au. Daca
    # normalizarea ar disparea, testul asta pica primul.
    sursa = "Consiliul a aprobat hotararea de buget."
    assert citate_inventate('„HOTĂRÂREA DE BUGET”'.lower(), sursa) == []


# ---- §2.7 cifre --------------------------------------------------------------

def test_cifra_din_sursa_trece_iar_una_straina_e_semnalata():
    sursa = "Investitia este de 1.500.000 de lei pentru 12 scoli."
    assert cifre_straine("Investitie de 1500000 lei", sursa) == []
    assert "45" in cifre_straine("Investitie pentru 45 de scoli", sursa)


def test_cifrele_de_o_singura_cifra_sunt_ignorate():
    # Altfel "a 3-a oara" produce semnal la fiecare al doilea articol.
    assert cifre_straine("s-a intamplat a 3-a oara", "text fara cifre") == []


# ---- §2.5 rezerve ------------------------------------------------------------

def test_rezerva_pierduta_cand_rezumatul_afirma_ce_sursa_doar_banuieste():
    sursa = "Barbatul este acuzat ca ar fi sustras banii din casierie."
    assert rezerva_pierduta("Barbatul a sustras banii din casierie.", sursa) is True


def test_rezerva_pastrata_nu_e_semnalata():
    sursa = "Barbatul este acuzat ca ar fi sustras banii."
    assert rezerva_pierduta("Barbatul e acuzat de sustragere.", sursa) is False


def test_fara_rezerva_in_sursa_nu_exista_ce_pierde():
    assert rezerva_pierduta("A castigat concursul.", "Elevul a castigat concursul.") is False


# ---- §2.2 suprapunere --------------------------------------------------------

def test_text_copiat_integral_da_suta_la_suta():
    sursa = ("Politia a anuntat ca traficul va fi restrictionat pe bulevardul principal "
             "intre orele opt si zece dimineata pentru lucrari de asfaltare")
    s = suprapunere_sursa(sursa, sursa)
    assert s.procent == 100.0
    assert s.max_cuvinte >= 8


def test_text_reformulat_da_zero():
    sursa = ("Politia a anuntat ca traficul va fi restrictionat pe bulevardul principal "
             "intre orele opt si zece pentru lucrari de asfaltare")
    rezumat = ("Circulatia se inchide doua ore dimineata pe artera centrala, din cauza "
               "unor reparatii la carosabil, potrivit autoritatilor locale")
    assert suprapunere_sursa(rezumat, sursa).procent == 0.0


def test_rezumat_mai_scurt_decat_fereastra_da_zero_procent_dar_max_cuvinte_real():
    # Capcana documentata in docstring: procentul 0 NU inseamna curat pe texte scurte;
    # de-asta `max_cuvinte` se calculeaza separat. Titlurile au 6-16 cuvinte.
    sursa = "Guvernul a aprobat ordonanta privind plafonarea preturilor la energie"
    titlu = "Guvernul a aprobat ordonanta"
    s = suprapunere_sursa(titlu, sursa)
    assert s.procent == 0.0
    assert s.max_cuvinte == 4


# ---- verificarea compusa -----------------------------------------------------

def test_verifica_aduna_toate_codurile():
    sursa = "Primarul spune ca ar fi vorba de 20 de locuinte."
    probleme = verifica("Titlu", 'Sunt „exact 99 de locuinte” gata.', sursa)
    coduri = {p.cod for p in probleme}
    assert "citat_inventat" in coduri
    assert "cifra_straina" in coduri
    assert "rezerva_pierduta" in coduri


# ---- jurnalul de suprapunere -------------------------------------------------

def test_noteaza_scrie_un_rand_in_calea_redirectata(tmp_path, monkeypatch):
    jurnal = tmp_path / "raport.jsonl"
    monkeypatch.setenv("IZZ_RAPORT_COPIERE", str(jurnal))
    raport_copiere.noteaza("B", "https://exemplu.ro/x", "Un titlu oarecare",
                           "Un rezumat scris cu alte cuvinte", "Textul sursei initiale")
    randuri = [json.loads(l) for l in jurnal.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(randuri) == 1
    assert randuri[0]["model"] == "B"
    assert "text_procent" in randuri[0] and "titlu_procent" in randuri[0]


def test_noteaza_nu_salveaza_niciodata_textul_sursei(tmp_path, monkeypatch):
    # Regula 1 din antetul modulului. Daca pica, scrubul juridic e ocolit pe usa din dos.
    jurnal = tmp_path / "raport.jsonl"
    monkeypatch.setenv("IZZ_RAPORT_COPIERE", str(jurnal))
    secret = "PROPOZITIE UNICA DIN SURSA CARE NU TREBUIE SA AJUNGA IN JURNAL"
    raport_copiere.noteaza("B", "id", "titlu", "rezumat complet diferit", secret)
    assert secret.lower() not in jurnal.read_text(encoding="utf-8").lower()


def test_noteaza_nu_ridica_exceptii_niciodata(tmp_path, monkeypatch):
    # Regula 2 din antetul modulului: o masuratoare care raporteaza nu poate fi motivul
    # pentru care un articol nu se publica.
    monkeypatch.setenv("IZZ_RAPORT_COPIERE", str(tmp_path / "sub" / "dir" / "r.jsonl"))
    raport_copiere.noteaza("B", None, None, None, None)
    raport_copiere.noteaza(None, object(), object(), object(), "sursa")


def test_calea_implicita_ramane_in_data_cand_nu_e_redirectata(monkeypatch):
    monkeypatch.delenv("IZZ_RAPORT_COPIERE", raising=False)
    assert raport_copiere._cale() == raport_copiere.CALE


# ---- unealta de masurare pe corpus -------------------------------------------

def test_fluxul_C_ramane_neverificabil_chiar_cand_are_sursa(tmp_path):
    """Pazeste invariantul din care ramura `synthesis` era cod mort.

    Fluxul C nu-si pastreaza sursele per membru, deci se exclude INAINTE de a alege
    rezumatul. Daca cineva scoate `continue`-ul, testul asta pica si repune intrebarea.
    """
    corpus = tmp_path / "articles.json"
    corpus.write_text(json.dumps([
        {"model": "C", "processed_by": "gemini", "original_title": "T", "description": "D",
         "title": "t", "synthesis": "s"},
        {"model": "B", "processed_by": "official", "title": "t", "teaser": "x"},
    ], ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "tools/masoara_sinteza.py", str(corpus)],
                       cwd=RADACINA, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert "neverificabile (sursa lipsa) : 1" in r.stdout
    assert "VERIFICATE                   : 0" in r.stdout


# ---- unealta de citit raportul -----------------------------------------------

def _modul_citeste():
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("citeste_raport",
                                   RADACINA / "tools" / "citeste_raport_copiere.py")
    modul = module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def test_histograma_acopera_toate_valorile_o_singura_data():
    # Benzile trebuie sa fie o partitie: fiecare rezumat cade exact intr-una. Daca s-ar
    # suprapune sau ar lasa o gaura, procentele din raport nu ar mai insemna nimic.
    m = _modul_citeste()
    valori = [0.0, 0.5, 1.0, 9.9, 10.0, 24.9, 25.0, 49.9, 50.0, 74.9, 75.0, 99.9, 100.0]
    benzi = m._histograma(valori)
    assert sum(n for _, n in benzi) == len(valori)
    assert benzi[-1][1] == 1          # doar 100.0 intra in banda de sus


def test_pentru_consola_nu_cade_pe_diacritice():
    # Capcana [Q1] din auditul din 2026-08-20: consola Windows e cp1252 si un fragment
    # cu diacritice ar opri unealta exact pe randul cel mai important.
    m = _modul_citeste()
    iesire = m._pentru_consola("hotărârea de buget, ședința de miercuri")
    assert isinstance(iesire, str) and len(iesire) > 10


def test_unealta_ruleaza_pe_jurnal_si_ignora_randul_stricat(tmp_path):
    jurnal = tmp_path / "r.jsonl"
    jurnal.write_text(
        '{"model": "B", "text_procent": 10, "text_max_cuvinte": 3, "id": "a", "fragment": "x"}\n'
        '{ rupt\n'
        '{"model": "C", "text_procent": 100, "text_max_cuvinte": 12, "id": "b", "fragment": "y"}\n',
        encoding="utf-8")
    r = subprocess.run([sys.executable, "tools/citeste_raport_copiere.py", str(jurnal)],
                       cwd=RADACINA, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert "REZUMATE MASURATE: 2" in r.stdout
    assert "1 randuri necitibile" in r.stdout
    assert "maxim absolut: 12" in r.stdout


def test_jurnal_inexistent_da_cod_de_eroare_si_explica(tmp_path):
    r = subprocess.run([sys.executable, "tools/citeste_raport_copiere.py",
                        str(tmp_path / "nu-exista.jsonl")],
                       cwd=RADACINA, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1
    assert "NU EXISTA" in r.stdout


# --- Praguri blocante §2.2 (text_copiat / titlu_copiat), 2026-09-05 ---------------

from generator import verifica_sinteza as vs  # noqa: E402 - bloc de teste dedicat

_SURSA_16 = ("primăria a anunțat astăzi că lucrările la pasajul central vor începe lunea "
             "viitoare iar traficul va fi deviat complet timp de trei luni")


def test_propozitie_copiata_integrala_e_blocanta():
    probleme = vs.verifica("Titlu reformulat altfel", _SURSA_16, _SURSA_16 + " și mai mult context oficial.")
    assert any(p.cod == "text_copiat" for p in probleme)


def test_parafraza_curata_nu_e_blocanta():
    rezumat = ("administrația locală a comunicat că șantierul de la pasaj pornește săptămâna "
               "viitoare, cu devieri pe tot parcursul veri")
    probleme = vs.verifica("Consiliul local a votat planul de trafic", rezumat, _SURSA_16)
    coduri = {p.cod for p in probleme}
    assert "text_copiat" not in coduri
    assert "titlu_copiat" not in coduri


def test_citat_verbatim_lung_permis():
    rezumat = "„" + _SURSA_16 + "” a declarat purtătorul de cuvânt."
    probleme = vs.verifica("Declarație despre pasaj", rezumat, _SURSA_16 + " Confirmarea a venit oficial.")
    coduri = {p.cod for p in probleme}
    assert "text_copiat" not in coduri
    assert "citat_inventat" not in coduri


def test_titlu_transcris_integral_e_blocant():
    titlu = " ".join(_SURSA_16.split()[:8])
    probleme = vs.verifica(titlu, "Rezumat parafrazat, alte cuvinte cu totul.", _SURSA_16)
    assert any(p.cod == "titlu_copiat" for p in probleme)


def test_text_copiat_ajunge_blocant_in_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("IZZ_RAPORT_COPIERE", str(tmp_path / "jurnal.jsonl"))
    monkeypatch.setenv("IZZ_RAPORT_COPIERE_GATE", str(tmp_path / "gate.jsonl"))
    raport_copiere.noteaza("C", "id-gate-test", "Titlu reformulat separat", _SURSA_16, _SURSA_16)
    randuri = [json.loads(l) for l in (tmp_path / "gate.jsonl")
               .read_text(encoding="utf-8").splitlines() if l.strip()]
    coduri = {i["cod"] for r in randuri for i in r["blocking_issues"]}
    assert "text_copiat" in coduri
