#!/usr/bin/env python3
"""Mutation testing: masoara ce VERIFICA testele, nu doar ce executa.

DE CE EXISTA: coverage-ul spune ce linii se ATING. O linie atinsa de un test care nu o
afirma e acoperita si nepazita in acelasi timp. Unealta asta schimba cate un operator
(`>=`->`>`, `and`->`or`, sterge un `not`) si ruleaza testele care acopera modulul. Daca
testele TREC cu operatorul schimbat, mutantul a SUPRAVIETUIT — adica nimeni nu privea acolo.

Masurat 2026-09-02, prima rulare: patru granite nepazite in `cluster`/`select`/`geo`, toate
off-by-one sau logica booleana. Dosarul: `specs/arhitectura-cuplare.md` sect. 4e.

DOUA CAPCANE, amandoua intalnite si evitate aici — vezi `IZZ-0275`:

1. BYTECODE STALE. Doi mutanti succesivi pe acelasi fisier pot iesi cu ACEEASI marime in
   ACEEASI secunda, iar invalidarea `.pyc` se face pe (mtime in secunde, marime) — deci
   Python ruleaza bytecode-ul mutantului ANTERIOR si raporteaza un supravietuitor fals.
   De-aia: `PYTHONDONTWRITEBYTECODE=1` SI stergerea `__pycache__` inainte de fiecare rulare.
2. SETUL DE TESTE. Un modul „fara supravietuitori" pentru ca fisierul care il acopera n-a
   fost inclus in rulare e o masuratoare falsa, nu o veste buna. Perechile din `TINTE` sunt
   masurate, nu ghicite; cand adaugi un modul, verifica intai ca testele alese chiar il ating.

NU MUTEAZA REPO-UL. Lucreaza pe o copie in /tmp (`generator/` si `tests/` copiate, restul
prin symlink), deci o intrerupere nu lasa un modul stricat in working tree.

    python tools/mutanti.py                # sweep complet, determinist (~2 min)
    python tools/mutanti.py --regresie     # doar granitele deja gasite (~5 s)
    python tools/mutanti.py --modul geo    # un singur modul

CE NU ACOPERA: `render.py`, cel mai mare hotspot al repo-ului. Testele care il acopera
randeaza `output/`, deci un sweep ar dura ore. Plasa lui e `tools/echivalenta.py`.
"""
import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import token
import tokenize

ROOT = pathlib.Path(__file__).resolve().parent.parent

# modul -> fisierele de test care il ACOPERA (masurat: fiecare a fost rulat si atinge modulul)
TINTE = {
    "util":    ["test_util.py", "test_util_edge.py", "test_slug_stabil.py",
                "test_titlu_doar_data.py"],
    "guard":   ["test_guard.py"],
    "cluster": ["test_cluster.py", "test_dedup_intre_surse.py"],
    "geo":     ["test_geo.py", "test_localities.py", "test_atribuire_gold.py"],
    # `select.py` a fost extras din `render.py`, deci testele lui au ramas cu numele vechi.
    # Omiterea lui `test_render_editorial.py` a produs doi supravietuitori falsi (IZZ-0275).
    "select":  ["test_render_editorial.py", "test_substanta_sursa.py",
                "test_anunt_oficial_fara_teaser.py", "test_title_quality_audit.py"],
}

MUTATII = [
    (r"(?<![<>=!])>=(?!=)",   ">",  ">= -> >"),
    (r"(?<![<>=!])<=(?!=)",   "<",  "<= -> <"),
    (r"(?<![<>=!])>(?![=>])", ">=", ">  -> >="),
    (r"\band\b",              "or", "and -> or"),
    (r"\bnot\s+",             "",   "sterge not"),
]

# Granitele gasite pe 2026-09-02 si pazite de atunci. `--regresie` verifica DOAR ca raman
# ucise: e verificarea ieftina de rulat inainte de un refactor pe modulele astea.
REGRESIE = [
    ("cluster", 40,  r"\band\b",            "or"),   # _similar: conjunctie, nu disjunctie
    ("cluster", 40,  r"(?<![<>=!])>=(?!=)", ">"),    # _similar: pragul de tokeni, atins exact
    ("cluster", 75,  r"\band\b",            "or"),   # _strict_match: absorbtia cross-run
    ("cluster", 75,  r"(?<![<>=!])>=(?!=)", ">"),    # _strict_match: pragul de 4 tokeni
    ("cluster", 110, r"\band\b",            "or"),   # attach_recent: garda pe entitati
    ("select",  37,  r"(?<![<>=!])>=(?!=)", ">"),    # _dedup: 4 cuvinte comune = duplicat
    ("select",  108, r"(?<![<>=!])<=(?!=)", "<"),    # _titlu_scurt: taiere la limita exacta
    ("geo",     338, r"\band\b",            "or"),   # gazetteer: randurile stricate se arunca
]

ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


def _atelier() -> pathlib.Path:
    """Copie de lucru in /tmp: cod copiat, date prin symlink (25 MB pe care nu-i dublam)."""
    lucru = pathlib.Path(tempfile.mkdtemp(prefix="izz-mutanti-"))
    for d in ("generator", "tests"):
        shutil.copytree(ROOT / d, lucru / d,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for x in ("data", "templates", "static", "content", "tools", "specs",
              "moderation.yaml", "requirements.txt", "ruff.toml"):
        tinta = ROOT / x
        if tinta.exists():
            (lucru / x).symlink_to(tinta)
    return lucru


def _curata(lucru: pathlib.Path) -> None:
    for d in lucru.rglob("__pycache__"):
        shutil.rmtree(d, ignore_errors=True)


def _testele_trec(lucru: pathlib.Path, fisiere: list) -> bool | None:
    cai = [str(lucru / "tests" / f) for f in fisiere if (lucru / "tests" / f).exists()]
    if not cai:
        return None
    _curata(lucru)
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", *cai, "-q", "--no-header",
                            "-p", "no:cacheprovider"],
                           cwd=lucru, capture_output=True, text=True, timeout=600, env=ENV)
    except subprocess.TimeoutExpired:
        return None
    return r.returncode == 0        # True = trec = mutantul a SUPRAVIETUIT


def _incearca(lucru, modul, nr, tipar, inlocuire) -> bool | None:
    """Aplica un mutant pe linia `nr` (1-indexata), ruleaza, restaureaza. None = inaplicabil.

    `tipar` e fie un regex (modul --regresie, unde linia e cunoscuta si e cod), fie perechea
    (coloana_start, coloana_stop) venita din `_candidati`, care taie exact tokenul.
    """
    p = lucru / "generator" / f"{modul}.py"
    orig = p.read_text(encoding="utf-8")
    linii = orig.split("\n")
    if nr > len(linii):
        return None
    linie = linii[nr - 1]
    if isinstance(tipar, tuple):
        c0, c1 = tipar
        mutata = linie[:c0] + inlocuire + linie[c1:]
    else:
        mutata = re.sub(tipar, inlocuire, linie, count=1)
    if mutata == linie:
        return None
    linii[nr - 1] = mutata
    p.write_text("\n".join(linii), encoding="utf-8")
    try:
        return _testele_trec(lucru, TINTE[modul])
    finally:
        p.write_text(orig, encoding="utf-8")
        _curata(lucru)


def _candidati(modul: str):
    """(nr_linie, tipar, inlocuire, eticheta, textul liniei) — determinist, in ordinea din fisier.

    Selectia se face pe TOKENI, nu pe text. Prima versiune filtra liniile cu `#` sau ghilimele
    si atat — ceea ce lasa sa treaca INTERIORUL docstring-urilor si comentariile de la capatul
    liniei. Rezultatul: 13 din 33 de „supravietuitori" din primul sweep erau proza — sageata
    `->` dintr-un comentariu, mutata in `->=`. Zgomot care umfla numitorul si ascunde
    supravietuitorii reali. `tokenize` stie exact ce e cod si ce nu; `->` e un singur token,
    deci nu se mai confunda cu operatorul `>`.
    """
    cale = ROOT / "generator" / f"{modul}.py"
    linii = cale.read_text(encoding="utf-8").split("\n")
    with open(cale, "rb") as fh:
        jetoane = list(tokenize.tokenize(fh.readline))

    for jeton in jetoane:
        if jeton.start[0] != jeton.end[0]:
            continue                      # token pe mai multe linii (sir triplu) — nu se muta
        cheie = jeton.string
        if jeton.type == token.OP and cheie in (">=", "<=", ">"):
            inlocuire = {">=": ">", "<=": "<", ">": ">="}[cheie]
        elif jeton.type == token.NAME and cheie in ("and", "not"):
            inlocuire = "or" if cheie == "and" else ""
        else:
            continue
        nr, c0 = jeton.start[0], jeton.start[1]
        c1 = jeton.end[1]
        eticheta = f"{cheie} -> {inlocuire or '(sters)'}"
        yield nr, c0, c1, inlocuire, eticheta, linii[nr - 1].strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--modul", choices=sorted(TINTE), help="doar modulul asta")
    ap.add_argument("--regresie", action="store_true",
                    help="doar granitele deja gasite; iese 1 daca vreuna a redevenit nepazita")
    args = ap.parse_args()

    lucru = _atelier()
    try:
        if args.regresie:
            inviati = []
            for modul, nr, tipar, inlocuire in REGRESIE:
                stare = _incearca(lucru, modul, nr, tipar, inlocuire)
                eticheta = {None: "INAPLICABIL (linia s-a mutat?)",
                            True: "SUPRAVIETUIT", False: "ucis"}[stare]
                print(f"  {modul}.py:{nr:<5} {eticheta}")
                if stare is not False:
                    inviati.append(f"{modul}.py:{nr}")
            if inviati:
                print("\n!! granite redevenite nepazite: " + ", ".join(inviati))
                print("   daca linia doar s-a mutat, actualizeaza REGRESIE; altfel s-a pierdut un test.")
                return 1
            print("\nToate granitele din 2026-09-02 sunt in continuare pazite.")
            return 0

        module = [args.modul] if args.modul else sorted(TINTE)
        ucisi = supravietuitori = 0
        detalii = []
        for modul in module:
            for nr, c0, c1, inlocuire, eticheta, linie in _candidati(modul):
                stare = _incearca(lucru, modul, nr, (c0, c1), inlocuire)
                if stare is None:
                    continue
                if stare:
                    supravietuitori += 1
                    detalii.append(f"  {modul}.py:{nr:<5} {eticheta:<12} {linie[:66]}")
                else:
                    ucisi += 1
            print(f"  {modul:<9} gata ({ucisi} ucisi / {supravietuitori} supravietuitori cumulat)")

        total = ucisi + supravietuitori
        print(f"\n=== {ucisi} ucisi, {supravietuitori} supravietuitori din {total} mutanti ===")
        if total:
            print(f"    rata de ucidere: {100 * ucisi / total:.0f}%")
        if detalii:
            print("\nSUPRAVIETUITORI (testele NU au observat schimbarea):")
            print("\n".join(detalii))
            print("\nUn supravietuitor NU e automat un bug: poate fi mutant ECHIVALENT (cele doua")
            print("variante se comporta identic pe orice intrare reala). Judeca-l, nu-l repara orb —")
            print("`IZZ-0277` e un exemplu de supravietuitor lasat deliberat in pace, cu motiv scris.")
        return 0
    finally:
        shutil.rmtree(lucru, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
