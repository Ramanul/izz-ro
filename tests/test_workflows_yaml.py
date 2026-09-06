"""Toate workflow-urile GitHub trebuie să fie YAML valid.

Istorie măsurată: `workflow_dispatch` fără două puncte în `harta-smoke.yml`
a stat acolo din 12 august și a făcut FIECARE rulare să moară în 0 s, fără
niciun job — pe orice branch, pentru că GitHub nu mai putea evalua filtrele
`on:` dintr-un fișier pe care nu-l putea parsa. A ieșit la suprafață abia
pe 6 septembrie, când comitul pe datasetul hărții a declanșat workflow-ul
prima dată. Un fișier de 25 de linii, o literă, o săptămână de CI roșu.

Testul ăsta parsează fiecare workflow la fiecare PR și părnăcește clasa
întreagă înainte de merge.
"""
import pathlib

import yaml

WF = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _workflows():
    return sorted(list(WF.glob("*.yml")) + list(WF.glob("*.yaml")))


def test_exista_workflow_de_parsat():
    assert _workflows(), "niciun workflow gasit — globul e gresit?"


def test_fiecare_workflow_e_yaml_valid_cu_joburi():
    for cale in _workflows():
        doc = yaml.safe_load(cale.read_text(encoding="utf-8"))
        assert isinstance(doc, dict), f"{cale.name}: YAML nu e un mapping"
        assert doc.get("jobs"), f"{cale.name}: nu are jobs"
