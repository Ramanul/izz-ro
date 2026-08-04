"""Slug-ul se taie la limita de cuvant, nu la mijloc.

Masurat 2026-08-04 pe arhiva reconstruita din istoricul git (7001 articole, 39 de zile):
1254 (17.9%) aveau slug-ul retezat prin cuvant — `...pentru-masuri-de-econom`,
`...pe-un-feribot-i`. Cu regula noua se schimba 1669 (23.8%), diferenta fiind
slug-urile care se terminau in cratima.
"""
from generator.render import _taie_slug


def test_scurt_ramane_neatins():
    assert _taie_slug("stire-scurta") == "stire-scurta"


def test_taie_inapoi_la_ultima_cratima():
    s = "a" * 70 + "-cuvantfoartelung"
    assert _taie_slug(s) == "a" * 70


def test_nu_lasa_cratima_la_coada():
    """Cazul masurat `...de-armament-`: taietura la 80 cadea EXACT pe cratima."""
    s = "b" * 79 + "-restul-titlului"
    assert not _taie_slug(s).endswith("-")


def test_garda_pastreaza_taietura_bruta_cand_cuvantul_e_urias():
    """Un titlu cu un singur cuvant de 200 de caractere: a da inapoi pana la ultima cratima
    ar lasa un slug gol. Sub pragul de 40, taietura bruta e preferabila.

    Pe corpusul real garda nu s-a activat niciodata (0 din 7001) — exista pentru cazul
    patologic, nu pentru unul observat.
    """
    s = "scurt-" + "x" * 200
    assert _taie_slug(s) == s[:80]


def test_limita_se_respecta():
    s = "-".join(["cuvant"] * 40)
    assert len(_taie_slug(s)) <= 80
