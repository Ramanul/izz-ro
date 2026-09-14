"""Garzi pentru poarta de stare partajata (`tests/poarta_stare.py`).

DE CE EXISTA. Poarta e utila doar cat timp marcajul e COMPLET. Un test nou care citeste
`data/articles.json` si ramane nemarcat readuce exact defectul pe care poarta il inchide —
si l-ar readuce tacut, fiindca nimic nu l-ar semnala.

Lectia e din IZZ-0371 si IZZ-0379, doua incidente cu aceeasi forma: o garda scrisa ca LISTA
de fisiere, care a ramas in urma repo-ului. `test_no_retired_origin_...` verifica trei
fisiere si rata trei; garda de sub-punct verifica o trimitere din paisprezece. Asa ca garda
de mai jos MATURA arborele de teste, nu enumera fisiere: ce nu e cunoscut, pica.
"""
from __future__ import annotations

import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

import pytest

import poarta_stare

ROOT = Path(__file__).resolve().parents[1]
TESTE = ROOT / "tests"

# Idiomurile prin care un test ajunge la starea COMISA si MUTABILA — construita din `ROOT`,
# deci calea reala din repo, nu una redirectionata in `tmp_path`. Cele doua forme sunt exact
# cele folosite azi in suita: `os.path.join(ROOT, "data", "articles.json")` si
# `ROOT / "specs" / "STATE.md"`. O mentiune in docstring sau intr-o lista de siruri NU se
# potriveste, fiindca nu construieste calea.
_MUTABILE = (("data", "articles.json"), ("specs", "STATE.md"))
_TIPARE = tuple(
    re.compile(
        rf'(?:os\.path\.join\(\s*ROOT\s*,\s*"{director}"\s*,\s*"{re.escape(fisier)}"'
        rf'|ROOT\s*/\s*"{director}"\s*/\s*"{re.escape(fisier)}")'
    )
    for director, fisier in _MUTABILE
)

# Scutiri, fiecare cu motivul ei. NU o lista care creste: fiecare rand spune de ce testul
# ramane BLOCANT desi citeste stare mutabila.
#
#   · `test_reguli.py` — citeste `specs/STATE.md` doar ca sa-i numere liniile fata de
#     plafonul pe care si-l declara singur. Plafonul e o proprietate a DOCUMENTULUI, sub
#     control editorial: se incalca numai prin commit-ul cuiva, niciodata prin cresterea
#     starii, deci nu poate flipui intre doua rulari pe acelasi head. Ramane blocant.
SCUTIRI = {"test_reguli.py": "numara liniile lui STATE.md fata de plafonul declarat"}


def _doar_cod(sursa: str) -> str:
    """Sursa fara proza: comentarii si siruri pe mai multe linii (docstring-uri) scoase.

    DE CE. Prima versiune matura textul brut si se prindea pe ea insasi: comentariul care
    EXPLICA idiomul e, la nivel de text, identic cu idiomul. Acelasi fals pozitiv ar lovi
    orice test care isi documenteaza intrarile — adica exact testele scrise cum cere repo-ul.

    Se scot doua clase, amandoua proza: `COMMENT` si sirurile care contin un `\\n` (triple-quoted).
    Sirurile de pe un rand RAMAN, fiindca idiomul insusi e facut din ele (`"data"`,
    `"articles.json"`) — scoase, garda n-ar mai avea ce cauta.

    Fisierul nesintactic se intoarce neatins: o garda nu are voie sa devina oarba pe un
    fisier stricat, iar un test care nu se parseaza pica oricum la colectare.
    """
    try:
        jetoane = list(tokenize.generate_tokens(io.StringIO(sursa).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return sursa
    linii = sursa.splitlines(keepends=True)
    for jeton in jetoane:
        proza = jeton.type == tokenize.COMMENT or (
            jeton.type == tokenize.STRING and "\n" in jeton.string
        )
        if not proza:
            continue
        # ALBIRE pe loc, nu `untokenize`: reconstruirea sursei din jetoane normalizeaza
        # spatierea (`os .path .join (`) si tiparele nu se mai potrivesc — masurat la a doua
        # rulare, proba pozitiva a iesit goala. Aici raman si offseturile, si formatarea.
        (r0, c0), (r1, c1) = jeton.start, jeton.end
        for rand in range(r0 - 1, r1):
            inceput = c0 if rand == r0 - 1 else 0
            sfarsit = c1 if rand == r1 - 1 else len(linii[rand].rstrip("\n"))
            linie = linii[rand]
            capat = linie[len(linie.rstrip("\n")):]
            corp = linie.rstrip("\n")
            linii[rand] = corp[:inceput] + " " * (sfarsit - inceput) + corp[sfarsit:] + capat
    return "".join(linii)


def _module_care_citesc_stare_mutabila() -> set[str]:
    gasite = set()
    for cale in sorted(TESTE.glob("test_*.py")):
        cod = _doar_cod(cale.read_text(encoding="utf-8"))
        if any(tipar.search(cod) for tipar in _TIPARE):
            gasite.add(cale.name)
    return gasite


def _module_cu_test_marcat() -> set[str]:
    iesire = subprocess.run(
        [sys.executable, "-m", "pytest", str(TESTE), "-m", poarta_stare.MARCAJ,
         "--collect-only", "-q", "-p", "no:randomly"],
        cwd=ROOT, capture_output=True, text=True, check=False, timeout=300,
    )
    assert iesire.returncode == 0, f"colectarea marcajului a esuat:\n{iesire.stdout[-2000:]}"
    return {
        linie.split("::", 1)[0].rsplit("/", 1)[-1]
        for linie in iesire.stdout.splitlines()
        if linie.startswith("tests/") and "::" in linie
    }


def test_marcajul_nu_e_gol():
    """Un marcaj golit de o redenumire ar face poarta inerta fara sa pice nimic."""
    assert _module_cu_test_marcat(), (
        "niciun test nu mai poarta marcajul `stare_partajata` — poarta e inerta"
    )


def test_fiecare_modul_care_citeste_starea_mutabila_are_un_test_marcat():
    citesc = _module_care_citesc_stare_mutabila()
    marcate = _module_cu_test_marcat()
    lipsa = sorted(citesc - marcate - set(SCUTIRI))
    assert not lipsa, (
        "module de test care citesc stare COMISA si MUTABILA fara niciun test marcat "
        f"`{poarta_stare.MARCAJ}`: {lipsa}.\n"
        "Verdictul lor poate flipui intre doua rulari pe acelasi head, deci ar inrosi coada "
        "de PR-uri pentru o derivare de stare care nu e a lor. Marcheaza testul, sau adauga "
        "modulul in SCUTIRI cu motivul pentru care NU poate flipui."
    )


def test_scutirile_raman_motivate_si_reale():
    """O scutire pentru un fisier disparut ar ascunde ca garda nu mai acopera nimic."""
    for nume, motiv in SCUTIRI.items():
        assert (TESTE / nume).exists(), f"scutire pentru un fisier care nu exista: {nume}"
        assert motiv.strip(), f"scutire fara motiv: {nume}"


# Probele de mai jos COMPUN idiomul din bucati in loc sa-l scrie intreg. Nu e cochetarie:
# scris intreg, fisierul asta se potriveste pe propriul lui tipar si garda se prinde pe ea
# insasi — masurat la prima rulare. O scutire ar fi ascuns ca proba negativa e chiar cazul
# pozitiv, deci bucatile sunt varianta care pastreaza garda si proba, amandoua reale.
_D, _F = "data", "articles.json"


def test_garda_prinde_un_modul_nou_nemarcat(tmp_path, monkeypatch):
    """Proba negativa: garda chiar pica pe cazul pe care pretinde ca il prinde."""
    fals = tmp_path / "test_fals.py"
    fals.write_text(
        'import os\nROOT = "/x"\n'
        f'def test_x():\n    open(os.path.join(ROOT, "{_D}", "{_F}"))\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(sys.modules[__name__], "TESTE", tmp_path)
    assert _module_care_citesc_stare_mutabila() == {"test_fals.py"}


def test_garda_ignora_mentiunea_din_docstring(tmp_path, monkeypatch):
    """Fals pozitiv care ar face garda de nefolosit: calea doar POMENITA, nu construita."""
    fals = tmp_path / "test_fals.py"
    fals.write_text(
        f'"""Masurat pe {_D}/{_F} la 2026-08-06."""\n'
        f'CAI = ["{_D}/{_F}", "specs/STATE.md"]\n'
        'def test_x():\n    assert CAI\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(sys.modules[__name__], "TESTE", tmp_path)
    assert _module_care_citesc_stare_mutabila() == set()


# --- tabela de decizie a portii ----------------------------------------------------

@pytest.fixture(autouse=True)
def _fara_cache():
    poarta_stare.motiv_neblocant.cache_clear()
    yield
    poarta_stare.motiv_neblocant.cache_clear()


def test_local_ramane_blocant(monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("IZZ_STARE_BLOCANTA", raising=False)
    assert poarta_stare.motiv_neblocant() is None


@pytest.mark.parametrize("eveniment", ["push", "schedule", "workflow_dispatch"])
def test_push_in_main_si_schedule_raman_blocante(monkeypatch, eveniment):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", eveniment)
    monkeypatch.delenv("IZZ_STARE_BLOCANTA", raising=False)
    assert poarta_stare.motiv_neblocant() is None


def test_pr_care_atinge_intrarile_ramane_blocant(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.delenv("IZZ_STARE_BLOCANTA", raising=False)
    monkeypatch.setattr(poarta_stare, "fisiere_atinse_de_pr",
                        lambda: ["generator/config.py", "README.md"])
    assert poarta_stare.motiv_neblocant() is None


def test_pr_care_atinge_un_test_ramane_blocant(monkeypatch):
    """Daca schimbi testul, raspunzi de el — altfel s-ar putea slabi sub poarta lui."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.delenv("IZZ_STARE_BLOCANTA", raising=False)
    monkeypatch.setattr(poarta_stare, "fisiere_atinse_de_pr",
                        lambda: ["tests/test_buget_fisiere.py"])
    assert poarta_stare.motiv_neblocant() is None


def test_pr_strain_de_intrari_devine_neblocant(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.delenv("IZZ_STARE_BLOCANTA", raising=False)
    monkeypatch.setattr(poarta_stare, "fisiere_atinse_de_pr",
                        lambda: ["static/styles.css", "templates/index.html"])
    motiv = poarta_stare.motiv_neblocant()
    assert motiv and "nu atinge" in motiv


def test_diff_indeterminabil_ramane_blocant(monkeypatch):
    """Directia implicita e BLOCANT: un fals permis lasa sa treaca exact PR-ul periculos."""
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.delenv("IZZ_STARE_BLOCANTA", raising=False)
    monkeypatch.setattr(poarta_stare, "fisiere_atinse_de_pr", lambda: None)
    assert poarta_stare.motiv_neblocant() is None


def test_variabila_de_forta_bate_totul(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("IZZ_STARE_BLOCANTA", "1")
    monkeypatch.setattr(poarta_stare, "fisiere_atinse_de_pr", lambda: [])
    assert poarta_stare.motiv_neblocant() is None


def test_diff_ul_e_pe_trei_puncte(monkeypatch):
    """Cu doua puncte, orice commit aterizat pe main intre timp ar parea „atins de PR"."""
    apeluri = []
    monkeypatch.setattr(poarta_stare, "_baza_de_comparatie", lambda: "origin/main")
    monkeypatch.setattr(poarta_stare, "_git",
                        lambda *a: apeluri.append(a) or "generator/config.py\n")
    assert poarta_stare.fisiere_atinse_de_pr() == ["generator/config.py"]
    assert apeluri[-1] == ("diff", "--name-only", "origin/main...HEAD")


def test_intrarile_sunt_cai_reale_din_repo():
    """O intrare mutata ar face poarta sa nu mai recunoasca PR-ul care chiar o atinge."""
    lipsa = [cale for cale in poarta_stare.INTRARI if not (ROOT / cale).exists()]
    assert not lipsa, f"intrari declarate care nu exista pe disc: {lipsa}"
