"""§2.2 — reformulare integrala, ZERO propozitii copiate.

Regula cu cea mai mare expunere de drept de autor din REGULI-SINTEZA.md. Pana la
`generator/raport_copiere.py` traia doar in prompt, in 5 locuri din `process.py`, fara
nicio verificare mecanica — adica singura protectie era ca modelul a fost rugat frumos.

Testele de aici verifica DOUA lucruri diferite:
  · masuratoarea e corecta (nu rateaza copierea, nu inventeaza copiere unde nu e)
  · jurnalul nu poate darama o rulare, orice i-ai da
Al doilea conteaza la fel de mult ca primul: o plasa de siguranta care opreste publicarea
cand da de un caz neprevazut e mai rea decat lipsa ei.
"""
import json

import pytest

from generator.raport_copiere import noteaza
from generator.verifica_sinteza import suprapunere_sursa

SURSA = ("Primaria Ploiesti a anuntat miercuri ca lucrarile de reabilitare a stadionului "
         "Ilie Oana vor incepe in luna septembrie, cu un buget estimat de 12 milioane de lei.")


def test_reformularea_completa_nu_produce_semnal():
    """Un rezumat scris cu alte cuvinte trebuie sa dea 0% — altfel semnalul e inutil."""
    r = suprapunere_sursa("Stadionul din Ploiesti intra in renovare din toamna.", SURSA)
    assert r.procent == 0.0
    assert r.max_cuvinte < 8


def test_propozitia_copiata_verbatim_e_prinsa():
    r = suprapunere_sursa(
        "Lucrarile de reabilitare a stadionului Ilie Oana vor incepe in luna septembrie.", SURSA)
    assert r.procent == 100.0
    assert r.max_cuvinte >= 8
    assert "reabilitare a stadionului" in r.fragment


def test_diacriticele_nu_ascund_copierea():
    """Cazul care ar fi facut verificarea inutila in practica.

    Modelul scrie cu diacritice, feedurile de primarie de multe ori nu. Daca „lucrările" si
    „lucrarile" ar fi cuvinte diferite, o propozitie copiata integral ar trece drept curata.
    """
    cu_diacritice = ("Lucrările de reabilitare a stadionului Ilie Oană vor începe "
                     "în luna septembrie.")
    assert suprapunere_sursa(cu_diacritice, SURSA).max_cuvinte >= 8


def test_punctuatia_mutata_nu_ascunde_copierea():
    """O virgula in plus nu trebuie sa rupa secventa: se compara cuvinte, nu caractere."""
    r = suprapunere_sursa(
        "Lucrarile de reabilitare, a stadionului Ilie Oana, vor incepe in luna septembrie!",
        SURSA)
    assert r.max_cuvinte >= 8


def test_rezumatul_scurt_da_zero_prin_constructie_dar_max_cuvinte_ramane_util():
    """Sub 8 cuvinte nu exista nicio fereastra, deci procentul e 0 — dar nu fiindca e curat.

    De aceea `max_cuvinte` se calculeaza fara pragul de lungime: pe titluri, care au 6-16
    cuvinte, el e singurul semnal disponibil. Un test care ar cere doar `procent == 0` aici
    ar consfinti exact gaura pe care functia trebuie s-o acopere.
    """
    r = suprapunere_sursa("stadionul Ilie Oana intra in renovare", SURSA)
    assert r.procent == 0.0
    assert r.max_cuvinte == 2      # „ilie oana"; „stadionul" != „stadionului"


def test_textele_goale_nu_crapa():
    for rezumat, sursa in (("", ""), ("ceva", ""), ("", "ceva")):
        assert suprapunere_sursa(rezumat, sursa).procent == 0.0


def test_jurnalul_scrie_un_rand_cu_cifrele(tmp_path, monkeypatch):
    cale = tmp_path / "raport.jsonl"
    monkeypatch.setattr("generator.raport_copiere.CALE", cale)
    noteaza("B", "http://exemplu.ro/a", "Titlu oarecare",
            "Lucrarile de reabilitare a stadionului Ilie Oana vor incepe in luna septembrie.",
            SURSA)
    rand = json.loads(cale.read_text(encoding="utf-8").strip())
    assert rand["model"] == "B"
    assert rand["id"] == "http://exemplu.ro/a"
    assert rand["text_procent"] == 100.0
    assert rand["text_max_cuvinte"] >= 8
    assert rand["fragment"]


def test_titlul_si_textul_se_masoara_separat(tmp_path, monkeypatch):
    """Concatenate, un titlu cu suprapunere legitima ar trage procentul si ar ineca semnalul."""
    cale = tmp_path / "raport.jsonl"
    monkeypatch.setattr("generator.raport_copiere.CALE", cale)
    noteaza("C", "x", "Primaria Ploiesti a anuntat miercuri ca lucrarile de reabilitare incep",
            "Stadionul intra in renovare din toamna.", SURSA)
    rand = json.loads(cale.read_text(encoding="utf-8").strip())
    assert rand["titlu_max_cuvinte"] >= 8
    assert rand["text_procent"] == 0.0


@pytest.mark.parametrize("args", [
    ("B", None, None, None, None),
    ("B", "x", "titlu", "text", ""),
    ("C", 12345, ["nu", "e", "text"], {"nici": "asta"}, SURSA),
])
def test_jurnalul_nu_ridica_niciodata_exceptii(args, tmp_path, monkeypatch):
    """Regula 2 din antetul modulului: o masuratoare nu poate opri publicarea.

    Daca `noteaza` ar propaga o exceptie, un tip neasteptat intr-un camp ar amana articole
    bune — plasa de siguranta ar deveni punct unic de esec.
    """
    monkeypatch.setattr("generator.raport_copiere.CALE", tmp_path / "r.jsonl")
    noteaza(*args)


def test_jurnalul_nu_scrie_textul_sursei(tmp_path, monkeypatch):
    """`process.py` sterge textul sursei intentionat („scrub juridic").

    Jurnalul nu are voie sa-l reintroduca pe usa din dos: din sursa poate ajunge in fisier
    doar fragmentul COMUN, care e oricum publicat pe izz.ro.
    """
    cale = tmp_path / "raport.jsonl"
    monkeypatch.setattr("generator.raport_copiere.CALE", cale)
    noteaza("B", "x", "Titlu", "Stadionul intra in renovare.", SURSA)
    scris = cale.read_text(encoding="utf-8")
    assert "12 milioane" not in scris
    assert "Primaria Ploiesti a anuntat" not in scris
