"""Pragul de timeout al randarii din `conftest` — sa nu redevina o constanta expirata.

De ce exista fisierul asta: pe 2026-08-28 `main` a ajuns sa pice `pytest` pe o randare
perfect sanatoasa. Pragul era `timeout=600`, pus cand randarea normala dura ~85 s, deci
era ~7x. Intre timp starea a crescut si randarea normala a ajuns la 654-721 s: pragul
coborase SUB normal si nu mai deosebea „blocat" de „mare".

Aceeasi clasa de greseala ca `OUTPUT_FILE_BUDGET=19500` lasat dupa mutarea gazdei pe
Workers Paid — o constanta calibrata la o scara, tacut gresita la alta. De-aia pragul nu
mai e constanta, ci creste cu starea; testele de aici tin formula onesta.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import timeout_randare  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Masurat 2026-08-28 pe 10.742 articole in stare: 721 s intr-un container de sesiune web
# (4 nuclee), 654 s pe masina proprietarului. Luam cifra LENTA ca referinta.
RANDARE_MASURATA_S = 721
ARTICOLE_LA_MASURATOARE = 10_742


def test_pragul_lasa_marja_peste_randarea_masurata():
    """La starea de la masuratoare, pragul trebuie sa fie confortabil peste ea."""
    prag = timeout_randare(ARTICOLE_LA_MASURATOARE)
    assert prag >= RANDARE_MASURATA_S * 2, (
        f"prag {prag} s pentru {ARTICOLE_LA_MASURATOARE} articole, dar randarea masurata "
        f"e {RANDARE_MASURATA_S} s. Sub 2x, un runner incarcat pica pe o randare sanatoasa.")


def test_pragul_lasa_marja_si_pe_starea_de_AZI():
    """Nu e o formalitate: pica singur daca starea creste peste ce acopera formula."""
    with open(os.path.join(ROOT, "data", "articles.json"), encoding="utf-8") as fh:
        n = len(json.load(fh))
    estimat = n * (RANDARE_MASURATA_S / ARTICOLE_LA_MASURATOARE)
    prag = timeout_randare(n)
    assert prag >= estimat * 2, (
        f"la {n} articole randarea se estimeaza la {estimat:.0f} s, iar pragul e {prag} s. "
        f"Formula a ramas in urma cresterii — remasoara si ridica factorul.")


def test_NEGATIV_pragul_chiar_CRESTE_cu_starea():
    """O formula care intoarce acelasi numar la orice scara e exact bug-ul reparat aici."""
    assert timeout_randare(100_000) > timeout_randare(20_000)


def test_NEGATIV_podeaua_apara_un_repo_mic():
    """Sub podea nu se coboara: un checkout aproape gol nu trebuie sa dea un prag absurd."""
    assert timeout_randare(0) == 1200
    assert timeout_randare(10) == 1200
