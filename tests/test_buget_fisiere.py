"""Bugetul de fisiere al output-ului (`render._image_budget`).

De ce exista testul: pe 2026-08-21 output-ul a trecut plafonul de 20.000 de fisiere al
Cloudflare Pages, deploy-ul a inceput sa fie refuzat si site-ul a stat 21 de ore pe un
release vechi, fara ca nimic din pipeline sa raporteze rosu la timp -- jobul de continut
trecea verde, iar `release-probe` pica 25 de minute mai tarziu cu "izz.ro serveste
63bcc9bd0965, care nu include 51fe7790c026".

Fiecare garda de aici are si un caz NEGATIV: o garda care nu poate pica e mai rea decat
niciuna (IZZ-0177).
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generator import config          # noqa: E402
from generator.render import _image_budget  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Plafonul real al gazdei, masurat prin bracket pe 2026-08-21/22: 19.987 fisiere =
# deploy verde, 20.337 = build picat. NU e citit din documentatia Cloudflare -- proxy-ul
# sesiunii respinge developers.cloudflare.com (CLAUDE.md §16.3).
PLAFON_GAZDA_MASURAT = 20000


def test_bugetul_configurat_sta_sub_plafonul_masurat():
    """Bugetul trebuie sa lase marja sub plafonul gazdei."""
    assert config.OUTPUT_FILE_BUDGET < PLAFON_GAZDA_MASURAT, (
        f"OUTPUT_FILE_BUDGET={config.OUTPUT_FILE_BUDGET} nu lasa marja sub plafonul "
        f"masurat de {PLAFON_GAZDA_MASURAT}. Ridica-l doar cu o masuratoare noua.")


def test_cand_incape_tot_fiecare_articol_primeste_si_arta_si_coperta():
    img, art, cov = _image_budget(1000, budget=10_000, reserve=1_000)
    assert (art, cov) == (1000, 1000)
    assert img == 8000


def test_NEGATIV_bugetul_strans_taie_intai_copertile_nu_arta():
    """Cazul negativ: la buget mic, copertile cad, dar arta ramane la toti."""
    # 1000 articole, 1000 rezerva, buget 2600 -> 1600 fisiere de imagine
    img, art, cov = _image_budget(1000, budget=2600, reserve=1000)
    assert img == 600
    assert art == 600, "arta ar trebui limitata de buget, nu ignorata"
    assert cov == 0, "copertile trebuie sa cada INAINTEA artei"


def test_NEGATIV_bugetul_foarte_strans_lasa_articole_fara_nicio_imagine():
    """Cazul negativ dur: nu incape nici macar o imagine per articol."""
    img, art, cov = _image_budget(1000, budget=1200, reserve=1000)
    assert img == 0
    assert (art, cov) == (0, 0), "sub buget zero nu se scrie nicio imagine"


def test_NEGATIV_bugetul_depasit_de_rezerva_nu_devine_negativ():
    """Rezerva mai mare decat bugetul nu trebuie sa produca numere negative."""
    img, art, cov = _image_budget(500, budget=100, reserve=9_000)
    assert (img, art, cov) == (0, 0, 0)
    assert img >= 0 and art >= 0 and cov >= 0


@pytest.mark.parametrize("n", [0, 1, 10, 500, 3000, 6000, 9000, 20_000])
def test_invariantul_tine_pe_tot_domeniul(n):
    """Nu se promite niciodata mai mult decat incape, si copertile nu depasesc arta."""
    img, art, cov = _image_budget(n)
    assert art + cov <= img, "s-au promis mai multe fisiere decat incap in buget"
    assert cov <= art, "un articol nu poate avea coperta fara arta"
    assert art <= n
    # paginile de articol se scad primele si nu sunt niciodata sacrificate
    total = config.OUTPUT_NON_ARTICLE_RESERVE + n + art + cov
    assert total <= max(config.OUTPUT_FILE_BUDGET, config.OUTPUT_NON_ARTICLE_RESERVE + n)


def test_starea_actuala_incape_cu_o_imagine_per_articol():
    """Tripwire pe starea REALA: cand pica, articolele incep sa ramana fara imagine.

    Nu e o formalitate — pica singur pe masura ce starea creste, cu cateva zile inainte
    ca degradarea sa fie vizibila pe site. Cand pica: coboara ARTICLE_TTL_DAYS sau mută
    imaginile in afara Pages. NU ridica bugetul fara o masuratoare noua a plafonului.
    """
    with open(os.path.join(ROOT, "data", "articles.json"), encoding="utf-8") as fh:
        n = len(json.load(fh))
    _img, art, _cov = _image_budget(n)
    assert art == n, (
        f"{n - art} din {n} articole ar ramane fara imagine. Starea a crescut peste ce "
        f"incape in OUTPUT_FILE_BUDGET={config.OUTPUT_FILE_BUDGET} cu rezerva "
        f"{config.OUTPUT_NON_ARTICLE_RESERVE}. Vezi §17 si specs/STATE.md.")


def test_podeaua_absoluta_ramane_deasupra_starii_curente():
    """Chiar si fara nicio imagine, paginile trebuie sa incapa. Asta e limita dura."""
    with open(os.path.join(ROOT, "data", "articles.json"), encoding="utf-8") as fh:
        n = len(json.load(fh))
    maxim_pagini = config.OUTPUT_FILE_BUDGET - config.OUTPUT_NON_ARTICLE_RESERVE
    assert n <= maxim_pagini, (
        f"{n} articole, dar sub buget incap doar {maxim_pagini} pagini. Aici nicio "
        f"optimizare de imagini nu mai ajuta: trebuie TTL mai mic sau alta gazda.")


# --- plafonul dur al gazdei -------------------------------------------------------
# Bugetul e tinta la care randarea imparte imaginile; plafonul e punctul de la care
# Cloudflare refuza deploy-ul. Un `logging.error` NU opreste nimic: randarea iese cu cod
# 0, jobul de continut ramane verde si esecul reapare in `release-probe` 25 de minute mai
# tarziu. Peste plafon randarea trebuie sa moara zgomotos.

def test_bugetul_sta_sub_plafonul_dur():
    assert config.OUTPUT_FILE_BUDGET < config.OUTPUT_FILE_CEILING
    assert config.OUTPUT_FILE_CEILING <= PLAFON_GAZDA_MASURAT


def _scrie_fisiere(d, cate):
    for i in range(cate):
        (d / f"f{i}.html").write_text("x", encoding="utf-8")


def test_NEGATIV_peste_plafonul_gazdei_randarea_moare_zgomotos(tmp_path, monkeypatch):
    """Cazul negativ care conteaza: peste plafon NU se iese cu cod 0."""
    from generator import render
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    monkeypatch.setattr(config, "OUTPUT_FILE_CEILING", 3)
    monkeypatch.setattr(config, "OUTPUT_FILE_BUDGET", 2)
    _scrie_fisiere(tmp_path, 5)
    with pytest.raises(RuntimeError, match="peste plafonul gazdei"):
        render._write_build_metadata(0)


def test_diagnosticul_supravietuieste_esecului(tmp_path, monkeypatch):
    """build.json se scrie INAINTE de verdict, altfel esecul isi ascunde propria dovada."""
    from generator import render
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    monkeypatch.setattr(config, "OUTPUT_FILE_CEILING", 3)
    monkeypatch.setattr(config, "OUTPUT_FILE_BUDGET", 2)
    _scrie_fisiere(tmp_path, 5)
    with pytest.raises(RuntimeError):
        render._write_build_metadata(0)
    scris = json.loads((tmp_path / "build.json").read_text(encoding="utf-8"))
    assert scris["file_count"] == 6, "numarul care a declansat esecul trebuie sa ramana citibil"


def test_intre_buget_si_plafon_publicarea_merge_mai_departe(tmp_path, monkeypatch):
    """Marja stramta nu trebuie sa doboare publicarea cand deploy-ul ar trece oricum."""
    from generator import render
    monkeypatch.setattr(render, "OUT_DIR", str(tmp_path))
    monkeypatch.setattr(config, "OUTPUT_FILE_BUDGET", 3)
    monkeypatch.setattr(config, "OUTPUT_FILE_CEILING", 50)
    _scrie_fisiere(tmp_path, 5)
    render._write_build_metadata(0)   # avertizeaza, dar nu ridica
    assert (tmp_path / "build.json").exists()
