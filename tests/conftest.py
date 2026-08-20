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
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")


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
    try:
        r = subprocess.run([sys.executable, "-m", "generator.main", "--render-only"],
                           cwd=ROOT, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        raise AssertionError(
            "randarea a depasit 600 s. Cauza obisnuita: `media/` lipseste din checkout, deci "
            "copertile se regenereaza cu Pillow in loc sa fie copiate. Verifica "
            "`git sparse-checkout list`."
        ) from None
    assert r.returncode == 0, f"randarea a esuat:\n{r.stdout}\n{r.stderr}"
    assert os.path.isdir(OUT), "output/ lipseste si dupa randare"
    return OUT
