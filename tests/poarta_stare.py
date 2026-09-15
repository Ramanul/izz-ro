"""Poarta pentru garzile care citesc stare COMISA si MUTABILA.

DE CE EXISTA (2026-09-14). Masurat pe ultimele 19 rulari `ci.yml` incheiate pe main
(comanda: `actions_list list_workflow_runs ci.yml branch=main perPage=30`, fereastra
2026-09-06 … 2026-09-14): **10 ROSII din 19**. Niciuna dintre cele trei verificate in
detaliu nu era cauzata de diff-ul care tocmai aterizase:

  · IZZ-0378 — o linie invechita din `specs/STATE.md` a picat INTREAGA coada de PR-uri,
    inclusiv dependabot-uri care nu ating fisierul. `test_niciun_pr_fantoma_in_state_open`
    citeste istoricul de merge al lui main, care se misca sub orice ramura deschisa.
  · #332 — pe ACELASI commit 85483216, `tests` trece pe `event=push` si pica pe
    `event=pull_request`: merge commitul aduce starea de pe main in checkout.
  · IZZ-0384 / fb7f8ed — `test_podeaua_absoluta_ramane_deasupra_ferestrei_TTL` a picat pe
    main cu `git diff HEAD~1 --name-only` intorcand doar `specs/STATE.md` si
    `specs/registru.tsv`, adica NICIO intrare a testului.

INVARIANTUL, scris o data: **verdictul unui PR e functie de diff-ul PR-ului.** Un test al
carui rezultat poate flipui intre doua rulari pe ACELASI head nu are ce cauta in poarta care
blocheaza coada — nu fiindca ar fi mai putin important, ci fiindca acolo pedepseste omul
gresit. Plateste autorul urmatorului PR, nu autorul starii.

CE FACE. Testele marcate `stare_partajata` raman in suita si raman rosii cand starea chiar a
derivat. Se schimba doar CINE e blocat de ele:

  · pe `push` in main, pe `schedule`, si local  -> BLOCANT, ca azi.
  · pe un PR care ATINGE intrarile garzii       -> BLOCANT (altfel ar fi o gaura: un PR care
    urca `ARTICLE_TTL_DAYS` ar trece).
  · pe un PR care NU atinge intrarile           -> raportat ca `xfail` cu motivul scris, deci
    vizibil in rezumatul pytest, dar fara sa inroseasca coada.

CE NU FACE, spus pe fata. Nu repara derivarea starii si nu o ascunde de proprietar: un rosu
pe main ramane rosu pe main, si de-aia perechea acestui modul e rularea programata din
`ci.yml` — fara ea, derivarea ar fi descoperita tot de urmatorul PR, doar mai tarziu.

DE CE NU IN WORKFLOW. Aceeasi suita e pornita din doua workflow-uri (`ci.yml` si
`tests.yml`); o poarta scrisa in YAML ar trebui tinuta sincronizata in doua locuri, si exact
clasa asta de duplicare a produs IZZ-0371 (acelasi fallback scris in sapte workflow-uri, corect
in patru). Aici e o singura implementare, cu teste proprii.
"""
from __future__ import annotations

import functools
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MARCAJ = "stare_partajata"

# Caile care fac un PR RASPUNZATOR pentru o garda de stare. Atingi una, garda redevine
# blocanta pentru tine. Lista e de INTRARI ale garzilor, nu de fisiere „importante":
#   · `generator/config.py`  — ARTICLE_TTL_DAYS, OUTPUT_FILE_BUDGET, rezerva, CATEGORII_REDENUMITE
#   · `generator/state.py`   — normalizarea `published` la salvare
#   · `generator/fetch.py`   — parserele de data care produc `published`
#   · `data/articles.json`   — starea insasi
#   · `specs/STATE.md`       — sectiunea `## Open` pe care o citeste garda de PR fantoma
#   · `specs/registru.tsv`   — garda de coliziuni de ID intre ramuri paralele
#   · `tests/`               — testul marcat insusi; daca il schimbi, raspunzi de el
INTRARI = (
    "generator/config.py",
    "generator/state.py",
    "generator/fetch.py",
    "data/articles.json",
    "specs/STATE.md",
    "specs/registru.tsv",
)
INTRARI_PREFIX = ("tests/",)


def _git(*argumente: str) -> str | None:
    """Iesirea comenzii, sau None daca git a esuat. Nu ridica: apelantul decide implicitul."""
    try:
        iesire = subprocess.run(
            ["git", *argumente], cwd=ROOT, capture_output=True, text=True,
            check=False, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return iesire.stdout if iesire.returncode == 0 else None


def _baza_de_comparatie() -> str | None:
    """Ref-ul fata de care se masoara diff-ul PR-ului, prima varianta care exista."""
    baza = (os.environ.get("GITHUB_BASE_REF") or "main").strip()
    for ref in (f"origin/{baza}", baza, "origin/main", "main"):
        if _git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"):
            return ref
    return None


def fisiere_atinse_de_pr() -> list[str] | None:
    """Caile schimbate de ramura fata de baza ei, sau None daca nu se pot determina.

    Trei puncte, nu doua: `A...B` da ce s-a schimbat pe RAMURA de la baza comuna incoace.
    Cu doua puncte, orice commit aterizat pe main intre timp ar aparea ca „atins de PR" —
    exact confuzia pe care modulul asta o repara.
    """
    ref = _baza_de_comparatie()
    if ref is None:
        return None
    iesire = _git("diff", "--name-only", f"{ref}...HEAD")
    if iesire is None:
        return None
    return [linie.strip() for linie in iesire.splitlines() if linie.strip()]


def _pr_atinge_intrarile() -> bool | None:
    fisiere = fisiere_atinse_de_pr()
    if fisiere is None:
        return None
    return any(
        cale in INTRARI or cale.startswith(INTRARI_PREFIX) for cale in fisiere
    )


@functools.lru_cache(maxsize=1)
def motiv_neblocant() -> str | None:
    """Motivul pentru care garzile de stare NU blocheaza rularea curenta, sau None.

    None inseamna BLOCANT — si e implicitul pentru tot ce nu e clar. Directia asta a fost
    aleasa deliberat: un fals blocant costa o investigatie, un fals permis lasa sa treaca
    exact PR-ul care urca TTL-ul peste plafon.
    """
    if os.environ.get("IZZ_STARE_BLOCANTA") == "1":
        return None
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return None  # local: suita completa, verdict complet
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        return None  # push in main, schedule, workflow_dispatch: blocant
    atinge = _pr_atinge_intrarile()
    if atinge is None:
        return None  # nu stim -> blocam, ca pana acum
    if atinge:
        return None  # PR-ul chiar raspunde de intrari
    return (
        "garda de stare partajata: PR-ul nu atinge niciuna dintre intrarile ei "
        f"({', '.join(INTRARI)}, tests/). Un esec aici e derivare de stare pe main, nu un "
        "defect al acestui diff — vezi rularea programata din ci.yml si tests/poarta_stare.py."
    )
