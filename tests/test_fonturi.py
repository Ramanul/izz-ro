"""Fonturile auto-găzduite: plafon de octeți, zero fișiere moarte, diacritice intacte.

Subsetarea (U+0000-00FF + diacriticele românești) e ce face diferența dintre 76 KB cât se
livrează azi și ~400 KB cât ar cântări familia întreagă. Un subset greșit nu dă eroare: dă
un pătrățel în locul lui „ș" în titlu, pe un singur cuvânt, într-o singură pagină. De aceea
garda verifică explicit că fiecare față comisă acoperă literele românești.

Plafonul de 80 KB nu e ținta din propunere (3 fișiere / 55 KB), ci garda peste starea
măsurată: 5 fețe / 76.224 B. Ținta cere o decizie de design (Inter 600 → 700 sau tăierea
unei fețe); garda cere doar ca nimeni să nu adauge o a șasea față din neatenție.
"""
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTURI = os.path.join(ROOT, "static", "fonts")
FONTS_CSS = os.path.join(ROOT, "static", "fonts.css")
BAZA = os.path.join(ROOT, "templates", "base.html")

PLAFON_OCTETI = 80_000     # măsurat 7 nov: 5 fețe, 76.224 B
MAX_FETE = 5
# Literele fără de care un titlu românesc arată spart, plus semnele tipografice din texte.
DIACRITICE = "ăâîșțĂÂÎȘȚ„”–—…"


def _fete() -> list[str]:
    with open(FONTS_CSS, encoding="utf-8") as fh:
        css = fh.read()
    return re.findall(r"url\(/static/fonts/([\w.-]+\.woff2)\)", css)


def test_fiecare_fata_declarată_există_și_nimic_nu_e_orfan():
    referite = set(_fete())
    assert referite, "fonts.css nu declară nicio față"
    comise = {f for f in os.listdir(FONTURI) if f.endswith(".woff2")}
    lipsa = sorted(referite - comise)
    assert not lipsa, f"declarate în fonts.css, lipsă pe disc: {lipsa}"
    orfane = sorted(comise - referite)
    assert not orfane, (f"fișiere woff2 fără @font-face (se livrează degeaba): {orfane}")


def test_plafonul_de_octeti_si_de_fete():
    fete = _fete()
    total = sum(os.path.getsize(os.path.join(FONTURI, f)) for f in fete)
    assert len(fete) <= MAX_FETE, f"{len(fete)} fețe (max {MAX_FETE}) — vezi docstring"
    assert total <= PLAFON_OCTETI, (f"fonturile cântăresc {total} B, plafon {PLAFON_OCTETI} B. "
                                    "O față nouă cere o decizie, nu un commit.")


@pytest.mark.parametrize("fata", sorted({os.path.basename(f) for f in _fete()}))
def test_fiecare_fata_are_diacriticele_romanesti(fata):
    from fontTools.ttLib import TTFont

    with TTFont(os.path.join(FONTURI, fata)) as font:
        cmap = font.getBestCmap()
    lipsa = [c for c in DIACRITICE if ord(c) not in cmap]
    assert not lipsa, f"{fata} nu acoperă: {''.join(lipsa)}"


def test_preloadurile_din_sablon_arata_spre_fisiere_reale():
    html = open(BAZA, encoding="utf-8").read()
    preload = re.findall(r'rel="preload"\s+href="\{\{ base \}\}/static/fonts/([\w.-]+\.woff2)"',
                         html)
    assert preload, "niciun preload de font în base.html"
    for f in preload:
        assert os.path.exists(os.path.join(FONTURI, f)), f"preload mort: {f}"


def test_subsetul_din_fetch_fonts_acopera_diacriticele():
    """Ce cere `tools/fetch_fonts.py` la descărcare trebuie să acopere diacriticele.

    Garda prinde momentul în care cineva îngustează `RO_UNICODES` ca să scadă fișierul: un
    „ș" care lipsește din subset nu se vede până nu apare în primul titlu.
    """
    sursa = open(os.path.join(ROOT, "tools", "fetch_fonts.py"), encoding="utf-8").read()
    lista = re.search(r"RO_UNICODES\s*=\s*\"([^\"]+)\"", sursa)
    assert lista, "nu găsesc RO_UNICODES în tools/fetch_fonts.py"
    acoperit = set()
    for parte in lista.group(1).split(","):
        parte = parte.strip().replace("U+", "")
        if "-" in parte:
            start, end = parte.split("-")
            acoperit.update(range(int(start, 16), int(end, 16) + 1))
        elif parte:
            acoperit.add(int(parte, 16))
    lipsa = [c for c in DIACRITICE + "aAzZ09" if ord(c) not in acoperit]
    assert not lipsa, f"RO_UNICODES nu acoperă: {''.join(lipsa)}"
