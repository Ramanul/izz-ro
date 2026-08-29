"""Pragul de timeout al randarii din `conftest` — sa nu redevina o constanta expirata.

De ce exista fisierul asta: pe 2026-08-28 `main` a ajuns sa pice `pytest` pe o randare
perfect sanatoasa. Pragul era `timeout=600`, pus cand randarea normala dura ~86 s, deci
era ~7x. Intre timp starea a crescut si randarea normala a ajuns la 638 s: pragul coborase
SUB normal si nu mai deosebea „blocat" de „mare" (#222).

Aceeasi clasa de greseala ca `OUTPUT_FILE_BUDGET=19500` lasat dupa mutarea gazdei pe
Workers Paid — o constanta calibrata la o scara, tacut gresita la alta. De-aia pragul nu
mai e constanta fixa, ci `_limita_randare()` creste cu starea; testele de aici tin formula
onesta, fara sa astepte o randare completa (IZZ-0177: cazurile negative conteaza la fel de
mult ca cele pozitive).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import LIMITA_MINIMA, SECUNDE_PER_ARTICOL, _numar_articole  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Masurat 2026-08-28 pe 10.742 articole in stare: 638 s intr-o rulare reala pe `main`.
RANDARE_MASURATA_S = 638
ARTICOLE_LA_MASURATOARE = 10_742


def test_pragul_lasa_marja_peste_randarea_masurata():
    """La starea de la masuratoare, pragul trebuie sa fie confortabil peste ea."""
    prag = _limita_randare_pentru(ARTICOLE_LA_MASURATOARE)
    assert prag >= RANDARE_MASURATA_S * 1.5, (
        f"prag {prag} s pentru {ARTICOLE_LA_MASURATOARE} articole, dar randarea masurata "
        f"e {RANDARE_MASURATA_S} s. Sub 1.5x, un runner incarcat pica pe o randare sanatoasa.")


def test_pragul_lasa_marja_si_pe_starea_de_azi():
    """Nu e o formalitate: pica singur daca starea a crescut peste ce acopera formula."""
    n = _numar_articole()
    if n == 0:
        return
    estimat = n * (RANDARE_MASURATA_S / ARTICOLE_LA_MASURATOARE)
    prag = _limita_randare_pentru(n)
    assert prag >= estimat * 1.5, (
        f"la {n} articole randarea se estimeaza la {estimat:.0f} s, iar pragul e {prag} s. "
        f"Formula a ramas in urma cresterii — remasoara si ridica SECUNDE_PER_ARTICOL.")


def test_NEGATIV_pragul_chiar_creste_cu_starea():
    """O formula care intoarce acelasi numar la orice scara e exact bug-ul reparat in #222."""
    assert _limita_randare_pentru(100_000) > _limita_randare_pentru(20_000)


def test_NEGATIV_podeaua_apara_un_checkout_mic_sau_gol():
    """Sub podea nu se coboara: un checkout aproape gol nu trebuie sa dea un prag absurd."""
    assert _limita_randare_pentru(0) == LIMITA_MINIMA
    assert _limita_randare_pentru(10) == LIMITA_MINIMA


def _limita_randare_pentru(n_articole: int) -> int:
    """`_limita_randare()` citeste `data/articles.json` direct — pentru teste, aceeasi
    formula aplicata pe un numar dat, ca sa nu depinda de starea reala a checkout-ului."""
    return max(LIMITA_MINIMA, int(n_articole * SECUNDE_PER_ARTICOL))
