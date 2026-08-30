#!/usr/bin/env python3
"""Posteaza un fisier ca un comentariu pe un issue. Folosit de `revizuire.yml`.

Exista ca FISIER, nu ca heredoc in workflow, dintr-un motiv precis: orice valoare din
`${{ ... }}` interpolata direct in `run:` e tiparul care a produs o injectie reala in
repo-ul asta (#177, reparata prin ENV). Un script separat primeste tot prin mediu si
prin argumente, deci tiparul nu se poate reintroduce din neatentie.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

API = "https://api.github.com"


def url_comentarii(depozit: str, issue: str) -> str:
    """URL-ul construit din bucati VALIDATE, nu din interpolare. Un `depozit` care nu are
    forma `owner/repo` sau un `issue` care nu e numeric opresc apelul aici."""
    proprietar, _, nume = depozit.partition("/")
    if not proprietar or not nume or "/" in nume:
        raise ValueError(f"depozit neasteptat: {depozit!r}")
    if not issue.isdigit():
        raise ValueError(f"numar de issue neasteptat: {issue!r}")
    return f"{API}/repos/{proprietar}/{nume}/issues/{issue}/comments"


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("folosire: posteaza_rezumat.py <fisier> <numar_issue>")
        return 2
    corp = Path(argv[1]).read_text(encoding="utf-8")
    depozit, token = os.environ.get("DEPOZIT", ""), os.environ.get("GH_TOKEN", "")
    if not depozit or not token:
        print("LIPSA: DEPOZIT si/sau GH_TOKEN nu sunt in mediu.")
        return 2
    cerere = urllib.request.Request(
        url_comentarii(depozit, argv[2]), data=json.dumps({"body": corp}).encode(),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(cerere, timeout=30) as r:  # noqa: S310 - URL validat mai sus
        print("postat:", r.status)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
