"""Articolele vechi trebuie sa urmeze rubrica geografica pe care o are ACUM sursa lor.

Axa geografica e decisa de sursa. Dar categoria unui articol deja procesat e inghetata in
`data/articles.json` si se recalculeaza doar la bump de PROMPT_VERSION, asa ca o rearanjare
de config lasa in urma articole pe rubrica veche. Nu se repara singure niciodata: cand a
fost scris testul, 131 de articole stateau in `local` desi sursele lor erau `zonal` de mult.
"""
import json

import pytest

from generator import config, geo, state


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
    """O sursa reala aflata pe axa geografica, ca testul sa nu inventeze config.

    Cade, nu sare: fara nicio sursa geografica in config, testele de resync s-ar
    dezactiva tacit exact cand configuratia e stricata — adica fix cand contau.
    """
    for sid, s in config.SOURCES.items():
        if s.get("category") in config.PINNED_CATEGORIES:
            return sid, s["category"]
    raise AssertionError(
        f"config.SOURCES nu are nicio sursa pe axa geografica "
        f"({sorted(config.PINNED_CATEGORIES)}) — configuratie stricata, nu motiv de skip")


def _sursa_zonala_cu_localitate():
    """O sursa `zonal` cu judet declarat + o localitate NEAMBIGUA din judetul ei.

    Nu se hardcodeaza nici sursa, nici localitatea: prima rearanjare de config sau de
    gazetteer ar face testul sa treaca degeaba. Cade, nu sare — o configuratie fara nicio
    pereche valida e o configuratie stricata, nu un motiv de skip.
    """
    geo.eticheta_localitate("X")            # forteaza incarcarea dictionarelor de afisare
    for sid, s in config.SOURCES.items():
        judet = s.get("judet")
        if s.get("category") != "zonal" or not judet:
            continue
        for nume, judete in (geo._JUDETUL_LOCALITATII or {}).items():
            if judete != {judet} or nume == judet:
                continue
            eticheta = geo.eticheta_localitate(nume)
            titlu = f"Un accident rutier s-a produs la {eticheta}"
            if geo.clasifica(titlu, judet) == "local":
                return sid, titlu, eticheta
    raise AssertionError(
        "config.SOURCES nu are nicio sursa `zonal` cu judet care sa aiba o localitate "
        "neambigua in gazetteer — config sau data/localities.json e stricat, nu motiv de skip")


def test_textul_care_sustine_categoria_stocata_nu_e_tras_pe_rubrica_sursei(stare):
    """Regula proprietarului (2026-08-02): LOCAL = UNDE se intampla, nu CINE publica.

    Pana pe 2026-08-08 functia asta o anula la fiecare `load()`: un articol despre o comuna,
    publicat de un ziar judetean, era impins inapoi pe `zonal`. 663 din 1247 de articole de la
    surse cu rubrica geografica fixata erau in situatia asta.
    """
    sid, titlu, _ = _sursa_zonala_cu_localitate()
    stare([{"source": sid, "category": "local", "title": titlu, "url": "u"}])
    assert state.load()[0]["category"] == "local"


def test_textul_care_NU_sustine_categoria_stocata_e_readus(stare):
    """Scenariul pentru care s-a scris functia ramane acoperit.

    Titlul numeste doar judetul, deci `local` nu e sustinut de text -> articolul se intoarce
    pe rubrica sursei. Garda din 2026-08-08 cere potrivire EXACTA, nu „orice nivel geografic",
    tocmai ca sa nu inghete articolele astea pe rubrica gresita.
    """
    sid, _, _ = _sursa_zonala_cu_localitate()
    judet = config.SOURCES[sid]["judet"]
    titlu = f"Politistii din {geo.eticheta_judet(judet)} au facut perchezitii"
    assert geo.clasifica(titlu, judet) == "zonal", "premisa testului: titlul numeste judetul"
    stare([{"source": sid, "category": "local", "title": titlu, "url": "u"}])
    assert state.load()[0]["category"] == "zonal"


def test_teaserul_conteaza_nu_doar_titlul(stare):
    """Aceeasi intrare ca la ingestie: `_text_clasificabil` ia titlu + teaser + synthesis."""
    sid, titlu, _ = _sursa_zonala_cu_localitate()
    stare([{"source": sid, "category": "local", "title": "Anunt",
            "teaser": titlu, "url": "u"}])
    assert state.load()[0]["category"] == "local"


def test_textul_e_acelasi_cu_cel_de_la_ingestie():
    """`state._text_articol` duplica `process._text_clasificabil`. Aici se tin legate.

    Daca una capata un camp nou si cealalta nu, garda de mai sus vede alt text decat
    clasificarea de la ingestie si articolele incep iar sa oscileze intre rubrici.
    """
    from generator.process import _text_clasificabil
    for art in ({"title": "t", "teaser": "z", "synthesis": "s"},
                {"title": "t"}, {"teaser": "z"}, {}, {"title": None, "teaser": "z"}):
        assert state._text_articol(art) == _text_clasificabil(art)


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


@pytest.mark.parametrize("intrare", [
    None,
    "un sir, nu un articol",
    123,
    ["lista"],
    {"source": "x", "category": ["lista"]},   # nehashabil -> `in set` arunca TypeError
    {"source": 123, "category": "local"},
    {"source": None, "category": None},
])
def test_intrarile_malformate_nu_opresc_pipeline_ul(stare, intrare):
    """Inainte de resync, `load()` returna orice lista JSON neatinsa. Daca resyncul arunca
    pe o intrare stricata, `except (JSONDecodeError, OSError)` din load() NU o prinde, deci
    ar cadea tot pipeline-ul in loc sa se intoarca pe starea goala."""
    stare([intrare])
    assert state.load() == [intrare]


def test_intrarea_valida_e_corectata_chiar_langa_una_stricata(stare):
    """O intrare stricata nu trebuie sa opreasca resyncul celorlalte."""
    sid, actuala = _sursa_geo()
    veche = next(c for c in config.PINNED_CATEGORIES if c != actuala)
    stare([None, {"source": sid, "category": veche, "title": "x", "url": "u"}])
    assert state.load()[1]["category"] == actuala


def _pe_alta_rubrica_decat_sursa(articole):
    """Articolele a caror rubrica geografica difera de cea declarata pentru sursa lor.

    NU toate sunt derapaje — de la 2026-08-08 asta e chiar starea normala pentru o stire
    despre o comuna publicata de un ziar judetean (regula proprietarului: LOCAL = UNDE se
    intampla). Se separa mai jos, dupa ce spune textul.
    """
    return [a for a in articole
            if (s := config.SOURCES.get(a.get("source") or ""))
            and s.get("category") in config.PINNED_CATEGORIES
            and a.get("category") in config.PINNED_CATEGORIES
            and a["category"] != s["category"]]


def _derapaje(articole):
    """Doar cele pe care nici textul lor nu le sustine — alea sunt de reparat."""
    return [a for a in _pe_alta_rubrica_decat_sursa(articole)
            if geo.clasifica(state._text_articol(a),
                             geo.judet_sursa(a["source"])) != a["category"]]


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
    with open(state.STATE_PATH, encoding="utf-8") as fh:
        brut = json.load(fh)
    print(f"pe alta rubrica decat sursa: {len(_pe_alta_rubrica_decat_sursa(brut))} din "
          f"{len(brut)}, din care nesustinute de text: {len(_derapaje(brut))}")
    assert _derapaje(state.load()) == []
