"""Aria de click a hărții = umplerea poligonului, iar la suprapunere câștigă ultimul pictat.

Issue #454: garda `tools/harta_dom_check.py` raporta 2 puncte din 81 în care browserul
(`elementsFromPoint`) și geometria (`isPointInFill`) nu erau de acord — ILFOV/DAMBOVITA și
CONSTANTA/None. Cauza nu era o eroare de date, ci aria de click: `.map-county` avea valoarea
implicită `visiblePainted`, deci conturul de 1,1 px de ecran (non-scaling-stroke) făcea parte
din arie și, fiind pictat peste vecin, returna pe graniță județul desenat deasupra în loc de
județul care conține punctul.

Testele de aici nu au nevoie de browser: verifică (1) contractul din CSS, (2) modelul din
gardă, (3) geometria reală din `data/map.json` — inclusiv enclava București, care stă în
întregime în Ilfov și e scăpată doar de ordinea de pictare.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MAP = Path("static/harta-stiri/data/map.json")
CSS = Path("static/harta-stiri/harta-stiri.css")
JS = Path("static/harta-stiri/harta-stiri.js")
GARDA = Path("tools/harta_dom_check.py")


def _puncte(path_d: str) -> list[tuple[float, float]]:
    numere = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", path_d)]
    return [(numere[i], numere[i + 1]) for i in range(0, len(numere) - 1, 2)]


def _in_umplere(punct: tuple[float, float], poligon: list[tuple[float, float]]) -> bool:
    """Regula de umplere pe poligoane simple: even-odd == nonzero (fără găuri, fără auto-intersecții)."""
    x, y = punct
    interior = False
    for i in range(len(poligon)):
        x1, y1 = poligon[i - 1]
        x2, y2 = poligon[i]
        if (y1 > y) != (y2 > y):
            if x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
                interior = not interior
    return interior


def _harta() -> tuple[dict[str, list[tuple[float, float]]], tuple[float, float]]:
    date = json.loads(MAP.read_text(encoding="utf-8"))["map"]
    judete = {nume: _puncte(d) for nume, d in date["judete"].items()}
    lat, sus, latime, inaltime = (float(v) for v in date["viewbox"].split())
    assert (lat, sus) == (0.0, 0.0)
    return judete, (latime, inaltime)


def _ordine_de_pictare(judete: dict) -> list[str]:
    """Ordinea din DOM: cheile din map.json, cu județele din COUNTIES_DRAW_LAST la sfârșit."""
    sursa = JS.read_text(encoding="utf-8")
    gasit = re.search(r"const COUNTIES_DRAW_LAST = \[(.*?)\];", sursa)
    assert gasit, "COUNTIES_DRAW_LAST a dispărut din harta-stiri.js"
    ultimele = re.findall(r'"([A-Z]+)"', gasit.group(1))
    assert ultimele, "COUNTIES_DRAW_LAST este gol"
    return ([n for n in judete if n not in ultimele] + [n for n in judete if n in ultimele])


def _proprietar(
    punct: tuple[float, float],
    judete: dict[str, list[tuple[float, float]]],
    ordine: list[str],
) -> str | None:
    """Cine primește clickul: ultimul poligon pictat a cărui umplere conține punctul."""
    for nume in reversed(ordine):
        if _in_umplere(punct, judete[nume]):
            return nume
    return None


def test_aria_de_click_a_poligonului_e_umplerea():
    css = CSS.read_text(encoding="utf-8")
    assert ".map-county,.map-uat{pointer-events:fill}" in css, (
        "aria de click trebuie să fie umplerea, nu umplerea plus conturul (issue #454); "
        "conturul e non-scaling-stroke și se pictează peste vecin"
    )
    # Conturul hărții (strat propriu, peste poligoane) rămâne exclus din aria de click.
    assert ".map-outline{" in css and "pointer-events:none}" in css
    # Țintele tactile transparente rămân singurele care acceptă orice pixel.
    assert ".map-county-hit{fill:#000;fill-opacity:0;stroke:transparent;pointer-events:all" in css


def test_garda_alege_ultimul_poligon_pictat_nu_aria_cutiei():
    sursa = GARDA.read_text(encoding="utf-8")
    inceput = sursa.index("const ownerAt = (sx, sy) => {")
    sfarsit = sursa.index("let checked = 0", inceput)
    corp = sursa[inceput:sfarsit]
    assert "for (let i = paths.length - 1; i >= 0; i -= 1)" in corp, (
        "geometria se citește în ordinea pictării, ca `elementsFromPoint`: ultimul poligon câștigă"
    )
    assert "getBBox" not in corp, (
        "regula veche (aria bbox minimă) nu descrie pictura browserului și rupea pe graniță (#454)"
    )
    assert "isPointInFill" in corp
    assert "isPointInStroke" not in sursa, "conturul nu mai face parte din aria de click"


def test_grila_de_audit_nu_cade_in_doua_judete_deodata():
    judete, (latime, inaltime) = _harta()
    ordine = _ordine_de_pictare(judete)
    assert len(judete) == 42 and len(ordine) == 42
    cu_proprietar = 0
    for i in range(1, 10):
        for j in range(1, 10):
            punct = (latime * i / 10, inaltime * j / 10)
            contin = [nume for nume in ordine if _in_umplere(punct, judete[nume])]
            assert len(contin) <= 1, (
                f"punctul {punct} stă în umplerea a două județe {contin}: acolo browserul și "
                "geometria pot da răspunsuri diferite, deci grila de audit nu mai e o probă"
            )
            cu_proprietar += bool(contin)
    # Grila e o probă, nu o demonstrație: dacă parserul s-ar strica, testul ar trece degeaba.
    assert cu_proprietar >= 50, f"doar {cu_proprietar} din 81 de puncte au proprietar"


def test_enclava_bucuresti_castiga_prin_ordinea_de_pictare():
    judete, _ = _harta()
    bucuresti = judete["BUCURESTI"]
    xs = [p[0] for p in bucuresti]
    ys = [p[1] for p in bucuresti]
    centru = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    # Premisa: orașul stă în întregime în Ilfov (nu e o gaură în geometrie, e o suprapunere).
    assert _in_umplere(centru, judete["ILFOV"])
    assert all(_in_umplere(varf, judete["ILFOV"]) for varf in bucuresti)
    # În ordinea din fișier ar câștiga Ilfov; regula din JS îl mută pe București la sfârșit.
    assert _proprietar(centru, judete, list(judete)) == "ILFOV"
    assert _proprietar(centru, judete, _ordine_de_pictare(judete)) == "BUCURESTI"


def test_toate_judetele_au_o_geometrie_utilizabila():
    judete, _ = _harta()
    for nume, poligon in judete.items():
        assert len(poligon) >= 3, nume
        arie = 0.0
        for i in range(len(poligon)):
            x1, y1 = poligon[i - 1]
            x2, y2 = poligon[i]
            arie += x1 * y2 - x2 * y1
        assert abs(arie) / 2 > 1, f"{nume} are arie ~0, deci nu poate primi niciun click"
