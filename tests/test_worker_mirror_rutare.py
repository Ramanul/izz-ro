"""Rutarea 404 -> oglinda gh-pages (`infra/worker-404-mirror.js`).

DE CE EXISTA. Fallback-ul pe oglinda e locul unde o greseala de rutare NU se vede ca eroare,
ci ca continut VECHI servit drept proaspat: prima pagina, o paginare de categorie sau un
sitemap luate de pe oglinda ar raspunde 200 cu continutul de la ultima publicare a oglinzii.
De asta regulile sunt o functie pura (`e_cale_de_oglinda`) si au teste proprii in JS.

Aici sunt doua lucruri pe care testul JS nu le poate apara:

  1. sincronizarea cu Python — workerul tine lista de categorii in JS, pipeline-ul o tine in
     `generator/config.py`. O categorie noua adaugata doar intr-o parte face ca articolele ei
     expirate sa dea 404 in loc sa vina de pe oglinda. La fel pentru numele imaginilor de
     articol, care trebuie sa fie aceleasi cu cele numarate de `tools/count_output.py`.
  2. ca testele JS chiar ruleaza in CI — un fisier de teste pe care nimeni nu-l porneste e
     decor. De asta suita pytest le executa prin `node --test`.
"""
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import config  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKER = os.path.join(ROOT, "infra", "worker-404-mirror.js")
TEST_JS = os.path.join(ROOT, "infra", "worker-404-mirror.test.mjs")


def _sursa() -> str:
    with open(WORKER, encoding="utf-8") as fh:
        return fh.read()


def _set_js(nume: str) -> set[str]:
    """Elementele unui `new Set([...])` din sursa workerului."""
    m = re.search(r"const %s = new Set\(\[(.*?)\]\);" % nume, _sursa(), re.S)
    assert m, f"nu gasesc `const {nume} = new Set([...])` in worker — structura s-a schimbat"
    return {x for x in re.findall(r'"([^"]+)"', m.group(1))}


def test_categoriile_din_worker_sunt_cele_din_pipeline():
    """Lista de categorii a workerului == `config.CATEGORIES`.

    Fara sincronizare, o categorie noua (sau una redenumita — vezi `CATEGORII_REDENUMITE`)
    isi pierde articolele expirate: ele raman pe oglinda, dar workerul nu le mai cere.
    """
    assert _set_js("CATEGORII") == set(config.CATEGORIES), (
        "workerul si pipeline-ul au liste de categorii diferite; adauga categoria si in "
        "`infra/worker-404-mirror.js` (const CATEGORII)")


def test_imaginile_de_articol_sunt_cele_numarate_de_count_output():
    """Lista de imagini a workerului == `IMAGINI` din `tools/count_output.py`.

    Ambele descriu acelasi lucru: ce fisiere pot trai intr-un director de articol. Daca
    difera, o imagine ceruta de o pagina de pe oglinda nu primeste fallback si cititorul
    vede articolul cu poza sparta.
    """
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import count_output  # noqa: E402  (import tardiv: necesita tools/ pe sys.path)
    assert _set_js("IMAGINI_ARTICOL") == count_output.IMAGINI, (
        "workerul si `tools/count_output.py` nu sunt de acord asupra imaginilor de articol")


def test_oglinda_primeste_doar_lista_pozitiva():
    """Workerul nu are o lista de EXCEPTII: are una de permisiuni.

    Garda pe forma, ca `test_determinism_render`: o lista negativa ( „toate in afara de…")
    ar lasa automat orice ruta noua sa cada pe oglinda, inclusiv prima pagina.
    """
    sursa = _sursa()
    assert "SECTIUNI_COADA" in sursa and "CATEGORII" in sursa
    assert "e_cale_de_oglinda" in sursa
    # intoarce 404-ul local cand regula zice nu, si cand oglinda raspunde non-2xx
    assert sursa.count("return raspuns") >= 3


@pytest.mark.skipif(shutil.which("node") is None, reason="node nu e disponibil")
def test_suitea_js_de_rutare_e_verde(tmp_path):
    """Ruleaza testele JS ale regulilor de rutare.

    DE CE PRINTR-UN DIRECTOR TEMPORAR: workerul e `.js`, iar Node il trateaza ca CommonJS fara
    un `package.json` cu `"type": "module"` in director — si `package.json` e in `.gitignore`
    (linia 51), deci un astfel de fisier NU ar ajunge in CI si testul ar pica acolo. Solutia
    fara sa atingem configuratia de deploy: copiem workerul ca `.mjs` (extensia e ESM
    neconditionat) si testul langa el, cu importul rescris. Productia ramane neschimbata.

    `node --test` intoarce non-zero la primul esec, deci assert-ul pe returncode e suficient;
    afisam iesirea ca un esec sa poata fi diagnosticat din log-ul CI, nu doar ghicit.
    """
    worker_dst = tmp_path / "worker-404-mirror.mjs"
    test_dst = tmp_path / "worker-404-mirror.test.mjs"
    shutil.copyfile(WORKER, worker_dst)
    with open(TEST_JS, encoding="utf-8") as fh:
        test_src = fh.read()
    test_dst.write_text(
        test_src.replace('"./worker-404-mirror.js"', '"./worker-404-mirror.mjs"'),
        encoding="utf-8")

    r = subprocess.run(["node", "--test", str(test_dst)], capture_output=True, text=True,
                       cwd=str(tmp_path), timeout=120)
    assert r.returncode == 0, f"testele JS de rutare au picat:\n{r.stdout[-3000:]}\n{r.stderr[-1500:]}"
