#!/usr/bin/env python3
"""Sincronizeaza sectiunea ## Open din STATE.md cu ce poate DOVEDI istoricul git.

DE CE EXISTA: STATE.md e memoria comuna a mai multor agenti care lucreaza pe acelasi repo
in paralel. Antetul lui documenteaza aceeasi greseala de doua ori: sectiuni intitulate
`Open PR` pentru PR-uri deja merge-uite. Adnotarea manuala pierde cursa cu cadenta.

CE POATE SI CE NU, spus explicit, fiindca aici a fost defectul:
  - Un merge normal lasa un commit de merge -> detectabil.
  - Un squash lasa subiectul `<titlu> (#NNN)` -> detectabil.
  - Un REBASE nu lasa NIMIC: SHA-urile sunt rescrise, nu exista commit de merge, iar
    head-ul PR-ului nu e stramos al lui main. Git nu poate decide.

MASURAT 2026-09-04 pe #247 (`feat(home): prospetime 72h`, merged 08:39 dupa API): niciuna
din cele trei metode nu-l gaseste. Versiunea de dinainte a acestui fisier folosea DOAR
`git log --merges`, nu-l vedea, si tiparea `deja sincronizat` -- adica raporta certitudine
acolo unde nu avea nici informatie. De-aia varianta asta prefera sa spuna „nu pot decide":
un fals negativ TACUT intr-un fisier de memorie partajata e mai rau decat un semn de
intrebare vizibil.

    python tools/sync_state.py                 # adnoteaza ce se poate dovedi, raporteaza restul
    python tools/sync_state.py --dry-run       # nu scrie nimic, doar spune ce ar face
"""
import argparse
import re
import subprocess
from pathlib import Path

# PR-uri numite in ## Open. Formatul canonic e `#NNN`.
_PR = re.compile(r"#(\d+)")
# Subiectul pe care GitHub il pune la „Squash and merge": `<titlu al PR-ului> (#NNN)`.
_SQUASH = re.compile(r"\(#(\d+)\)\s*$")


def find_state_file() -> Path | None:
    """Primul STATE.md gasit: intai locurile canonice, apoi o cautare recursiva.

    Ordinea conteaza — o cautare recursiva pornita direct ar putea gasi un STATE.md
    dintr-un worktree sau dintr-un director de arhiva inaintea celui real.
    """
    for p in [Path("STATE.md"), Path("specs/STATE.md"), Path("docs/STATE.md")]:
        if p.exists():
            return p
    for p in Path(".").rglob("*.md"):
        if p.name.lower() == "state.md" and ".git" not in p.parts:
            return p
    return None


def _git(*args: str) -> str:
    """Iesirea standard a unui `git`, cu esecul tratat ca text gol.

    `check=False` deliberat: intr-un repo fara istoric (clona superficiala, worktree
    proaspat) comenzile de log ies nenul, si atunci raspunsul corect e „git nu stie",
    nu o exceptie — chemarea de mai sus tocmai asta trebuie sa poata distinge.
    """
    res = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    return res.stdout


def merged_prs() -> set[str]:
    """PR-urile pe care git le poate DOVEDI aterizate. Doua cai, ambele necesare.

    Nici una nu prinde un rebase — vezi docstring-ul modulului. Ce nu e aici nu inseamna
    „deschis", inseamna „git nu stie"; apelantul trebuie sa trateze distinct cele doua.
    """
    # (1) Commituri de merge. `--oneline` da doar subiectul, deci un `#NNN` gasit aici e
    # aproape sigur PR-ul merge-uit, nu unul mentionat in treacat intr-un corp de mesaj.
    din_merge = set(_PR.findall(_git("log", "--merges", "--oneline", "-n", "300")))

    # (2) Squash. `--first-parent` tine cautarea pe trunchi: un `(#NNN)` dintr-un commit
    # adus de pe o ramura laterala n-ar dovedi ca PR-ul ALA a aterizat.
    din_squash = {
        m.group(1)
        for linie in _git("log", "--first-parent", "--format=%s", "-n", "400").splitlines()
        if (m := _SQUASH.search(linie))
    }
    return din_merge | din_squash


def prs_din_open(continut: str) -> list[str]:
    """PR-urile numite in ## Open, in ordinea aparitiei, fara duplicate."""
    gasite: list[str] = []
    in_open = False
    for linie in continut.splitlines():
        s = linie.strip()
        if s.startswith("## Open"):
            in_open = True
            continue
        if s.startswith("## ") and in_open:
            break
        if in_open and s.startswith("- "):
            for pr in _PR.findall(linie):
                if pr not in gasite:
                    gasite.append(pr)
    return gasite


def reconcile(dry_run: bool = False) -> bool:
    """Adnoteaza `(merged)` ce poate dovedi git; raporteaza restul ca nedecis.

    Intoarce True daca fisierul a fost modificat. Raportul de la final NU e optional:
    fara el, un PR aterizat prin rebase ramane tacut in ## Open si fisierul pare
    sincronizat — defectul masurat pe #247, descris in docstring-ul modulului.
    """
    state_file = find_state_file()
    if not state_file:
        print("!! STATE.md nu a fost gasit. Treci pe main sau pe ramura cu PR-ul.")
        return False

    continut = state_file.read_text(encoding="utf-8")
    dovedite = merged_prs()

    linii = continut.splitlines()
    noi, in_open, modificat = [], False, False
    adnotate: list[str] = []

    for linie in linii:
        s = linie.strip()
        if s.startswith("## Open"):
            in_open = True
            noi.append(linie)
            continue
        if s.startswith("## ") and in_open:
            in_open = False

        if in_open and s.startswith("- "):
            m = _PR.search(linie)
            # Adnoteaza dupa PRIMUL PR de pe linie: intr-o lista `#A/#B merged` adnotarea
            # de la coada s-ar citi ca si cum ar acoperi doar ultimul (nota din STATE.md).
            if m and m.group(1) in dovedite and "merged" not in linie.lower():
                linie = f"{linie.rstrip()} (merged)"
                adnotate.append(m.group(1))
                modificat = True

        noi.append(linie)

    if modificat and not dry_run:
        state_file.write_text("\n".join(noi) + "\n", encoding="utf-8")

    prefix = "[dry-run] " if dry_run else ""
    if adnotate:
        print(f"{prefix}{state_file}: adnotate (merged) -> #{', #'.join(adnotate)}")
    else:
        print(f"{prefix}{state_file}: nimic de adnotat din ce poate dovedi git.")

    # Partea care lipsea: ce NU poate decide git. Fara randurile astea, un PR aterizat prin
    # rebase ramane tacut in ## Open si fisierul pare sincronizat.
    nedecise = [pr for pr in prs_din_open(continut) if pr not in dovedite]
    if nedecise:
        print()
        print("NU POT DECIDE din git (fara commit de merge si fara sufix squash) —")
        print("aterizarea prin rebase rescrie SHA-urile si nu lasa urma:")
        print(f"  #{', #'.join(nedecise)}")
        print("Verifica-le la sursa inainte sa le crezi deschise, de exemplu prin conectorul")
        print("GitHub (`pull_request_read` -> campul `merged`). Un `find` gol nu e dovada.")
    return modificat


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="nu scrie, doar raporteaza")
    reconcile(**vars(ap.parse_args()))
