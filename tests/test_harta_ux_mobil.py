"""Gărzi pentru problemele de utilizare raportate pe 17 oct 2026 (Android + desktop).

1. Atingerea unei forme lăsa un chenar negru pătrat: regula UA `:focus{outline:auto 5px}` se
   aplică elementelor SVG focusabile și la click/atingere, nu doar la tastatură.
2. `.legend-bands{display:flex}` anula atributul `hidden`: legenda arăta ambele scări deodată.
3. Interfața scria „1 regiuni · 1 județe" și „46 evenimente" (fără acordul numeralului).
4. Pe telefon nu exista mărire cu două degete. Gestul în sine e verificat cu degete reale în
   `tools/harta_dom_check.py` (secțiunea GESTURI TACTILE); aici se apără doar cablarea.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "static" / "harta-stiri" / "harta-stiri.css").read_text(encoding="utf-8")
JS = (ROOT / "static" / "harta-stiri" / "harta-stiri.js").read_text(encoding="utf-8")


def test_formele_focusate_nu_primesc_chenarul_browserului():
    regula = re.search(r"([^{}]*\.map-uat:focus[^{}]*)\{outline:none\}", CSS)
    assert regula and ".map-county:focus" in regula.group(1), (
        "fără `.map-county:focus,.map-uat:focus{outline:none}` revine chenarul negru la atingere")
    # indicatorul pentru tastatură rămâne, ca contur al formei
    assert re.search(r"\.map-uat:focus-visible\{[^}]*stroke:", CSS)


def test_atributul_hidden_castiga_peste_display():
    assert "[hidden]{display:none!important}" in CSS


def test_harta_marita_preia_degetul():
    assert re.search(r"\.map-stage\.is-zoomed\{[^}]*touch-action:none", CSS)
    assert 'addEventListener("touchstart", onTouchStart, { passive: false })' in JS


@pytest.mark.skipif(shutil.which("node") is None, reason="node lipseste; testul ruleaza JS-ul livrat")
def test_acordul_numeralului(tmp_path):
    fn = re.search(r"function cate\(n, unu, multe\) \{[\s\S]*?\n  \}", JS)
    assert fn, "nu am gasit `cate` in harta-stiri.js"
    cazuri = [0, 1, 2, 19, 20, 46, 100, 101, 119, 120, 668, 1001, 1020]
    script = fn.group(0) + f"\nconsole.log(JSON.stringify({json.dumps(cazuri)}.map(n => cate(n, 'județ', 'județe'))));"
    cale = tmp_path / "h.js"
    cale.write_text(script, encoding="utf-8")
    rez = subprocess.run(["node", str(cale)], capture_output=True, text=True, timeout=30)
    assert rez.returncode == 0, rez.stderr
    assert json.loads(rez.stdout) == [
        "0 județe", "1 județ", "2 județe", "19 județe", "20 de județe", "46 de județe",
        "100 de județe", "101 județe", "119 județe", "120 de județe", "668 de județe",
        "1001 județe", "1020 de județe"]
