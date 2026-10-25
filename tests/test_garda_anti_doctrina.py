"""Garda anti-doctrinară, mecanizată (specs/plan-paradigma-izz.md §4).

Site-ul trebuie să FIE produsul principiilor sale — în structură și funcționare —, nu să le
predice. Decizia proprietarului (23.10.2026): ideile din care s-au derivat regulile nu se
pomenesc pe site; regulile se explică în limbaj civic, pe /principii/ și /legal/method/, iar
raționamentul complet de proiectare stă în depozitul public de cod.

Testul scanează TOT textul public scris de mână (pagini, șabloane, scripturile din pagină):
un termen cosmologic sau un titlu de carte ajuns acolo e o „fractură deschisă" (Argon R1) —
filosofia iese prin piele. Textele generate (sintezele) sunt acoperite de
`tests/test_render_dialectic.py`.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
INTERZISE = re.compile(
    r"contactul\s+ra|\balienmind\b|legea\s+lui\s+unu|\blegea\s+confuziei\b|channeling|"
    r"densit[aăi]|catalizator|polarit|polariz|\brecolt|liberul\s+arbitru|distorsiun|"
    r"\bspiritual|\bsinele\s+superior|\bcreatorul\s+unic|\bunic\s+creator",
    re.IGNORECASE,
)


def _fisiere():
    for pattern in ("content/**/*.md", "templates/**/*.html", "static/*.js"):
        yield from ROOT.glob(pattern)


def test_nicio_doctrina_in_textul_public():
    gasite = []
    for f in _fisiere():
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in INTERZISE.finditer(text):
            linie = text.count("\n", 0, m.start()) + 1
            gasite.append(f"{f.relative_to(ROOT)}:{linie}: {m.group(0)!r}")
    assert not gasite, "vocabular doctrinar în textul public:\n" + "\n".join(gasite)


def test_garda_chiar_prinde_ce_trebuie():
    """Contra-proba: fără ea, o expresie regulată stricată ar trece testul de mai sus gol."""
    for t in ("Contactul Ra, volumul 1", "nivel spiritual", "densitățile", "Liberul Arbitru"):
        assert INTERZISE.search(t), t
    assert not INTERZISE.search("spirit civic, la 100.000 de locuitori")
