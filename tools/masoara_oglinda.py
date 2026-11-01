#!/usr/bin/env python3
"""Cat ocupa oglinda GitHub Pages, masurat din arborele publicat, pe directoare.

DE CE EXISTA. Plafonul documentat de GitHub e 1 GB pentru un site publicat, iar oglinda a ajuns
la 3,73 GB fara ca nimic sa semnaleze (masurat 2026-10-31). Jobul `mirror` publica adaugand,
deci dimensiunea creste singura: ~19 MB/zi doar din paginile noi.

DE CE PE DIRECTOARE. Un singur apel `git/trees?recursive=1` se trunchiaza: pe 2026-10-31 a
intors 32.989 din 70.190 de fisiere, cu `truncated: true`. Un total citit de acolo ar parea
sanatos exact cand nu e. Mersul pe directoare costa ~40 de apeluri si raspunde complet.
`git ls-tree -l` nu e alternativa: pe o clona fara fisiere tipareste `BAD` in loc de marime.

Pragurile stau aici, ca sa fie o singura sursa de adevar pentru garda si pentru taiere
(`tools/curata_oglinda.py`).
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import Counter

REPO = "Ramanul/ramanul.github.io"
RAMURA = "gh-pages"

MB = 1_000_000
AVERTIZARE_MB = 900
PLAFON_MB = 950
TINTA_MB = 850
ROSU_MB = 980
# GitHub da 10 GB pe disc pentru un repo. Stergerile nu micsoreaza istoricul, deci il urmarim
# separat: o micsorare ar cere rescrierea istoricului, adica decizia proprietarului.
REPO_AVERTIZARE_GB = 8
INCERCARI = 4
# O masurare normala costa ~40 de apeluri. Peste plafon, un director s-a trunchiat si coborarea
# ar cere cate un apel per articol: mai bine job rosu decat zeci de mii de cereri.
MAX_APELURI = 500


def cere_api(cale: str) -> dict:
    cerere = urllib.request.Request(f"https://api.github.com/{cale}", headers={
        "Accept": "application/vnd.github+json", "User-Agent": "izz-oglinda"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        cerere.add_header("Authorization", f"Bearer {token}")
    # Arborii mari raspund uneori cu 5xx; un job rosu din asta ar fi alarma falsa.
    for incercare in range(INCERCARI):
        try:
            with urllib.request.urlopen(cerere, timeout=60) as raspuns:
                return json.load(raspuns)
        except urllib.error.HTTPError as eroare:
            if eroare.code < 500 or incercare == INCERCARI - 1:
                print(f"::error::GitHub a raspuns {eroare.code} la {cale}")
                raise
            time.sleep(2 ** incercare)
    raise AssertionError("bucla de mai sus iese prin return sau raise")


def arbore(cere=cere_api, ref: str = RAMURA) -> dict[str, int]:
    """Toate fisierele publicate, cale -> octeti. Coboara un nivel cand raspunsul e trunchiat."""
    radacina = cere(f"repos/{REPO}/git/trees/{ref}")
    if radacina.get("truncated"):
        raise RuntimeError("radacina oglinzii a venit trunchiata, deci totalul ar fi fals")
    fisiere: dict[str, int] = {}
    stiva: list[tuple[str, str]] = []

    def aduna(prefix: str, intrari: list[dict]) -> None:
        for e in intrari:
            cale = f"{prefix}{e['path']}"
            if e["type"] == "blob":
                fisiere[cale] = e["size"]

    aduna("", radacina["tree"])
    stiva.extend((e["path"], e["sha"]) for e in radacina["tree"] if e["type"] == "tree")
    apeluri = 0
    while stiva:
        apeluri += 1
        if apeluri > MAX_APELURI:
            raise RuntimeError(f"peste {MAX_APELURI} de apeluri, deci un director mare s-a trunchiat")
        cale, sha = stiva.pop()
        recursiv = cere(f"repos/{REPO}/git/trees/{sha}?recursive=1")
        if not recursiv.get("truncated"):
            aduna(f"{cale}/", recursiv["tree"])
            continue
        direct = cere(f"repos/{REPO}/git/trees/{sha}")
        if direct.get("truncated"):
            raise RuntimeError(f"directorul {cale} a venit trunchiat si pe un singur nivel")
        aduna(f"{cale}/", direct["tree"])
        stiva.extend((f"{cale}/{e['path']}", e["sha"]) for e in direct["tree"] if e["type"] == "tree")
    return fisiere


def verdict(total: int) -> str:
    """`ok`, `avertizare` (peste 900 MB), `taiere` (peste 950) sau `rosu` (peste 980)."""
    if total > ROSU_MB * MB:
        return "rosu"
    if total > PLAFON_MB * MB:
        return "taiere"
    if total > AVERTIZARE_MB * MB:
        return "avertizare"
    return "ok"


def pe_directoare(fisiere: dict[str, int]) -> list[tuple[str, int, int]]:
    """(director de top, octeti, fisiere), de la cel mai mare la cel mai mic."""
    octeti: Counter = Counter()
    numar: Counter = Counter()
    for cale, marime in fisiere.items():
        top = cale.split("/", 1)[0] if "/" in cale else "(radacina)"
        octeti[top] += marime
        numar[top] += 1
    return [(top, marime, numar[top]) for top, marime in octeti.most_common()]


def raport(fisiere: dict[str, int], repo_kb: int) -> str:
    total = sum(fisiere.values())
    randuri = [
        f"## Oglinda: {total / MB:,.0f} MB publicati din plafonul de 1.000 MB",
        "",
        f"{len(fisiere):,} fisiere. Repo pe disc: {repo_kb / 1_000_000:.2f} GB "
        f"(avertisment la {REPO_AVERTIZARE_GB} GB).",
        "",
        "| Director | MB | Fisiere |",
        "|---|---:|---:|",
    ]
    randuri += [f"| {top} | {marime / MB:,.1f} | {numar:,} |"
                for top, marime, numar in pe_directoare(fisiere)[:15]]
    return "\n".join(randuri)


def publica_raport(text: str) -> None:
    print(text)
    rezumat = os.environ.get("GITHUB_STEP_SUMMARY")
    if rezumat:
        with open(rezumat, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def semnaleaza_repo(repo_kb: int) -> None:
    if repo_kb > REPO_AVERTIZARE_GB * 1_000_000:
        print(f"::warning::repo-ul oglinzii are {repo_kb / 1_000_000:.2f} GB pe disc; "
              "micsorarea cere rescrierea istoricului, deci decizia proprietarului")


def main() -> int:
    fisiere = arbore()
    repo_kb = cere_api(f"repos/{REPO}")["size"]
    publica_raport(raport(fisiere, repo_kb))
    semnaleaza_repo(repo_kb)
    total = sum(fisiere.values())
    stare = verdict(total)
    if stare != "ok":
        print(f"::warning::oglinda are {total / MB:,.0f} MB, stare {stare}")
    return 1 if stare == "rosu" else 0


if __name__ == "__main__":
    sys.exit(main())
