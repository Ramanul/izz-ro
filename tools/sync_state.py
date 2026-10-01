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

DE CE CITESTE TOT BLOCUL, nu doar liniile care incep cu `- ` (reparat 2026-09-14): pana
azi bucla sarea liniile de CONTINUARE ale unui bullet. STATE.md are plafon de ~40 de linii,
deci wrappingul e regula, nu exceptia — adica unealta era oarba pe majoritatea continutului
tocmai in fisierul pentru care a fost scrisa. Masurat pe STATE.md de pe #343: unealta vedea
3 PR-uri in `## Open` (328, 344, 343), garda din `tests/test_pr_fantoma.py` vedea 18. De-aia
raporta „nimic de adnotat" pe exact starea pe care garda o pica, iar aceeasi eroare a aparut
de doua ori in 12 ore, pe doua ramuri (#342 commit 1870208, apoi #343).

DE CE ADNOTAREA STA IMEDIAT DUPA NUMAR, nu la capatul liniei: garda accepta
`_DECLARAT_MERGED` (definit mai jos), iar clasa lui exclude `#`. Pe o linie cu mai multe PR-uri, un
`(merged)` pus la coada e atins DOAR de ultimul numar; pentru toate celelalte drumul e taiat
de urmatorul `#`. Pozitia veche era corecta doar accidental, cand PR-ul adnotat se intampla
sa fie ultimul de pe linie. Imediat dupa numar e singura pozitie care garanteaza potrivirea
indiferent de cate PR-uri mai sunt pe linie.

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
# „Declarat deja merge-uit". Tiparul e COPIAT din `tests/test_pr_fantoma.py` (`PR_MERGED_ANNOT`)
# si se aplica pe TOT blocul `## Open`, nu pe o linie: garda aia ruleaza in CI, deci ea e
# autoritatea asupra a ce inseamna „adnotat". Fara alinierea asta cele doua unelte se
# contrazic — masurat 2026-09-04: garda trecea, iar `sync_state` voia sa mai adauge un
# `(merged)` pe bullet-ul de regula care doar CITEAZA `#248`, desi linia-paranteza de
# deasupra il declara deja. Adnotarea in plus e zgomot si creste fisierul spre plafonul
# lui de 40 de linii, adica strica exact ce pazeste cealalta garda.
_DECLARAT_MERGED = re.compile(r"#(\d+)[^#\n]*\bmerged\b", re.I)


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


def blocul_open(continut: str) -> str:
    """Textul dintre `## Open` si urmatorul titlu de nivel 2. Gol daca sectiunea lipseste."""
    linii, aduna, bloc = continut.splitlines(), False, []
    for linie in linii:
        s = linie.strip()
        if s.startswith("## Open"):
            aduna = True
            continue
        if s.startswith("## ") and aduna:
            break
        if aduna:
            bloc.append(linie)
    return "\n".join(bloc)


def deja_declarate_merged(continut: str) -> set[str]:
    """PR-urile pe care blocul `## Open` le declara deja merge-uite, oriunde in el.

    Aceeasi semantica cu garda din `tests/test_pr_fantoma.py` — vezi comentariul de la
    `_DECLARAT_MERGED`. Un PR de aici NU mai primeste inca o adnotare.
    """
    return set(_DECLARAT_MERGED.findall(blocul_open(continut)))


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
        if in_open:
            for pr in _PR.findall(linie):
                if pr not in gasite:
                    gasite.append(pr)
    return gasite


def adnoteaza_linie(linie: str, dovedite: set[str], declarate: set[str]) -> tuple[str, list[str]]:
    """Pune `(merged)` imediat dupa FIECARE `#N` dovedit si inca nedeclarat de pe o linie.

    Pura, ca sa poata fi testata fara repo si fara fisier. `declarate` e MUTATA: un PR se
    declara o singura data in tot blocul, deci odata adnotat aici nu mai primeste o a doua
    adnotare pe alta linie. Vezi docstringul modulului pentru de ce pozitia conteaza.
    """
    proaspete: list[str] = []

    def _sub(m: "re.Match[str]") -> str:
        nr = m.group(1)
        if nr in dovedite and nr not in declarate:
            declarate.add(nr)
            proaspete.append(nr)
            return f"#{nr} (merged)"
        return m.group(0)

    return _PR.sub(_sub, linie), proaspete


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
    declarate = deja_declarate_merged(continut)

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

        if in_open:
            # Tot blocul, inclusiv continuarile de bullet, si fiecare numar de pe linie —
            # nu doar primul. `declarate` opreste o a doua adnotare pentru un PR pe care
            # blocul il declara deja merge-uit ALTUNDEVA (vezi `_DECLARAT_MERGED`) si se
            # completeaza pe masura ce adnotam, ca acelasi PR sa nu fie marcat de doua ori.
            linie, proaspete = adnoteaza_linie(linie, dovedite, declarate)
            if proaspete:
                adnotate.extend(proaspete)
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
    # `declarate` iese si de aici: un PR pe care textul il declara deja merge-uit e o
    # decizie luata de om si scrisa. Git tot nu-l poate dovedi (rebase), deci fara excluderea
    # asta ar fi raportat la FIECARE rulare, la nesfarsit — iar un avertisment care nu se
    # stinge niciodata devine zgomot pe care cititorul invata sa-l sara. Costul acceptat,
    # spus pe fata: unealta crede adnotarea pe cuvant. Nu are alternativa — pentru o
    # aterizare prin rebase git nu ofera nicio dovada de verificat impotriva.
    nedecise = [pr for pr in prs_din_open(continut)
                if pr not in dovedite and pr not in declarate]
    if nedecise:
        print()
        print("NU POT DECIDE din git (fara commit de merge si fara sufix squash) —")
        print("aterizarea prin rebase rescrie SHA-urile si nu lasa urma:")
        print(f"  #{', #'.join(nedecise)}")
        print("Verifica-le la sursa inainte sa le crezi deschise, de exemplu prin conectorul")
        print("GitHub (`pull_request_read` -> campul `merged`). Un `find` gol nu e dovada.")
        print("Lista contine si ISSUE-uri citate in ## Open (#83, #198 ...): din text nu se")
        print("poate spune care `#N` e PR si care e issue, iar unealta nu atinge reteaua.")
    return modificat


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="nu scrie, doar raporteaza")
    reconcile(**vars(ap.parse_args()))
