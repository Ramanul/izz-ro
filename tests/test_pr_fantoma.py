"""Garda: PR-uri deja pe main nu stau în STATE.md ## Open fără adnotarea (merged).

Port din #236 / #244. Necesită fetch-depth: 0 în tests.yml.

MODURI DE ATERIZARE PE MAIN — numărate pe istoricul COMPLET (1417 commit-uri,
2026-09-04). Prima măsurătoare din sesiune a dat „7 și 6": era făcută pe o clonă
shallow, care vedea două zile. De-aia `istoric_trunchiat()` de mai jos există.

  1. merge commit  `Merge pull request #N from …`  →  42 aterizări, detectate mereu
  2. squash GitHub `subiect oarecare (#N)`         → 148 aterizări, ratate până azi
  3. squash/rebase cu subiect scris de mână        → IMPOSIBIL de detectat din git

Varianta de dinainte vedea 42 din 190 de aterizări — 22%.

Modul 3 nu e o scăpare de implementare, e o limită a sursei, și are un caz real.
#247 a fost merge-uit pe 2026-09-04 08:39 (`merged: true`, `merged_by: Ramanul` în
API) și a aterizat ca `d9e3664 feat(home): prospețime 72h pe homepage`, cu corpul
„Integrează filtrul de prospețime 72h pe homepage și testele aferente." — ZERO
apariții ale lui `#247` în tot istoricul lui main. Garda l-a ratat, iar STATE.md
l-a ținut în `## Open` ca PR deschis până pe 09-04. Singura sursă care poate închide
modul 3 e API-ul GitHub, unde `tools/pr_nelistat.py` (#264) e deja — pe direcția
inversă (PR deschis care lipsește din STATE.md).

DE CE NU un tipar generic pe corpurile de commit, deși ar prinde mai mult: pe tot
istoricul, 70 de numere `#N` apar DOAR în corpuri, niciodată în subiect. Printre
ele #214 — PR deschis, draft, chiar acum — și #198 / #233, issue-uri deschise. Un
tipar larg le-ar declara „aterizate pe main" și ar cere adnotarea `(merged)` pentru
ele; STATE.md chiar îl listează pe #214 ca PR deschis, deci garda ar cere ștergerea
unei informații corecte. E tiparul `IZZ-0266`: un fals-pozitiv care aruncă lucruri
legitime costă mai mult decât un fals-negativ care tace. De-aia tiparele sunt
stricte și se aplică DOAR pe subiect.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PR_REF = re.compile(r"#(\d+)")
PR_MERGED_ANNOT = re.compile(r"#(\d+)[^#\n]*\bmerged\b", re.I)
MERGE_COMMIT = re.compile(r"Merge pull request #(\d+)")
# Convenția de squash a GitHub: numărul e ultimul lucru din subiect. Ancorat la
# final tocmai ca un „(#123)" din mijlocul unei fraze să nu conteze.
SQUASH_SUBIECT = re.compile(r"\(#(\d+)\)\s*$")

_SEP_CAMP = "\x00"   # între subiect și corp, în IEȘIREA lui git
_SEP_REC = "\x01"    # între commit-uri, idem
# `%x00`/`%x01` sunt escape-uri pe care le expandează GIT. Nu interpola aici
# octeții reali: `execve` nu poate transporta un NUL într-un argument, iar apelul
# pică cu `ValueError: embedded null byte`. S-a întâmplat (2026-09-04) și a trecut
# nedetectat local, fiindcă pe clona shallow testul care atinge calea era sărit.
_FORMAT = "--format=%s%x00%b%x01"


def sectiune_open(state_md: str) -> str:
    m = re.search(r"^## Open\s*$", state_md, re.M)
    if not m:
        return ""
    rest = state_md[m.end():]
    m2 = re.search(r"^## ", rest, re.M)
    return rest[:m2.start()] if m2 else rest


def pr_uri_mentionate(bloc: str) -> set[int]:
    return {int(n) for n in PR_REF.findall(bloc)}


def pr_uri_adnotate_merged(bloc: str) -> set[int]:
    return {int(n) for n in PR_MERGED_ANNOT.findall(bloc)}


def pr_uri_din_istoric(iesire_git: str) -> set[int]:
    """Numerele de PR dintr-o ieșire `git log` formatată cu `_FORMAT`.

    Pură — ca modurile de aterizare să poată fi testate fără un repo real.
    Se uită DOAR la subiect: vezi docstringul modulului pentru măsurătoarea care
    exclude corpurile.
    """
    gasite: set[int] = set()
    for inregistrare in iesire_git.split(_SEP_REC):
        subiect = inregistrare.partition(_SEP_CAMP)[0].strip()
        if not subiect:
            continue
        gasite.update(int(n) for n in MERGE_COMMIT.findall(subiect))
        squash = SQUASH_SUBIECT.search(subiect)
        if squash:
            gasite.add(int(squash.group(1)))
    return gasite


def istoric_trunchiat() -> bool:
    """True pe o clonă shallow, unde un verde al gărzii nu are acoperire.

    Măsurat 2026-09-04 în sesiunea web: clona locală era shallow (istoric din
    09-02), iar garda trecea în tăcere pe două zile de istoric. `RuntimeError`-ul
    de mai jos NU prinde cazul ăsta — pe shallow `git log` reușește, doar că
    întoarce mai puțin.
    """
    iesire = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    return iesire.returncode == 0 and iesire.stdout.strip() == "true"


def pr_uri_mergeuite_pe_main() -> set[int]:
    """PR-uri aterizate pe main, prin merge commit sau prin squash.

    În CI (checkout pe branch-ul PR) ref-ul local `main` lipsește adesea.
    Încercăm origin/main, apoi main, apoi --all.

    Cele două `--grep` sunt un pre-filtru ieftin (SAU, nu ȘI): restrâng ieșirea
    la commit-urile care ar putea conține un număr de PR. Potrivirea strictă,
    ancorată pe subiect, se face în `pr_uri_din_istoric`.

    `--all` e ultima variantă și e mai permisivă: ar putea vedea un `(#N)` de pe
    o ramură neaterizată. Măsurat 2026-09-04 pe repo real: zero astfel de subiecte
    în afara lui main — GitHub scrie `(#N)` abia la merge. Dacă apare vreodată
    unul, aici e locul de îngustat.
    """
    for ref in ("origin/main", "main", "--all"):
        iesire = subprocess.run(
            [
                "git", "log", ref, "-E",
                "--grep=Merge pull request #[0-9]+",
                r"--grep=\(#[0-9]+\)",
                _FORMAT,
            ],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        if iesire.returncode == 0:
            return pr_uri_din_istoric(iesire.stdout)
    raise RuntimeError(
        "nu pot citi istoricul de merge — verifică fetch-depth: 0 în tests.yml"
    )


def incalcari_pr_fantoma(state_md: str, mergeuite: set[int]) -> list[str]:
    bloc = sectiune_open(state_md)
    if not bloc:
        return ["STATE.md nu are secțiunea ## Open"]
    fantome = sorted((pr_uri_mentionate(bloc) & mergeuite) - pr_uri_adnotate_merged(bloc))
    return [
        f"#{n} e deja merge-uit pe main, dar stă în ## Open fără adnotarea (merged)"
        for n in fantome
    ]


def test_niciun_pr_fantoma_in_state_open():
    if istoric_trunchiat():
        motiv = (
            "clonă shallow: garda vede doar istoricul descărcat, deci un verde aici "
            "nu acoperă PR-urile mai vechi. Local: `git fetch --unshallow`."
        )
        # În CI istoricul complet e promis de `fetch-depth: 0`. Dacă lipsește,
        # verdictul e fals și trebuie să pice zgomotos, nu să fie sărit tăcut.
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail(f"fetch-depth: 0 lipsește din workflow — {motiv}")
        pytest.skip(motiv)
    state = (ROOT / "specs" / "STATE.md").read_text(encoding="utf-8")
    incalcari = incalcari_pr_fantoma(state, pr_uri_mergeuite_pe_main())
    assert not incalcari, "\n".join(incalcari)


def test_garda_pr_fantoma_pica_pe_pr_deja_mergeuit():
    state = "## Open\n\n- ceva despre #99\n\n## Standing\n"
    assert incalcari_pr_fantoma(state, {99})


def test_garda_pr_fantoma_accepta_adnotarea_merged():
    state = "## Open\n\n- **F4 (#99, merged).**\n\n## Standing\n"
    assert not incalcari_pr_fantoma(state, {99})


def test_garda_pr_fantoma_ignora_pr_neintegrat():
    state = "## Open\n\n- PR-uri deschise: #50 #60\n\n## Standing\n"
    assert not incalcari_pr_fantoma(state, {99})


# --- modurile de aterizare (vezi docstringul modulului) ---------------------

def _istoric(*perechi: tuple[str, str]) -> str:
    """Construiește o ieșire `git log` ca cea produsă de `_FORMAT`."""
    return "".join(f"{s}{_SEP_CAMP}{c}{_SEP_REC}" for s, c in perechi)


def test_modul_1_merge_commit_e_detectat():
    istoric = _istoric(("Merge pull request #248 from Ramanul/ci-paralel", "corp\n"))
    assert pr_uri_din_istoric(istoric) == {248}


def test_modul_2_squash_din_subiect_e_detectat():
    """Cazul care lipsea: 6 din ultimele 13 aterizări pe main arată așa."""
    istoric = _istoric(
        ("ci: bump actions/setup-python from 5.6.0 to 7.0.0 (#259)", ""),
        ("rules: §10 — permite conectorul MCP Cloudflare (#243)", "corp\n"),
    )
    assert pr_uri_din_istoric(istoric) == {259, 243}


def test_modul_3_squash_fara_referinta_ramane_nedetectabil():
    """Limita reală a sursei, pinuită cu commitul care a produs incidentul.

    d9e3664 a adus PR #247 pe main fără să-l pomenească nicăieri. Dacă testul
    ăsta începe să pice, înseamnă că cineva a găsit o cale — atunci docstringul
    modulului trebuie rescris, nu testul șters.
    """
    istoric = _istoric(
        ("feat(home): prospețime 72h pe homepage",
         "Integrează filtrul de prospețime 72h pe homepage și testele aferente.\n"),
    )
    assert pr_uri_din_istoric(istoric) == set()


def test_referinta_libera_din_corp_nu_conteaza_ca_merged():
    """Anti-regresie pentru fals-pozitivul care ar arunca informație corectă.

    Corpuri reale de pe main. #198 și #233 sunt issue-uri DESCHISE, #214 e un PR
    DESCHIS pe care STATE.md îl listează chiar în `## Open`. Un tipar mai larg
    le-ar declara aterizate și ar cere adnotarea `(merged)` pentru ele — adică
    ar cere ștergerea unei informații corecte.
    """
    istoric = _istoric(
        ("fix: fa lucrurile amanate, si pune o garda care face amanarea sa expire",
         "§12, F4, Axa 3, arhiva #198, masuratoarea de trafic\n"),
        ("docs: nota de sesiune", "vezi #214 si firul #233 pentru context\n"),
    )
    assert pr_uri_din_istoric(istoric) == set()


def test_paranteza_din_mijlocul_subiectului_nu_conteaza():
    istoric = _istoric(("revert: schimbarea (#231) care a stricat harta", ""))
    assert pr_uri_din_istoric(istoric) == set()


def test_formatul_git_nu_transporta_octeti_nuli():
    """Regresie pentru bug-ul de mai sus — separatorii se lasă pe seama lui git."""
    assert "\x00" not in _FORMAT and "\x01" not in _FORMAT
    assert _FORMAT == "--format=%s%x00%b%x01"


def test_pr_uri_mergeuite_chiar_interogheaza_git():
    """Cale reală, nu doar funcția pură: apelul subprocess trebuie să și meargă."""
    if istoric_trunchiat():
        pytest.skip("clonă shallow — rezultatul n-ar fi comparabil")
    mergeuite = pr_uri_mergeuite_pe_main()
    assert mergeuite, "niciun PR aterizat găsit pe un istoric complet"
    # #248 a aterizat prin merge commit, #243 prin squash — câte unul din fiecare
    # mod detectabil, ca testul să pice dacă se pierde vreunul.
    assert {243, 248} <= mergeuite
