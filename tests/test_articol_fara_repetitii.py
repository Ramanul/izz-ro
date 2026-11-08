"""Pagina de articol nu repetă același lucru (proprietar, 8.11.2026, captura „Jandarmii din Bacău").

Ce fixează: (1) „Notă pentru cititor" apare doar la sănătate și economie, unde decizia
cititorului are miză; pe restul, rândul de stare și dezvăluirea AI spun deja „verifică sursa";
(2) dezvăluirea AI (AI Act art. 50) rămâne pe orice articol generat; (3) un subiect cu același
nume ca județul nu apare a doua oară în banda de context („Bacău Bacău").
"""
import pytest

from generator import render
from tests.test_render_dialectic import _articol


def _pagina(a, topics=()) -> str:
    tpl = render._env().get_template("article.html")
    return tpl.render(**render._base_ctx(
        f"/{a['category']}/{a['slug']}/", a=a, active_cat=a["category"],
        topics=list(topics), people=[], related=[], nav_section="stiri"))


@pytest.mark.parametrize("categorie,are_nota", [
    ("sanatate", True), ("economic", True), ("local", False), ("sport", False)])
def test_nota_pentru_cititor_doar_unde_are_miza(categorie, are_nota):
    html = _pagina(_articol("SYNTHESIS_VALID", category=categorie))
    assert ("Notă pentru cititor" in html) is are_nota
    # dezvăluirea AI e o singură mențiune: bulina `ai-mark` (caseta `ai-note` a fost scoasă 8.11.2026)
    assert 'class="ai-mark"' in html
    assert 'class="ai-note"' not in html


def test_subiectul_cu_numele_judetului_nu_se_repeta():
    a = _articol("SYNTHESIS_VALID", category="local", judet="bacau")
    eticheta = render._env().filters["judet_label"]("bacau")
    html = _pagina(a, topics=[("bacau", eticheta), ("jandarmerie", "Jandarmerie")])
    banda = html[html.find('<div class="context"'):]
    banda = banda[:banda.find("</div>")]
    assert banda.count(f">{eticheta}<") == 1
    assert ">Jandarmerie<" in banda
