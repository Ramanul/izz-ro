"""Articolele vechi trebuie sa urmeze rubrica geografica pe care o are ACUM sursa lor.

Axa geografica e decisa de sursa. Dar categoria unui articol deja procesat e inghetata in
`data/articles.json` si se recalculeaza doar la bump de PROMPT_VERSION, asa ca o rearanjare
de config lasa in urma articole pe rubrica veche. Nu se repara singure niciodata: cand a
fost scris testul, 131 de articole stateau in `local` desi sursele lor erau `zonal` de mult.
"""
import json

import pytest

from generator import config, state


@pytest.fixture
def stare(tmp_path, monkeypatch):
    """Scrie o stare de test si o pune in locul celei reale."""
    def _scrie(articole):
        p = tmp_path / "articles.json"
        p.write_text(json.dumps(articole), encoding="utf-8")
        monkeypatch.setattr(state, "STATE_PATH", str(p))
        return p
    return _scrie


def _sursa_geo():
    """O sursa reala aflata pe axa geografica, ca testul sa nu inventeze config."""
    for sid, s in config.SOURCES.items():
        if s.get("category") in config.PINNED_CATEGORIES:
            return sid, s["category"]
    pytest.skip("nicio sursa geografica in config")


def test_articolul_ramas_pe_rubrica_veche_e_readus(stare):
    sid, actuala = _sursa_geo()
    veche = next(c for c in config.PINNED_CATEGORIES if c != actuala)
    stare([{"source": sid, "category": veche, "title": "x", "url": "u"}])
    assert state.load()[0]["category"] == actuala


def test_articolul_deja_corect_nu_e_atins(stare):
    sid, actuala = _sursa_geo()
    stare([{"source": sid, "category": actuala, "title": "x", "url": "u"}])
    assert state.load()[0]["category"] == actuala


def test_categoria_tematica_nu_e_rescrisa(stare):
    """Un articol pe o tema nu e tras pe axa geografica: sunt axe diferite (CLAUDE.md §7)."""
    sid, _ = _sursa_geo()
    stare([{"source": sid, "category": "sport", "title": "x", "url": "u"}])
    assert state.load()[0]["category"] == "sport"


def test_sursa_scoasa_din_config_isi_pastreaza_categoria(stare):
    """Fara sursa in config nu avem de unde sti alta categorie — nu ghicim."""
    stare([{"source": "sursa_inexistenta_xyz", "category": "local", "title": "x", "url": "u"}])
    assert state.load()[0]["category"] == "local"


def test_articol_fara_camp_source_nu_arunca(stare):
    stare([{"category": "local", "title": "x", "url": "u"}])
    assert state.load()[0]["category"] == "local"


def _derapaje(articole):
    return [a for a in articole
            if (s := config.SOURCES.get(a.get("source") or ""))
            and s.get("category") in config.PINNED_CATEGORIES
            and a.get("category") in config.PINNED_CATEGORIES
            and a["category"] != s["category"]]


def test_starea_reala_e_vindecata_la_load():
    """Canary pe starea chiar comisa in repo — 1100+ articole, config real.

    Ce dovedeste: ca `_resync_pinned` e CABLATA in `load()` si ca rezista pe date reale.
    Pica daca cineva scoate apelul din `load()` (verificat, nu presupus).

    Ce NU dovedeste: cu fixul activ, `load()` produce prin constructie o stare fara
    derapaje, deci asertiunea finala nu poate esua din cauza datelor. Testele unitare de
    mai sus sunt cele care verifica logica. Asta ramane util pentru ca e singurul care
    trece config-ul REAL peste starea REALA: o viitoare rearanjare de categorii care ar
    sparge functia se vede aici, nu in fixture-uri fabricate.

    Numarul brut e afisat, nu asertat: dupa o rulare completa `main.run()` salveaza starea
    deja vindecata, deci fisierul comis poate ajunge legitim la zero derapaje.
    """
    brut = json.load(open(state.STATE_PATH, encoding="utf-8"))
    print(f"derapaje in fisierul comis: {len(_derapaje(brut))} din {len(brut)}")
    assert _derapaje(state.load()) == []
