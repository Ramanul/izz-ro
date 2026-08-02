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
nu le atinge. Sunt permise explicit.

De ce HTMLParser si nu o expresie regulata: prima versiune inchidea blocurile pe
`</script\\s*>`, iar CodeQL a semnalat-o corect (`py/bad-tag-filter`) -- HTML accepta si
`</script foo>`, pe care regexul nu-l prinde, deci un script inline scris asa ar fi trecut
neobservat. Un filtru de securitate care rateaza cazul ocolit e mai rau decat niciun filtru."""
import os
from html.parser import HTMLParser

import pytest

from generator import render

TPL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates")

# Tipuri care NU se executa ca script, deci nu cad sub script-src.
_DATA_TYPES = ("application/ld+json", "application/json", "text/template")


class _ScriptScan(HTMLParser):
    """Aduna (a) corpurile de <script> executabile si (b) atributele `on*=`."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inline_bodies = []
        self.handlers = []
        self._executable = False

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        self.handlers += [k for k in a if k.startswith("on") and len(k) > 2]
        if tag == "script":
            typ = a.get("type", "").lower()
            self._executable = "src" not in a and not any(t in typ for t in _DATA_TYPES)

    handle_startendtag = handle_starttag

    def handle_data(self, data):
        if self._executable and data.strip():
            self.inline_bodies.append(data.strip())

    def handle_endtag(self, tag):
        if tag == "script":
            self._executable = False


def _scan(html: str) -> _ScriptScan:
    p = _ScriptScan()
    p.feed(html)
    p.close()
    return p


def _templates() -> list:
    return sorted(f for f in os.listdir(TPL_DIR) if f.endswith(".html"))


def test_there_are_templates_to_check():
    """Fara asta, o cale gresita ar face suita de mai jos verde pe zero fisiere."""
    assert len(_templates()) >= 10


def test_the_scan_actually_catches_the_defect():
    """Falsificare inainte de incredere: pe markup-ul VECHI al calculatorului, scanarea
    trebuie sa gaseasca si scriptul, si handlerul -- inclusiv cu tag de inchidere ocolit."""
    old = ('<input oninput="calcSalariu()">'
           '<script>function calcSalariu(){}</script foo>'
           '<script type="application/ld+json">{"a":1}</script>'
           '<script src="/static/x.js"></script>')
    scan = _scan(old)
    assert scan.handlers == ["oninput"]
    assert len(scan.inline_bodies) == 1 and "function calcSalariu" in scan.inline_bodies[0]


@pytest.mark.parametrize("name", _templates())
def test_template_has_no_executable_inline_script(name):
    with open(os.path.join(TPL_DIR, name), encoding="utf-8") as fh:
        scan = _scan(fh.read())
    assert not scan.inline_bodies, (
        f"{name}: <script> inline cu cod. CSP-ul (`script-src 'self'`) il blocheaza tacut. "
        f"Muta-l in static/ si include-l cu <script src=...>."
    )


@pytest.mark.parametrize("name", _templates())
def test_template_has_no_inline_event_handler(name):
    with open(os.path.join(TPL_DIR, name), encoding="utf-8") as fh:
        scan = _scan(fh.read())
    assert not scan.handlers, (
        f"{name}: atribut(e) {scan.handlers} -- si astea sunt cod inline, blocate de CSP. "
        f"Leaga evenimentele cu addEventListener din fisierul extern."
    )


def test_rendered_calculator_carries_no_inline_code():
    """Randarea propriu-zisa, nu doar sursa template-ului: `_render_calc_salariu` returna
    pana la 2026-08-02 un f-string cu <script> si oninput= in el."""
    html = render._render_calc_salariu(render._env(), {"valoare_curenta": {"brut": 4050}})
    scan = _scan(html)
    assert not scan.inline_bodies
    assert not scan.handlers
    # valoarea ajunge la JS ca date, nu interpolata in cod executabil
    assert 'data-salariu-minim="4050"' in html
    assert 'class="calc-brut"' in html


def test_standalone_calculator_page_renders_wired():
    """Pagina de sine statatoare, randata cap-coada. Testul de mai sus acopera doar partial-ul
    prin `_render_calc_salariu` (calea ghidurilor) -- iar exact pagina asta a fost a doua
    suprafata moarta pe live, deci lipsa ei din suita e fix golul care a lasat-o asa."""
    html = render._env().get_template("calculator.html").render(
        **render._base_ctx("/instrumente/calculator-salariu/", salariu_minim=4050))
    scan = _scan(html)
    assert not scan.inline_bodies
    assert not scan.handlers
    assert 'data-salariu-minim="4050"' in html
    assert "/static/calc-salariu.js?v=" in html, "scriptul nu e inclus -> pagina nu calculeaza"


def test_missing_entity_value_does_not_break_the_build():
    """`valoare_curenta: null` in date facea `.get(...).get(...)` sa pice cu AttributeError
    in mijlocul randarii. Pagina trebuie sa se randeze cu valoarea de rezerva, nu sa opreasca
    build-ul pentru un camp gol."""
    assert render._salariu_minim({"valoare_curenta": None}) == render._SALARIU_MINIM_FALLBACK
    assert render._salariu_minim({}) == render._SALARIU_MINIM_FALLBACK
    assert render._salariu_minim(None) == render._SALARIU_MINIM_FALLBACK
    assert render._salariu_minim({"valoare_curenta": {"brut": 4582}}) == 4582


def test_calculator_script_is_versioned():
    """§16.2: activele /static/ sunt servite `immutable` 30 de zile. Fara hash de continut
    in `?v=`, fixul nu ajunge la vizitatorii care revin -- exact capcana din 2026-07-12."""
    render._ASSET_VER = None  # cache de modul; forteaza recitirea de pe disc
    ver = render._asset_ver()
    assert "calc-salariu.js" in ver
    assert ver["calc-salariu.js"] not in ("", "0"), "fisierul lipseste din static/"
