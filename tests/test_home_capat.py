"""Prima pagină are un capăt și îl spune cinstit (trăsătura V din harta de fidelitate, 11.11.2026).

Capcana apărată: prima pagină e o SELECȚIE (câteva carduri pe rubrică; pe telefon mai puține
decât pe ecran lat). Linia de final nu are voie să pretindă că cititorul a văzut „toate"
subiectele și nu numără carduri. Pe o pagină fără știri nu apare deloc.
"""
from generator import render


def _articol(i, cat="economie"):
    return {
        "category": cat, "source_name": "Sursa Test", "title": f"Titlu de test numărul {i}",
        "slug": f"titlu-de-test-{i}", "published": "2026-11-12T08:00:00+00:00",
        "published_human": "12 noiembrie", "model": "B",
        "teaser": "Un rezumat de test cu suficiente cuvinte ca sa fie numarat.",
        "synthesis": "", "original_link": "https://exemplu.ro/x", "art_path": None,
        "anunt_fara_corp": False, "sources": None, "ai_generat": False,
    }


def _home(articole, zi):
    by_category = {"economie": articole[1:]} if articole else {}
    return render._env().get_template("index.html").render(**render._base_ctx(
        "/", nav_section="stiri", articles=articole, hero=articole[:1],
        by_category=by_category, jsonld_nodes=[], newsletter_html="", zi=zi,
        briefing=[], editorial_selection=None, ttl_days=11, judete=[]))


def _capat(html):
    return html.split('class="home-end"', 1)[1].split("</p>", 1)[0]


ZI = {"surse": 9, "relatari": 50, "judete": 3, "pe_judet": {}}


def test_linia_de_final_sta_dupa_ultima_rubrica_si_numeste_selectia():
    html = _home([_articol(i) for i in range(4)], {**ZI, "stiri": 37})
    assert html.count('class="home-end"') == 1
    capat = _capat(html)
    assert "selecția de pe prima pagină" in capat
    assert "au apărut 37 de subiecte" in capat
    assert "/azi/" in capat
    # nu pretinde completitudine și nu numește /azi/ „restul" (/azi/ are doar ziua curentă)
    assert "toate" not in capat.lower() and "restul" not in capat.lower()
    # după ultimul link de rubrică, nu în mijlocul grilei
    assert html.rindex('class="see-all"') < html.index('class="home-end"')


def test_numarul_apare_doar_cand_depaseste_ce_arata_pagina():
    """4 articole pe pagină: «o parte din cele 4» ar fi fals, la fel «din cele 1»."""
    arts = [_articol(i) for i in range(4)]
    for n in (1, 4):
        capat = _capat(_home(arts, {**ZI, "stiri": n}))
        assert "au apărut" not in capat and "/azi/" in capat
    assert "au apărut 5 subiecte" in _capat(_home(arts, {**ZI, "stiri": 5}))
    assert "ultimele 24 de ore" not in _capat(_home(arts, None))


def test_pagina_fara_stiri_nu_are_linie_de_final():
    assert 'class="home-end"' not in _home([], None)


def test_de_ro_regula_numeralului():
    de = render._de_ro
    assert [de(n) for n in (0, 1, 2, 19)] == ["", "", "", ""]
    assert [de(n) for n in (20, 37, 100, 969, 1000, 120)] == ["de "] * 6
    assert [de(n) for n in (101, 119, 1019)] == ["", "", ""]
    assert de(None) == "" and de("x") == ""


def test_antetul_si_lista_zilei_folosesc_de():
    html = _home([_articol(i) for i in range(4)],
                 {"stiri": 969, "surse": 169, "relatari": 1035, "judete": 37, "pe_judet": {}})
    antet = html.split('class="day-numbers"', 1)[1].split("</span>", 1)[0]
    assert "</b> de articole" in antet and "</b> de subiecte" in antet
    assert "</b> de surse" in antet and "</b> de județe" in antet
    azi = render._env().get_template("azi.html").render(**render._base_ctx(
        "/azi/", nav_section="stiri", zi_human="12 noiembrie",
        items=[{**_articol(i), "n_surse": 1} for i in range(21)]))
    assert "toate cele 21 de subiecte" in azi
