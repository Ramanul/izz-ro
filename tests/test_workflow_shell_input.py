"""Niciun input neîncredere nu se interpolază direct într-un script `run:`.

`${{ }}` se expandează înainte de shell. Ghilimelele din YAML nu ajută.
Valorile controlate de un actor (inputs, corp de eveniment, nume de branch
ales la dispatch) trec prin `env:`, apoi se citesc citate.

Excepțiile de mai jos sunt câmpuri puse de GitHub, nu de un comentator:
identificatori de rulare, pe care un actor nu le poate umple cu ghilimele.
"""
from pathlib import Path

import pytest
import yaml

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows"

# Expresii care rămân în `run:` pentru că nu sunt text de actor.
_PERMISE = (
    "github.server_url",
    "github.repository",
    "github.run_id",
    "github.workflow",
    "github.job",
    "github.sha",
    "runner.temp",
    "runner.os",
    "steps.",
    "needs.",
    "env.",
    "hashFiles(",
)


def _expresii(script: str) -> list[str]:
    gasite = []
    rest = script
    while "${{" in rest:
        start = rest.index("${{")
        end = rest.find("}}", start)
        if end < 0:
            gasite.append(rest[start:])
            break
        gasite.append(rest[start:end + 2])
        rest = rest[end + 2:]
    return gasite


def _interzisa(expresie: str) -> bool:
    interior = expresie[3:-2]
    return not any(marker in interior for marker in _PERMISE)


@pytest.mark.parametrize("cale", sorted(WF.glob("*.yml")))
def test_run_nu_interpoleaza_input_de_actor(cale: Path):
    doc = yaml.safe_load(cale.read_text(encoding="utf-8"))
    probleme = []
    for nume, job in (doc.get("jobs") or {}).items():
        for pas in job.get("steps") or []:
            script = pas.get("run")
            if not isinstance(script, str):
                continue
            for expresie in _expresii(script):
                if _interzisa(expresie):
                    probleme.append(f"{cale.name} job {nume}: {expresie.strip()}")
    assert probleme == []
