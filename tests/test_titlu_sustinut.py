"""Garda de respingere pentru titlurile deformate semantic.

RECUPERATA din commitul `7ee576db` (Manus AI, 2026-08-19), care NU a ajuns in `main`: acolo
`_synthesis_title_is_supported` respingea candidatul, aici supravietuise doar lista de markeri,
iar rolul fusese preluat de `_repair_synthesis_title`, care REPARA un singur caz.

Auditul din 2026-08-20 a semnalat golul ([C4]): reparatia trateaza UN caz dintr-o CLASA.
Cele doua ruleaza acum in lant — repari cand poti, respingi cand nu poti.
"""
from generator.process import _repair_synthesis_title, _titlu_sustinut_de_context

CONTEXT_IDENTITATE = "Suspecții au pretins că sunt lucrători antidrog și s-au dat drept polițiști."


def test_cazul_reparabil_trece_dupa_reparatie():
    """Nu pierdem articolul cand formularea e exact cea cunoscuta: se repara, apoi e sustinut."""
    title = "Doi bărbați arestați după ce au simțit polițiști antidrog"
    reparat = _repair_synthesis_title(title, CONTEXT_IDENTITATE)
    assert "s-au dat drept polițiști" in reparat
    assert _titlu_sustinut_de_context(reparat, CONTEXT_IDENTITATE) is True


def test_alta_formulare_din_aceeasi_clasa_e_RESPINSA():
    """Golul pe care il inchide garda: reparatia nu prinde varianta asta, si trecea nesemnalata."""
    title = "Doi bărbați arestați după ce au simțit agenți antidrog"
    reparat = _repair_synthesis_title(title, CONTEXT_IDENTITATE)
    assert reparat == title, "reparatia nu acopera formularea asta — de-aia e nevoie de garda"
    assert _titlu_sustinut_de_context(reparat, CONTEXT_IDENTITATE) is False


def test_titlu_normal_cu_context_de_identitate_trece():
    """Garda e ingusta: fara deformare, un titlu corect despre acelasi eveniment nu e atins."""
    title = "Doi bărbați arestați după ce s-au dat drept polițiști antidrog"
    assert _titlu_sustinut_de_context(title, CONTEXT_IDENTITATE) is True


def test_fara_revendicare_de_identitate_garda_nu_se_aplica():
    """Zero fals-pozitive pe stiri obisnuite: fara marker in context, orice titlu trece."""
    title = "Locuitorii au simțit un cutremur de 4,2 grade"
    assert _titlu_sustinut_de_context(title, "Un seism a fost resimțit în Vrancea.") is True


def test_titlu_gol_e_respins():
    """„No mangled output": un titlu vid nu se publica niciodata."""
    assert _titlu_sustinut_de_context("", CONTEXT_IDENTITATE) is False
    assert _titlu_sustinut_de_context("   ", CONTEXT_IDENTITATE) is False
    assert _titlu_sustinut_de_context(None, CONTEXT_IDENTITATE) is False
