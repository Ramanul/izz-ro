"""Garda de sincronizare workflow ↔ script pentru audit-gratuit.

Workflow-ul apeleaza subcomenzi ale tools/audit_gratuit.py. Daca cineva adauga sau
redenumeste un pas intr-un singur loc, testul de mai jos pica inainte de merge,
nu saptamana urmatoare la prima rulare programata.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pasii_workflowului_sunt_subcomenzi_reale() -> None:
    workflow = (ROOT / ".github" / "workflows" / "audit-gratuit.yml").read_text(encoding="utf-8")
    script = (ROOT / "tools" / "audit_gratuit.py").read_text(encoding="utf-8")
    apeluri = set(re.findall(r"python tools/audit_gratuit\.py ([a-z_]+)", workflow))
    definit = set(re.findall(r'sub\.add_parser\("([a-z_]+)"', script))
    assert apeluri, "workflow-ul nu mai apeleaza niciun pas al scriptului"
    assert apeluri <= definit, f"workflow-ul apeleaza subcomenzi inexistente: {sorted(apeluri - definit)}"


def test_scriptul_nu_dubleaza_integrarea_indexnow() -> None:
    """IndexNow exista deja in pipeline (config.INDEXNOW_KEY + tools/indexnow_submit.py).

    Un al doilea punct de trimitere ar trimite URL-urile de doua ori si ar dubla starea.
    """
    script = (ROOT / "tools" / "audit_gratuit.py").read_text(encoding="utf-8")
    assert "INDEXNOW" not in script, "audit_gratuit nu trebuie sa reimplementeze IndexNow"
