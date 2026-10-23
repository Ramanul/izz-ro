"""Orice `href` cu date din afară trece prin `href_extern` la randare.

DE CE EXISTA (2026-10-23). Semgrep `var-in-href` a semnalat pe #512 `href="{{ s.url }}"`:
escaparea Jinja2 nu oprește `javascript:`, e HTML valid. Calea principală era deja închisă
(`moderation.apply` ascunde articolele cu URL ostil, prin `guard.url_ostil`), dar nu orice
`href` trece prin ea: memoria subiectelor ține rânduri din rulări vechi, creditele de imagine
și catalogul de surse vin pe alte drumuri. Filtrul închide CLASA la locul folosirii; testul de
șablon împiedică un `href` nou să o redeschidă tăcut.
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generator import guard, render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# `{{ canonical }}` e construit din config.SITE["url"], nu din date externe.
_INTERNE = ("base", "canonical")


def test_orice_href_extern_din_sabloane_trece_prin_filtru():
    lipsa = []
    for cale in glob.glob(os.path.join(ROOT, "templates", "*.html")):
        text = open(cale, encoding="utf-8").read()
        for expr in re.findall(r'href="\{\{([^}]*)\}\}', text):
            expr = expr.strip()
            if expr.split()[0].split("|")[0] in _INTERNE:
                continue
            if "href_extern" not in expr:
                lipsa.append(f"{os.path.basename(cale)}: {expr}")
    assert not lipsa, lipsa


def test_corpusul_ostil_devine_diez_la_randare():
    env = render._env()
    tpl = env.from_string('<a href="{{ u | href_extern }}">x</a>')
    for u in guard._CORPUS_URL_OSTIL:
        assert tpl.render(u=u) == '<a href="#">x</a>', u


def test_url_legitim_trece_neschimbat_si_escapat():
    env = render._env()
    tpl = env.from_string('<a href="{{ u | href_extern }}">x</a>')
    assert tpl.render(u="https://www.digi24.ro/stiri/a?b=1&c=2") == \
        '<a href="https://www.digi24.ro/stiri/a?b=1&amp;c=2">x</a>'
    assert tpl.render(u="") == '<a href="#">x</a>'
    assert tpl.render(u=None) == '<a href="#">x</a>'
