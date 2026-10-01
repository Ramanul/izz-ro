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

import http.client
import json
import os
import re
import sys
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


# --- coada nu are voie sa creasca: plafon + termen de expirare ------------------------
#
# DE CE EXISTA (2026-09-15, cerere de proprietar). Garda de mai sus rezolva VIZIBILITATEA
# unui PR uitat; nu rezolva ACUMULAREA. Masurat in ziua cererii: 9 PR-uri deschise si 3
# issue-uri, dintre care 7 PR-uri erau munca de META (registre, garzi, reguli despre reguli)
# si unul singur atingea site-ul — #297, deschis de 9 zile, complet si verificat, cu 175 de
# commituri de drift adunate peste el cat timp coada crestea.
#
# Deci mecanismul acumularii nu e uitarea: e ABSENTA unei forte de iesire. O sesiune deschide
# un PR, se termina, si nimic nu obliga pe nimeni sa-l duca la capat. Plafonul e raspunsul
# clasic la o coada care creste mai repede decat se scurge; termenul e ce impiedica plafonul
# sa fie ocolit tinand PR-uri vechi la infinit.
#
# DOUA REGULI, DELIBERAT DIFERITE:
#   · PR = munca NETERMINATA. Are termen: peste `PRAG_STAGNARE_ZILE` fara commit nou se
#     aterizeaza sau se inchide cu motiv. Nu exista a treia optiune.
#   · ISSUE = DECIZIE sau observatie, care poate trai legitim luni de zile (#198 e exemplul,
#     si IZZ-0383 a decis explicit ca #233 si #271 raman deschise). Deci NU are termen: are
#     obligatia de a fi NUMIT in `## Open` din STATE.md, cu motivul pentru care sta deschis.
#     Un issue pe care nu-l poti justifica in doua randuri nu e o decizie, e o coada.
#
# DE CE NU BLOCHEAZA PR-URILE. Lungimea cozii e stare PARTAJATA: nu e vina diff-ului care
# tocmai a fost deschis, iar blocarea lui ar produce un blocaj circular — ca sa scurtezi coada
# trebuie sa mergeuiesti, ca sa mergeuiesti iti trebuie verde. Acelasi rationament ca in
# `tests/poarta_stare.py` (#347): raportat pe `pull_request`, BLOCANT pe `schedule`, unde
# exista cine sa actioneze.
PLAFON_COADA = int(os.environ.get("IZZ_PLAFON_COADA", "5"))
PRAG_STAGNARE_ZILE = int(os.environ.get("IZZ_PRAG_STAGNARE_ZILE", "7"))


def _fara_boti(elemente: list[dict]) -> list[dict]:
    return [e for e in elemente if (e.get("user") or {}).get("type") != "Bot"]


def incalcari_coada(pr_deschise: list[dict], acum: datetime) -> list[str]:
    """Plafonul de PR-uri deschise si PR-urile stagnante. Pura: nu atinge reteaua."""
    umane = _fara_boti(pr_deschise)
    probleme = []
    if len(umane) > PLAFON_COADA:
        probleme.append(
            f"coada are {len(umane)} PR-uri deschise, peste plafonul de {PLAFON_COADA}. "
            "Aterizeaza sau inchide, nu deschide altul."
        )
    limita = acum - timedelta(days=PRAG_STAGNARE_ZILE)
    for pr in umane:
        atins = pr.get("updated_at") or pr.get("created_at")
        if not atins:
            continue
        cand = datetime.fromisoformat(atins.replace("Z", "+00:00"))
        if cand > limita:
            continue
        zile = int((acum - cand).total_seconds() // 86400)
        probleme.append(
            f"PR #{pr['number']} stagneaza de {zile} zile (prag {PRAG_STAGNARE_ZILE}) "
            f"({pr.get('title', '')[:60]!r}). Aterizeaza-l sau inchide-l cu motiv."
        )
    return probleme


def incalcari_issue_fara_motiv(issue_deschise: list[dict], state_md: str) -> list[str]:
    """Un issue deschis trebuie NUMIT in `## Open`, cu motivul pentru care sta acolo.

    Fara termen, deliberat: un issue poate fi o decizie de proprietar care asteapta luni de
    zile (#198). Ce nu poate fi e nenumit — atunci nu e decizie, e coada.
    """
    bloc = sectiune_open(state_md)
    if not bloc:
        return ["specs/STATE.md nu are sectiunea ## Open"]
    mentionate = {int(n) for n in PR_REF.findall(bloc)}
    return [
        f"issue #{i['number']} e deschis si NU apare in `## Open` din STATE.md "
        f"({i.get('title', '')[:60]!r}). Scrie motivul pentru care sta deschis, sau inchide-l."
        for i in _fara_boti(issue_deschise) if int(i["number"]) not in mentionate
    ]


def _issue_deschise_din_api(repo: str, token: str) -> list[dict]:
    """Doar issue-uri: API-ul `/issues` intoarce si PR-uri, marcate cu cheia `pull_request`."""
    brute = _cere_api(repo, token, "/issues?state=open&per_page=100")
    return [i for i in brute if "pull_request" not in i]


REPO_VALID = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")
API_HOST = "api.github.com"


def _pr_deschise_din_api(repo: str, token: str) -> list[dict]:
    """Lista PR-urilor deschise, direct din API.

    DE CE `http.client` si nu `urllib`: `repo` vine dintr-o variabila de mediu, deci e o
    INTRARE, nu o constanta, iar `urllib.urlopen` onoreaza si `file://` — Semgrep a semnalat
    exact asta de patru ori (findings 96-99). Prima incercare a fost sa validez intrarea si
    sa suprim regula; marcajul n-a prins de doua ori la rand, si asta e semnalul ca reparam
    raportul, nu cauza.

    Aici nu exista schema de schimbat: gazda e un literal, conexiunea e HTTPS prin
    constructor, iar valoarea variabila intra DOAR in path. Nici macar o slabire viitoare a
    lui `REPO_VALID` n-ar putea produce o citire de fisier local. Validarea ramane, dar
    pentru ce e ea buna cu adevarat — un mesaj clar cand mediul e configurat gresit, in loc
    de un 404 opac.
    """
    return _cere_api(repo, token, "/pulls?state=open&per_page=100")


def _cere_api(repo: str, token: str, cale: str) -> list[dict]:
    """GET pe API-ul repo-ului. Extras din `_pr_deschise_din_api` cand garda cozii a avut
    nevoie si de `/issues`: doua copii ale aceluiasi cablaj ar fi driftat, exact clasa de
    defect pe care o repara IZZ-0389."""
    if not REPO_VALID.match(repo):
        raise ValueError(f"GITHUB_REPOSITORY nu are forma owner/nume: {repo!r}")
    conexiune = http.client.HTTPSConnection(API_HOST, timeout=30)
    try:
        conexiune.request(
            "GET", f"/repos/{repo}{cale}",
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github+json",
                     "User-Agent": "izz-ro-pr-nelistat"},
        )
        raspuns = conexiune.getresponse()
        corp = raspuns.read()
        if raspuns.status != 200:
            raise RuntimeError(f"API a raspuns {raspuns.status}: {corp[:200]!r}")
        return json.loads(corp)
    finally:
        conexiune.close()


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "Ramanul/izz-ro")
    if not token:
        print("fara GITHUB_TOKEN — garda se sare (nu esueaza: local nu are cum sa citeasca API-ul)")
        return 0
    curent = os.environ.get("PR_CURENT", "")
    exclude = {int(curent)} if curent.isdigit() else set()
    acum = datetime.now(timezone.utc)
    state_md = STATE.read_text(encoding="utf-8")
    pr_deschise = _pr_deschise_din_api(repo, token)

    probleme = incalcari(pr_deschise, state_md, acum, exclude)
    for p in probleme:
        print(f"!! {p}")

    # Coada e stare PARTAJATA: lungimea ei nu e vina diff-ului care tocmai s-a deschis, iar
    # blocarea lui ar fi circulara — ca sa scurtezi coada trebuie sa mergeuiesti, ca sa
    # mergeuiesti iti trebuie verde. Raportat pe `pull_request`, blocant unde exista cine sa
    # actioneze. Acelasi rationament ca `tests/poarta_stare.py`.
    coada = incalcari_coada(pr_deschise, acum)
    coada += incalcari_issue_fara_motiv(_issue_deschise_din_api(repo, token), state_md)
    pe_pr = os.environ.get("GITHUB_EVENT_NAME") == "pull_request"
    for c in coada:
        print(("~~ " if pe_pr else "!! ") + c)

    if probleme:
        print(f"\n{len(probleme)} PR-uri deschise lipsesc din specs/STATE.md.")
        return 1
    if coada and not pe_pr:
        print(f"\n{len(coada)} incalcari de coada. Plafon {PLAFON_COADA} PR-uri, "
              f"stagnare {PRAG_STAGNARE_ZILE} zile, orice issue numit in STATE.md.")
        return 1
    if coada:
        print(f"\n{len(coada)} incalcari de coada, RAPORTATE (nu blocheaza un PR: "
              "lungimea cozii nu e vina lui). Blocheaza rularea programata.")
    print("STATE.md listeaza toate PR-urile deschise de peste 24h.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
