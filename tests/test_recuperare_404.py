"""Teste pentru tools/recupereaza_404.py — normalizarea taxonomiei la recuperare.

De ce exista: unealta scoate articole din istoricul Git al lui `data/articles.json`, iar
istoricul le pastreaza sub categoria de ATUNCI. Categoria `zonal` a fost redenumita
`judetean` pe 2026-08-12; randarea nu mai scrie pagini sub numele mort, dar listarile
inca emit linkul catre el. Rezultat masurat inainte de fix: 5 articole recuperate cu
`zonal` -> 9 legaturi interne rupte raportate de `tools/html_check.py`, cu baseline-ul
pe `main` la 0.
"""
import importlib.util
import json
import os

from generator import config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _modul():
    cale = os.path.join(ROOT, "tools", "recupereaza_404.py")
    spec = importlib.util.spec_from_file_location("recupereaza_404", cale)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_categoria_redenumita_e_migrata_la_recuperare():
    mod = _modul()
    out = mod._normalizeaza({"slug": "x", "category": "zonal", "url": "u"})
    assert out["category"] == "judetean"


def test_categoria_valida_nu_e_atinsa():
    """Testul negativ: garda trebuie sa lase in pace ce e deja corect."""
    mod = _modul()
    for cat in ("judetean", "local", "economic", "sport"):
        out = mod._normalizeaza({"slug": "x", "category": cat, "url": "u"})
        assert out["category"] == cat, f"{cat} a fost modificat pe nedrept"


def test_normalizarea_nu_muteaza_articolul_din_istoric():
    """Recuperarea citeste articole din commit-uri; nu are voie sa le modifice pe loc."""
    mod = _modul()
    original = {"slug": "x", "category": "zonal", "url": "u"}
    mod._normalizeaza(original)
    assert original["category"] == "zonal"


def test_starea_comisa_nu_contine_categorii_moarte():
    """Garda pe DATE, nu doar pe cod: `data/articles.json` nu are voie sa poarte o
    categorie redenumita — ar produce exact legaturile rupte de mai sus."""
    cale = os.path.join(ROOT, "data", "articles.json")
    with open(cale, encoding="utf-8") as fh:
        d = json.load(fh)
    arts = d if isinstance(d, list) else d.get("articles", [])
    moarte = sorted({a.get("category") for a in arts} & set(config.CATEGORII_REDENUMITE))
    assert not moarte, f"categorii redenumite ramase in stare: {moarte}"
