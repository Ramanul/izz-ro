"""Fixturi comune suitei.

Exista pentru un singur motiv: trei fisiere de test citeau `output/` si randau DOAR daca
fisierul cautat lipsea, deci dadeau verdict despre orice artefact ramas pe disc — de la alt
commit, de la un build partial, de la rularea anterioara.

Dovada, masurata pe 2026-08-05 inainte de fix, cu codul neatins: am sters o linie din
`output/sitemap.xml` (`/calendar/`) si eticheta „Verificat:" dintr-un ghid randat. Rezultat:

    FAILED tests/test_sitemap_editorial.py::test_paginile_editoriale_sunt_in_sitemap[/calendar/]
    FAILED tests/test_entities_verified.py::test_eticheta_si_avertismentul_se_exclud_pe_fiecare_ghid
    2 failed, 18 passed in 1.79s

1.79 secunde inseamna ca nu s-a randat nimic: testele raportau despre disc, nu despre cod.
Invers, la fel de rau — un artefact vechi dar complet trece testele si ascunde o regresie reala.
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")


# Cat lasam randarea sa dureze. NU o constanta: exact o constanta a rotit tacut aici.
# Cifra dinainte era 600 s, aleasa cand randarea lua ~86 s ("~7x randarea normala"). Pe
# 2026-08-28 aceeasi randare ia 638 s — cu 38 peste plafon — si toate cele cinci fisiere care
# depind de fixtura asta ies ERROR. Nimic nu se stricase: corpusul crescuse de la ~4.600 la
# 10.742 de articole dupa ce `ARTICLE_TTL_DAYS` a trecut 7 -> 30 (#197), iar plafonul fix a
# ramas pe loc. La regim stabilizat (~24.660 de articole, masurat 822/zi x TTL 30) randarea
# ajunge la ~1.450 s, deci orice cifra fixa pe care as pune-o azi ar rota la fel pana in
# octombrie.
#
# De-asta se scaleaza cu corpusul, nu cu calendarul. Masurat 2026-08-28: 638 s / 10.742
# articole = 59 ms/articol pe cutia asta. Factorul de mai jos e 2x acela, ca sa acopere un
# runner de CI mai lent decat mediul de dezvoltare, si tot ramane departe de plafonul implicit
# de 6 ore al GitHub Actions — care e adevaratul lucru de evitat: acolo jobul raporteaza
# "cancelled", nu cauza.
SECUNDE_PER_ARTICOL = 0.12
LIMITA_MINIMA = 900


def _numar_articole() -> int:
    """Cate articole are starea. 0 dacă fisierul lipseste sau nu se poate citi — apelantul
    cade atunci pe LIMITA_MINIMA, care e comportamentul sigur."""
    try:
        with open(os.path.join(ROOT, "data", "articles.json"), encoding="utf-8") as fh:
            date = json.load(fh)
    except (OSError, ValueError):
        return 0
    if isinstance(date, list):
        return len(date)
    if isinstance(date, dict):
        for v in date.values():
            if isinstance(v, list):
                return len(v)
    return 0


def _limita_randare() -> int:
    return max(LIMITA_MINIMA, int(_numar_articole() * SECUNDE_PER_ARTICOL))


@pytest.fixture(scope="session")
def output_randat() -> str:
    """`output/` produs de codul curent, o singura data pe rulare de suita.

    Neconditionat: „randeaza daca lipseste" e exact bug-ul de mai sus, fiindca fisierul
    exista aproape mereu. Un test lent e mai ieftin decat un test care minte.

    O singura randare ajunge fiindca `render.build()` goleste continutul lui `output/` la
    fiecare rulare (generator/render.py, „reset output"), deci artefactul e intreg si
    coerent — nu exista drum prin care un test sa vada jumatate din randarea altcuiva.

    **Adevarat INTR-O rulare; fals intre DOUA rulari concurente** (masurat 2026-08-16).
    `output/` e o cale fixa, partajata, iar „reset output" o goleste fara niciun lock. Doua
    procese `pytest` pornite in paralel pe acelasi clone — tipic: o sesiune si un subagent
    care isi ruleaza fiecare suita — se calca reciproc: unul citeste `output/` exact cand
    celalalt tocmai l-a golit. Simptomul e o ploaie de ERRORS in testele care depind de
    fixtura asta (`test_sitemap_editorial`, `test_pagination`, `test_pagina_404`), care arata
    ca o regresie reala si nu e. Dovada: aceleasi fisiere, rulate SINGURE, dau 12 passed;
    suita intreaga rulata singura dupa aceea, 926 passed / 0 errors.
    **Deci: nu rula doua suite in paralel pe acelasi working tree.** Daca ai nevoie de
    paralelism intre agenti, dă-le `isolation: "worktree"` (CLAUDE.md §19) — clone separate
    inseamna `output/` separate. Inainte de a investiga ERRORS in testele astea, verifica
    intai daca ruleaza altcineva: o suita concurenta e cauza mult mai probabila decat un bug.
    Scope „session", nu „module": inainte se randa de pana la doua ori per suita
    (`test_pagination` neconditionat + `test_entities_verified` cand lipsea `output/ghiduri`),
    acum o singura data pentru toti consumatorii.
    """
    # `timeout` NU e optional (audit 2026-08-20, [T1]). Fara el, o randare care se blocheaza din
    # ORICE motiv opreste suita la infinit, fara niciun mesaj: masurat 421 s si zero iesire, dupa
    # care sesiunea a fost oprita manual. In CI ar arde pana la plafonul implicit de 6 ore si ar
    # raporta „cancelled", nu cauza. Cazul concret care a produs masuratoarea: un checkout fara
    # `media/`, unde `render.build()` regenereaza cu Pillow doua coperti pentru fiecare dintre
    # cele ~3900 de articole in loc sa le copieze din `media/` (stiva prinsa cu `faulthandler`:
    # PIL/Image.resize <- covers._save <- render.build). 600 s = ~7x randarea normala, deci nu
    # se declanseaza pe o masina incarcata, dar taie bucla infinita.
    limita = _limita_randare()
    try:
        r = subprocess.run([sys.executable, "-m", "generator.main", "--render-only"],
                           cwd=ROOT, capture_output=True, text=True, timeout=limita)
    except subprocess.TimeoutExpired:
        raise AssertionError(
            f"TIMEOUT DE RANDARE: a depasit {limita} s (corpus: {_numar_articole()} articole).\n"
            "Astea sunt lucruri DIFERITE, nu le confunda cu un render picat: aici procesul inca "
            "rula cand l-am taiat, deci ori e lent, ori e blocat.\n"
            "  - lent  -> corpusul a crescut peste ce acopera formula din `_limita_randare`; "
            "remasoara si ajusteaza SECUNDE_PER_ARTICOL.\n"
            "  - blocat -> cauza obisnuita e `media/` lipsa din checkout, deci copertile se "
            "regenereaza cu Pillow in loc sa fie copiate. Verifica `git sparse-checkout list`."
        ) from None
    assert r.returncode == 0, (
        f"RANDARE PICATA: a iesit cu cod {r.returncode} in mai putin de {limita} s. "
        "NU e un timeout — procesul a murit singur, cu eroarea de mai jos.\n"
        f"{r.stdout}\n{r.stderr}")
    assert os.path.isdir(OUT), "output/ lipseste si dupa randare"
    return OUT
