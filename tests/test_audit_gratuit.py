"""Garda de sincronizare workflow ↔ script pentru audit-gratuit.

Workflow-ul apeleaza subcomenzi ale tools/audit_gratuit.py. Daca cineva adauga sau
redenumeste un pas intr-un singur loc, testul de mai jos pica inainte de merge,
nu saptamana urmatoare la prima rulare programata.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
audit = importlib.import_module("tools.audit_gratuit")

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


# --- normalizatorul lychee (adăugat 2026-10-11, după eșecul 37298110785) ------------------
SCHEMA_2024 = {   # forma reală a raportului lychee v0.24.x (verificată în sursa proiectului)
    "total": 5, "unique": 5, "successful": 3, "unknown": 0, "unsupported": 0,
    "timeouts": 1, "redirects": 1, "remaps": 0, "excludes": 0, "errors": 1, "cached": 0,
    "success_map": {"reports/urls.txt": [
        {"url": "https://x/ok", "status": {"text": "OK", "code": 200}}]},
    "error_map": {"reports/urls.txt": [
        {"url": "https://x/rupt", "status": {"text": "Rejected status code: 404 Not Found",
                                             "code": 404}}]},
    "timeout_map": {"reports/urls.txt": [
        {"url": "https://x/lent", "status": {"text": "Timeout"}}]},
}


def _raporteaza(tmp_path, monkeypatch, brut) -> dict:
    monkeypatch.setattr(audit, "REPORTS_DIR", str(tmp_path))
    (tmp_path / "lychee-raw.json").write_text(json.dumps(brut), encoding="utf-8")
    audit.lychee()
    return json.loads((tmp_path / "lychee.json").read_text(encoding="utf-8"))


def test_normalizeaza_schema_reala_a_lychee(tmp_path, monkeypatch):
    raport = _raporteaza(tmp_path, monkeypatch, SCHEMA_2024)
    assert raport["stare"] == "ATENTIE"
    assert raport["date"]["total"] == 5 and raport["date"]["ok"] == 3
    assert raport["date"]["rupte"] == 2, "errors + timeouts"
    assert "https://x/rupt" in raport["detaliu"] and "404" in raport["detaliu"]
    assert "https://x/lent" in raport["detaliu"]


def test_toate_linkurile_bune_dau_stare_ok(tmp_path, monkeypatch):
    brut = dict(SCHEMA_2024, errors=0, timeouts=0,
                error_map={}, timeout_map={})
    raport = _raporteaza(tmp_path, monkeypatch, brut)
    assert raport["stare"] == "OK"
    assert raport["date"]["rupte"] == 0


def test_fara_raport_brut_starea_e_sarit(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "REPORTS_DIR", str(tmp_path))
    audit.lychee()
    raport = json.loads((tmp_path / "lychee.json").read_text(encoding="utf-8"))
    assert raport["stare"] == "SARIT", "un pas picat nu are voie să arate ca unul curat"
