"""Pagina și cardul unei sinteze dialectice (E2/E3), randate cu mediul Jinja real.

Ce fixează: (1) cele trei stări au etichete diferite, toate în limbaj civic; (2) fiecare
afirmație poartă publicațiile ei, ca atribuire în text — linkurile rămân DOAR în `sources-box`
(formula de atribuire permanentă, CLAUDE.md §7); (3) rolul fiecărei surse apare lângă ea;
(4) zero vocabular doctrinar în interfață (garda din specs/plan-paradigma-izz.md §4).
"""
import re

import pytest

from generator import render

DOCTRINA = ("Legea lui Unu", "Ra ", "AlienMind", "catalizator", "polaritate", "densitate",
            "distorsiune", "Legea Confuziei", "recoltă", "Consens", "Fricțiune")


def _articol(state, **kw):
    d = {"v": "e2-v1", "state": state, "rejected": 0, "total": 3, "milestone": False,
         "common": [], "diverg": [], "single": []}
    if state == "SYNTHESIS_VALID":
        d["common"] = [{"text": "Bugetul Bihorului este de 820 de milioane de lei.",
                        "src": ["Alfa", "Beta"], "hedged": False, "forced": False},
                       {"text": "Primarul ar fi semnat fără licitație.", "src": ["Alfa", "Beta"],
                        "hedged": True, "forced": False}]
        d["single"] = [{"text": "Din buget, 120 de milioane merg la drumuri.", "src": ["Beta"],
                        "hedged": False, "forced": False}]
    if state in ("SYNTHESIS_VALID", "ASSUMED_SILENCE"):
        d["diverg"] = [{"axis": "numărul voturilor pentru", "pos": [
            {"text": "21 de consilieri au votat pentru.", "src": ["Alfa"]},
            {"text": "19 consilieri au votat pentru.", "src": ["Beta"]}]}]
    if state == "SINGLE_ORIGIN":
        d["single"] = [{"text": "Bugetul Bihorului este de 820 de milioane de lei.",
                        "src": ["Alfa", "Gama"], "hedged": False, "forced": False}]
    a = {"category": "economic", "source_name": "Alfa", "title": "Bihorul are buget aprobat",
         "slug": "bihorul-are-buget", "published": "2026-10-22T10:00:00+00:00",
         "published_human": "22 octombrie", "model": "C", "teaser": "",
         "synthesis": "Bugetul Bihorului este de 820 de milioane de lei.",
         "original_link": "https://a.ro/1", "art_path": None, "anunt_fara_corp": False,
         "ai_generat": True, "first_source": "Alfa", "cross_confirmations": 2,
         "sources": [{"name": "Alfa", "url": "https://a.ro/1"}, {"name": "Beta", "url": "https://b.ro/1"},
                     {"name": "Gama", "url": "https://c.ro/1"}],
         "epistemic_roles": {"a.ro": "ROOT", "b.ro": "INDEPENDENT_CONTRIBUTOR", "c.ro": "CLONE"},
         "dialectic": d}
    a.update(kw)
    a["surse_roluri"] = render._roluri_surse(a)
    return a


def _pagina(a) -> str:
    tpl = render._env().get_template("article.html")
    return tpl.render(**render._base_ctx(
        f"/{a['category']}/{a['slug']}/", a=a, active_cat=a["category"],
        topics=[], people=[], related=[], nav_section="stiri"))


def _articol_html(html: str) -> str:
    return html[html.find("<article class=\"article\">"):html.find("</article>")]


@pytest.mark.parametrize("state,eticheta", [
    ("SYNTHESIS_VALID", "Sinteză din 3 publicații · 2 confirmări încrucișate"),
    ("SINGLE_ORIGIN", "Sinteză din 3 publicații cu o singură origine"),
    ("ASSUMED_SILENCE", "Relatări divergente din 3 publicații"),
])
def test_eticheta_spune_cum_e_construita_informatia(state, eticheta):
    assert eticheta in _pagina(_articol(state))


def test_faptele_poarta_publicatiile_iar_linkurile_raman_in_sources_box():
    html = _articol_html(_pagina(_articol("SYNTHESIS_VALID")))
    sec = html[html.find('<section class="dialectic"'):html.find("</section>")]
    assert "Confirmat de mai multe publicații" in sec
    assert "— Alfa, Beta" in sec
    assert "cu rezervă la sursă" in sec
    assert "Unde diferă relatările" in sec and "Numărul voturilor pentru" in sec
    assert "Dintr-o singură origine" in sec
    assert "<a " not in sec                         # atribuire în text, nu un al doilea „Surse"
    assert len(re.findall(r'class="sources-box"', html)) == 1


def test_tacerea_nu_redacteaza_o_versiune_comuna():
    html = _articol_html(_pagina(_articol("ASSUMED_SILENCE")))
    assert "ireconciliabile" in html
    assert "Confirmat de mai multe publicații" not in html


def test_rolul_fiecarei_surse_e_langa_ea_in_cuvinte_civice():
    html = _articol_html(_pagina(_articol("SYNTHESIS_VALID")))
    box = html[html.find('class="sources-box"'):]
    assert "prima relatare observată" in box
    assert "detalii suplimentare" in box
    assert "text comun cu altă publicație (posibil comunicat)" in box
    assert "Confirmări încrucișate" in box


@pytest.mark.parametrize("state", ["SYNTHESIS_VALID", "SINGLE_ORIGIN", "ASSUMED_SILENCE"])
def test_zero_vocabular_doctrinar_in_interfata(state):
    html = _articol_html(_pagina(_articol(state)))
    for w in DOCTRINA:
        assert w not in html, w


def test_sinteza_veche_fara_structura_ramane_ca_inainte():
    a = _articol("SYNTHESIS_VALID")
    a.pop("dialectic")
    html = _articol_html(_pagina(a))
    assert "Sinteză multi-sursă" in html
    assert '<section class="dialectic"' not in html
    assert 'class="body"' in html


@pytest.mark.parametrize("state,eticheta", [
    ("SYNTHESIS_VALID", "Sinteză din 3 publicații · 2 confirmări încrucișate · generată automat"),
    ("SINGLE_ORIGIN", "Sinteză din 3 publicații · o singură origine · generată automat"),
    ("ASSUMED_SILENCE", "Relatări divergente · 3 publicații · generată automat"),
])
def test_cardul_spune_cate_confirmari_nu_doar_ca_e_multi_sursa(state, eticheta):
    card = render._env().get_template("_card.html").module.card
    assert eticheta in str(card(_articol(state)))


def test_registrul_sub_prag_arata_contoare_fara_titluri_si_fara_publicatii():
    triage = {"cand": "2026-10-23T05:03:42+00:00", "fara_substanta": 118, "expirate": 2459,
              "fara_substanta_exemple": ["https://exemplu.ro/titlu-momeala"],
              "ingestie": {"garda de continut ostil": 33, "item incomplet (fara link sau titlu)": 0},
              "sinteze": {"stare_SYNTHESIS_VALID": 7, "amanate_peste_prag": 1, "amanate_nemapat": 1,
                          "respinse_cifra": 2}}
    grupuri = render._sub_prag(triage, {"dedup": 1245, "garda": 5, "retrase": 0, "retinute": 0})
    toate = {r["eticheta"]: r["n"] for g in grupuri for r in g["randuri"]}
    assert toate["Fără conținut dincolo de titlu (sub 5 cuvinte noi)"] == 118
    # pe cauză: peste prag = verificare picată; obiect lipsă = modelul n-a răspuns
    assert toate["Amânate: n-au trecut verificarea contra surselor (se reiau la rularea următoare)"] == 1
    assert toate["Amânate: modelul n-a dat un răspuns folosibil (se reiau la rularea următoare)"] == 1
    assert toate["Duplicate ale unui eveniment deja publicat"] == 1245
    assert 0 not in toate.values()                       # zero nu e informație
    tpl = render._env().get_template("sub_prag.html")
    html = tpl.render(**render._base_ctx("/sub-prag/", nav_section="stiri", grupuri=grupuri))
    corp = html[html.find('<section class="sub-prag"'):html.find("</section>")]
    assert "exemplu.ro" not in corp and "titlu-momeala" not in corp
    assert "1245" in corp


def test_actualizarea_si_modificarea_tacuta_se_vad_pe_pagina():
    a = _articol("SYNTHESIS_VALID", modificari_tacute=["Beta"], updated_human="23 octombrie, 09:00")
    a["dialectic"]["schimbari"] = {"surse_noi": ["Gama"], "stare_anterioara": "SINGLE_ORIGIN"}
    html = _articol_html(_pagina(a))
    assert "Actualizare sinteză" in html and "A intrat o publicație nouă: Gama." in html
    assert "nu avea confirmări încrucișate" in html
    box = html[html.find('class="sources-box"'):]
    assert "actualizat de redacție după prima citire" in box


def test_origini_independente_fara_suprapunere_nu_sunt_numite_o_singura_origine():
    a = _articol("SINGLE_ORIGIN")
    a["dialectic"]["origini"] = 2
    html = _articol_html(_pagina(a))
    assert "fapte neconfirmate reciproc" in html
    assert "Fiecare fapt, la o singură publicație" in html
    assert "aceeași relatare inițială" not in html
    a["dialectic"]["origini"] = 1
    html = _articol_html(_pagina(a))
    assert "cu o singură origine" in html and "aceeași relatare inițială" in html
