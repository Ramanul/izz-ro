"""CSP-ul sitului e `script-src 'self'` FARA 'unsafe-inline' (render._write_headers).
Orice JS scris in pagina -- un `<script>` cu corp sau un atribut `on*=` -- este blocat
TACUT de browser: nicio eroare in output-ul de build, nicio exceptie in Python, doar o
functionalitate care nu ruleaza la vizitator.

Asta s-a intamplat de doua ori in acelasi repo: un handler inline mort inainte de #96, si
calculatorul de salariu, care n-a functionat NICIODATA in productie (masurat 2026-08-02 pe
https://izz.ro/ghiduri/salariul-minim/: `calcSalariu` undefined, `#calc-results` gol).
Testele de mai jos transforma regula din vigilenta in verificare: JS nou = fisier in
`static/`, inclus cu `<script src=...>`.

Blocurile `<script type="application/ld+json">` sunt date, nu cod: nu se executa, deci CSP
nu le atinge. Sunt permise explicit."""
import os
import re

import pytest

from generator import render

TPL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")

# <script ...> ... </script> cu tot cu atribute, ca sa putem citi `src`/`type`.
_SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script\s*>", re.S | re.I)
# `oninput="..."`, `onclick='...'` etc. Nu prinde `on` din cuvinte precum "button".
_INLINE_HANDLER = re.compile(r"\son[a-z]+\s*=\s*[\"']", re.I)

# Tipuri care NU se executa ca script, deci nu cad sub script-src.
_DATA_TYPES = ("application/ld+json", "application/json", "text/template")


def _templates() -> list:
    return sorted(f for f in os.listdir(TPL_DIR) if f.endswith(".html"))


def test_there_are_templates_to_check():
    """Fara asta, o cale gresita ar face suita de mai jos verde pe zero fisiere."""
    assert len(_templates()) >= 10


@pytest.mark.parametrize("name", _templates())
def test_template_has_no_executable_inline_script(name):
    with open(os.path.join(TPL_DIR, name), encoding="utf-8") as fh:
        html = fh.read()
    for attrs, body in _SCRIPT.findall(html):
        if "src=" in attrs.lower():
            continue  # fisier extern -- exact ce cerem
        if any(t in attrs.lower() for t in _DATA_TYPES):
            continue  # bloc de date, nu cod
        assert not body.strip(), (
            f"{name}: <script> inline cu cod. CSP-ul (`script-src 'self'`) il blocheaza "
            f"tacut. Muta-l in static/ si include-l cu <script src=...>."
        )


@pytest.mark.parametrize("name", _templates())
def test_template_has_no_inline_event_handler(name):
    with open(os.path.join(TPL_DIR, name), encoding="utf-8") as fh:
        html = fh.read()
    found = _INLINE_HANDLER.findall(html)
    assert not found, (
        f"{name}: atribut(e) {found} -- si astea sunt cod inline, blocate de CSP. "
        f"Leaga evenimentele cu addEventListener din fisierul extern."
    )


def test_rendered_calculator_carries_no_inline_code():
    """Randarea propriu-zisa, nu doar sursa template-ului: `_render_calc_salariu` returna
    pana la 2026-08-02 un f-string cu <script> si oninput= in el."""
    html = render._render_calc_salariu(render._env(), {"valoare_curenta": {"brut": 4050}})
    assert "<script" not in html.lower()
    assert not _INLINE_HANDLER.search(html)
    # valoarea ajunge la JS ca date, nu interpolata in cod executabil
    assert 'data-salariu-minim="4050"' in html
    assert 'class="calc-brut"' in html


def test_calculator_script_is_versioned():
    """§16.2: activele /static/ sunt servite `immutable` 30 de zile. Fara hash de continut
    in `?v=`, fixul nu ajunge la vizitatorii care revin -- exact capcana din 2026-07-12."""
    render._ASSET_VER = None  # cache de modul; forteaza recitirea de pe disc
    ver = render._asset_ver()
    assert "calc-salariu.js" in ver
    assert ver["calc-salariu.js"] not in ("", "0"), "fisierul lipseste din static/"
