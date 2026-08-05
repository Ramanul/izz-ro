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
    Scope „session", nu „module": inainte se randa de pana la doua ori per suita
    (`test_pagination` neconditionat + `test_entities_verified` cand lipsea `output/ghiduri`),
    acum o singura data pentru toti consumatorii.
    """
    r = subprocess.run([sys.executable, "-m", "generator.main", "--render-only"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, f"randarea a esuat:\n{r.stdout}\n{r.stderr}"
    assert os.path.isdir(OUT), "output/ lipseste si dupa randare"
    return OUT
