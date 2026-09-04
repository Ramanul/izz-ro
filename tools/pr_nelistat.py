"""Garda inversa: un PR deschis de mai mult de o zi NU poate lipsi din `specs/STATE.md`.

DE CE EXISTA, cu incidentul care a produs-o (2026-09-04): PR #253 era verde de 30 de ore
— toate cele 7 verificari `success` — si `specs/STATE.md` nu il pomenea deloc; lista lui de
PR-uri deschise zicea „#247" si atat. Proprietarul a citit STATE.md, a vazut ca nu e nimic
in asteptare, si a concluzionat ca munca sesiunii precedente s-a pierdut. Nu se pierduse:
statea neaterizata, invizibila.

`tests/test_pr_fantoma.py` pazeste directia CEALALTA — un PR deja pe main, listat ca Open
fara adnotarea `(merged)`. Directia asta, PR deschis care lipseste, nu era pazita de nimic,
si e cea mai scumpa: un PR listat gresit ca deschis costa o verificare; unul care lipseste
costa munca refacuta sau abandonata.

PRAGUL de 24 de ore nu e ales, e derivat din incident (30 de ore) si din cadenta reala a
repo-ului: un PR deschis acum cinci minute nu e o omisiune — STATE.md nici nu avea cum sa il
numeasca inainte sa existe. Unul care a supravietuit peste noapte, da.

Functia `incalcari` e pura (nu atinge reteaua) ca sa poata fi testata; `main()` ii aduce
datele din API.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "specs" / "STATE.md"
PRAG_ORE = 24
PR_REF = re.compile(r"#(\d+)")


def sectiune_open(state_md: str) -> str:
    """Blocul `## Open` din STATE.md, pana la urmatorul titlu de nivel 2."""
    m = re.search(r"^## Open\s*$", state_md, re.M)
    if not m:
        return ""
    rest = state_md[m.end():]
    m2 = re.search(r"^## ", rest, re.M)
    return rest[:m2.start()] if m2 else rest


def incalcari(pr_deschise: list[dict], state_md: str, acum: datetime,
              exclude: set[int] | None = None) -> list[str]:
    """PR-urile deschise de peste `PRAG_ORE` care nu apar in `## Open`.

    `exclude` = PR-ul pe care ruleaza CI chiar acum: nu se poate cere unui PR sa se
    autodeclare in STATE.md inainte sa fie deschis.

    PR-urile deschise de BOTI se sar. Motivul e plafonul: STATE.md are 40 de linii si e
    citit la fiecare pornire de sesiune — un `ci: bump actions/checkout` acolo costa context
    la fiecare tura si nu spune nimic despre unde suntem. Masurat la prima rulare a garzii
    (2026-09-04): din 11 PR-uri deschise, 4 erau Dependabot, deci fara regula asta garda ar
    fi sunat zilnic pentru bump-uri si ar fi fost dezactivata — exact esecul pe care o garda
    cu alarme false il produce. Ce NU acopera: un bot care deschide un PR de continut real
    ar fi sarit si el. Nu s-a intamplat inca in repo-ul asta; daca se intampla, filtrul
    trebuie ingustat pe `login`, nu pe `type`.
    """
    bloc = sectiune_open(state_md)
    if not bloc:
        return ["specs/STATE.md nu are sectiunea ## Open"]
    mentionate = {int(n) for n in PR_REF.findall(bloc)}
    exclude = exclude or set()
    limita = acum - timedelta(hours=PRAG_ORE)
    lipsa = []
    for pr in pr_deschise:
        numar = int(pr["number"])
        if numar in mentionate or numar in exclude:
            continue
        if (pr.get("user") or {}).get("type") == "Bot":
            continue
        deschis = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
        if deschis > limita:
            continue
        varsta = int((acum - deschis).total_seconds() // 3600)
        lipsa.append(
            f"PR #{numar} e deschis de {varsta}h si NU apare in `## Open` din STATE.md "
            f"({pr.get('title', '')[:60]!r}). Adauga-l sau inchide-l."
        )
    return sorted(lipsa)


def _pr_deschise_din_api(repo: str, token: str) -> list[dict]:
    cerere = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=100",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(cerere, timeout=30) as raspuns:
        return json.load(raspuns)


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "Ramanul/izz-ro")
    if not token:
        print("fara GITHUB_TOKEN — garda se sare (nu esueaza: local nu are cum sa citeasca API-ul)")
        return 0
    curent = os.environ.get("PR_CURENT", "")
    exclude = {int(curent)} if curent.isdigit() else set()
    probleme = incalcari(_pr_deschise_din_api(repo, token), STATE.read_text(encoding="utf-8"),
                         datetime.now(timezone.utc), exclude)
    for p in probleme:
        print(f"!! {p}")
    if probleme:
        print(f"\n{len(probleme)} PR-uri deschise lipsesc din specs/STATE.md.")
        return 1
    print("STATE.md listeaza toate PR-urile deschise de peste 24h.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
