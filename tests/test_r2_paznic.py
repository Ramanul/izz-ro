"""Paznicul de cost R2 (`infra-watchdog/r2-paznic.js`) — legat de suita pytest.

Logica e JavaScript si are testele ei in `infra-watchdog/r2-paznic.test.mjs`. Fara fisierul
asta, CI (care ruleaza pytest) nu le-ar executa niciodata, iar un prag stricat ar ajunge
neobservat intr-un cod a carui singura treaba e sa opreasca o factura.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

RADACINA = Path(__file__).resolve().parent.parent
MODUL = RADACINA / "infra-watchdog" / "r2-paznic.js"
TESTE_JS = RADACINA / "infra-watchdog" / "r2-paznic.test.mjs"


def _numar(nume: str) -> float:
    sursa = MODUL.read_text(encoding="utf-8")
    gasit = re.search(rf"export const {nume} = ([0-9.]+);", sursa)
    assert gasit, f"{nume} nu mai e o constanta exportata in r2-paznic.js"
    return float(gasit.group(1))


def test_pragul_de_taiere_ramane_sub_gratuitate():
    # Peste 1.0 paznicul ar taia DUPA ce incepe taxarea, adica n-ar mai pazi nimic.
    avertisment = _numar("PRAG_AVERTISMENT")
    taiere = _numar("PRAG_TAIERE")
    assert 0 < avertisment < taiere < 1


def test_watchdogul_cheama_paznicul_si_ramane_inert_implicit():
    index = (RADACINA / "infra-watchdog" / "index.js").read_text(encoding="utf-8")
    assert 'from "./r2-paznic.js"' in index
    assert "ruleazaPaznic(env)" in index
    toml = (RADACINA / "infra-watchdog" / "wrangler.toml").read_text(encoding="utf-8")
    # Bucket gol in repo = cod publicat fara efect; activarea e un pas separat, constient.
    assert re.search(r'^R2_PAZNIC_BUCKET = ""$', toml, re.MULTILINE)


@pytest.mark.skipif(shutil.which("node") is None, reason="node nu e disponibil")
def test_suita_js_a_paznicului_e_verde():
    r = subprocess.run(
        ["node", "--test", str(TESTE_JS)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(RADACINA), timeout=120,
    )
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-1000:]
