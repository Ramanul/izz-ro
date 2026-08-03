"""Ghidurile procedurale: proza pe sectiuni in loc de o cifra-titlu.

Context: `/utile/` a fost un al doilea sistem de ghiduri, inlocuit de `/ghiduri/` pe
2026-07-17 — apelul lui `_render_utilities` a fost sters in aceeasi zi, dar datele au ramas.
Trei ghiduri (buletin/pasaport, permis auto, Noua Casa) n-au ajuns niciodata la un vizitator:
`/utile/` da 404 pe live si nu e in sitemap. Sistemul de entitati stia doar valori monetare
(brut + istoric), asa ca portarea lor a cerut un camp `sectiuni` optional.

Testele apara cele doua feluri in care asta poate esua tacut: o sectiune goala care se
randeaza ca `<h2>` urmat de nimic, si markdown neconvertit care ajunge la cititor ca `**`.
"""
import importlib
import os
import sys

import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
build_entities = importlib.import_module("build_entities")

from generator import render  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTITIES_DIR = os.path.join(ROOT, "data", "entities")

# Ghidurile portate din data/utilities.json.
PORTATE = ("buletin-pasaport", "permis-auto", "noua-casa")
# A doua transa: ghidurile de valoare aveau deja cifra-titlu si istoricul in entitati, dar proza
# lor pe sectiuni ramasese in utilities.json — 11 sectiuni care n-au ajuns niciodata pe live.
PORTATE_VALOARE = ("pensia-minima", "alocatia-copii", "salariul-minim")
# Pragul e 2, nu 3: din cele cinci sectiuni ale salariului minim au trecut doua. Celelalte trei
# ori repetau ce randeaza deja sablonul, ori purtau o cifra pe sector pe care actul in vigoare
# dupa HG 146/2026 n-o mai sustine.
MIN_SECTIUNI = 2


def _ent(**kw):
    ent = {
        "id": "test", "nume": "Test", "tip": "acte", "categorie_ghid": "acte",
        "ultima_verificare": "2026-01-01", "verificat": False,
        "valoare_curenta": {"act_normativ": "HG 1/2026", "sursa_url": "https://x.ro/hg",
                            "in_vigoare_de": "2026-01-01"},
    }
    ent.update(kw)
    return ent


def test_sectiuni_lipsa_e_valid():
    """Ghidurile de valoare (salariu, pensie) n-au sectiuni si nu trebuie sa capete erori."""
    assert build_entities.validate(_ent()) == []


def test_sectiune_valida_trece():
    assert build_entities.validate(_ent(sectiuni=[{"titlu": "Cum", "continut": "Pasi."}])) == []


@pytest.mark.parametrize("sectiuni,asteptat", [
    ([{"titlu": "", "continut": "text"}], "titlu"),
    ([{"titlu": "Cum", "continut": "   "}], "continut"),
    ([{"continut": "text"}], "titlu"),
    ([{"titlu": "Cum"}], "continut"),
    (["nu e dict"], "nu e un dict"),
    ("nu e lista", "trebuie să fie o listă"),
    # `titlu: 5` in YAML e un int; `.strip()` pe el arunca AttributeError si opreste build-ul
    # cu traceback brut in loc de mesajul de validare. Gasit de review, reprodus, apoi reparat.
    ([{"titlu": 5, "continut": "text"}], "titlu"),
    ([{"titlu": "Cum", "continut": ["a", "b"]}], "continut"),
    ([{"titlu": None, "continut": "text"}], "titlu"),
])
def test_sectiune_malformata_blocheaza_buildul(sectiuni, asteptat):
    """Un `<h2>` gol urmat de nimic e output degradat publicat tacit (§7 Zero Zgomot)."""
    erori = build_entities.validate(_ent(sectiuni=sectiuni))
    assert any(asteptat in e for e in erori), erori


def test_markdownul_sectiunilor_ajunge_html_nu_asteriscuri():
    """`| safe` pe markdown neconvertit ar afisa `**2.500 lei**` literal in pagina."""
    html = render._md_to_html("Costa **2.500 lei** in total.")
    assert "<strong>2.500 lei</strong>" in html
    assert "**" not in html


@pytest.mark.parametrize("eid", PORTATE)
def test_ghidul_portat_exista_si_are_continut(eid):
    path = os.path.join(ENTITIES_DIR, f"{eid}.yaml")
    assert os.path.isfile(path), f"{eid}: ghidul portat lipseste din data/entities/"
    with open(path, encoding="utf-8") as fh:
        ent = yaml.safe_load(fh)
    assert build_entities.validate(ent) == []
    assert len(ent.get("sectiuni") or []) >= 3, f"{eid}: proza s-a pierdut la portare"
    assert ent.get("faq"), f"{eid}: FAQ-ul s-a pierdut la portare"
    # niciunul nu are cifra-titlu: exact motivul pentru care au avut nevoie de `sectiuni`
    assert "brut" not in ent["valoare_curenta"]


@pytest.mark.parametrize("eid", PORTATE)
def test_ghidul_portat_citeaza_o_sursa_reala(eid):
    """§14: nu se inventeaza fapte juridice. Fiecare act e o pagina exacta pe portalul
    legislativ oficial, nu homepage-ul unei institutii."""
    with open(os.path.join(ENTITIES_DIR, f"{eid}.yaml"), encoding="utf-8") as fh:
        vc = yaml.safe_load(fh)["valoare_curenta"]
    assert vc["sursa_url"].startswith("https://legislatie.just.ro/Public/DetaliiDocument/")
    assert vc["act_normativ"].strip()


@pytest.mark.parametrize("eid", PORTATE_VALOARE)
def test_ghidul_de_valoare_isi_poarta_proza(eid):
    """Un ghid de valoare fara `sectiuni` se randeaza doar ca cifra + istoric + FAQ. Arata
    complet, deci nimeni nu observa ca lipseste ceva — asa au stat 11 sectiuni de proza in
    data/utilities.json din 17 iulie pana in 3 august, invizibile pentru cititor."""
    with open(os.path.join(ENTITIES_DIR, f"{eid}.yaml"), encoding="utf-8") as fh:
        ent = yaml.safe_load(fh)
    assert build_entities.validate(ent) == []
    assert len(ent.get("sectiuni") or []) >= MIN_SECTIUNI, f"{eid}: proza s-a pierdut la portare"
    assert ent["valoare_curenta"].get("brut"), f"{eid}: e ghid de valoare, trebuie sa aiba cifra"


def test_nu_exista_un_al_doilea_sistem_de_ghiduri():
    """`data/utilities.json` a fost al doilea sistem de ghiduri: randorul lui a fost sters pe
    17 iulie, fisierul a ramas, si continutul lui a devenit invizibil fara ca nimic sa pice.
    Daca reapare, cineva a reintrodus o cale de continut care nu trece prin data/entities/."""
    assert not os.path.exists(os.path.join(ROOT, "data", "utilities.json"))
    assert not hasattr(render, "_render_utilities")


def test_pe_scurt_apare_doar_cand_exista_o_cifra():
    """Titlul „Pe scurt" promite un rezumat cu valoare. Deasupra unei simple linii de sursa
    e o promisiune neonorata — ghidurile procedurale isi poarta rezumatul in subtitlu."""
    env = render._env()
    env.filters.setdefault("format_int", lambda v: v)
    env.filters.setdefault("domain_from_url", lambda u: u)
    tpl = env.get_template("ghid.html")

    def _randeaza(valoare_curenta, sectiuni=()):
        ent = {"nume": "T", "categorie_ghid": "acte", "verificat": False,
               "valoare_curenta": {"descriere_lunga": "x", "sursa_url": "https://x.ro/a",
                                   **valoare_curenta}}
        return tpl.render(**render._base_ctx("/ghiduri/t/", ent=ent, categorii={},
                                             categorii_icon={}, related_news=[],
                                             faq_jsonld={}, breadcrumb_jsonld={},
                                             calculator_html="", sectiuni=list(sectiuni)))

    assert "Pe scurt" in _randeaza({"brut": 4050})
    assert "Pe scurt" not in _randeaza({}, [{"titlu": "Pasi", "continut_html": "<p>a</p>"}])


def test_sectiunile_ajung_in_pagina_randata():
    env = render._env()
    env.filters.setdefault("format_int", lambda v: v)
    env.filters.setdefault("domain_from_url", lambda u: u)
    html = env.get_template("ghid.html").render(**render._base_ctx(
        "/ghiduri/t/", ent={"nume": "T", "verificat": True, "categorie_ghid": "acte",
                            "valoare_curenta": {"descriere_lunga": "x", "sursa_url": "https://x.ro/a"}},
        categorii={}, categorii_icon={}, related_news=[], faq_jsonld={}, breadcrumb_jsonld={},
        calculator_html="", sectiuni=[{"titlu": "Acte necesare", "continut_html": "<p>Buletin.</p>"}]))
    assert "Acte necesare" in html
    assert "<p>Buletin.</p>" in html
