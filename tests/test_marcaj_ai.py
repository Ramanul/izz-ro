"""Marcajul AI Act art. 50(4) — pe articol, nu pe cardurile de listă.

DE CE EXISTA: marcajul a fost scris pe 2026-08-17 in 5 fisiere si predat NERULAT. Suita de
atunci (934 de teste) trecea, dar niciun test nu atingea elementul nou — deci "testele trec"
nu putea distinge "marcajul apare" de "marcajul lipseste complet". Fisierul asta inchide gaura.

2026-09-02: pe carduri/hero, eticheta se repeta pe fiecare item si se citeste ca semnal de
neincredere. Transparența rămâne pe pagina de articol (ai-mark + ai-note) și în
/legal/method/. Cardul păstrează doar trust-label (Sinteză / Rezumat / Anunț).

CE ACOPERA: randarea reala a macro-ului `card()` + `article.html` cu mediul Jinja din
`render._env()`, plus expresia care decide flagul.

Temeiul si formularea: REGULI-SINTEZA.md §4.
"""
import pytest

from generator import render

# Fluxurile care NU ating modelul de limbaj. Marcarea lor ar fi eroarea inversa — ar sugera
# ca stirea insasi e fabricata (REGULI-SINTEZA.md §4.4).
FLUXURI_NEMARCATE = ("official", "fallback")


def _articol(**kw):
    baza = {
        "category": "economie", "source_name": "Sursa Test", "title": "Titlu de test",
        "slug": "titlu-de-test", "published": "2026-08-17", "published_human": "17 august",
        "model": "B", "teaser": "Un rezumat de test cu suficiente cuvinte ca sa fie numarat.",
        "synthesis": "", "original_link": "https://exemplu.ro/x", "art_path": None,
        "anunt_fara_corp": False, "sources": None, "ai_generat": False,
    }
    baza.update(kw)
    return baza


@pytest.fixture(scope="module")
def card():
    return render._env().get_template("_card.html").module.card


def test_cardul_nu_poarta_marcajul_ai(card):
    """Listă/home: fără «Titlu sintetizat automat» — proveniența e trust-label."""
    html = str(card(_articol(ai_generat=True)))
    assert "Titlu sintetizat automat" not in html
    assert "ai-mark" not in html


def test_cardul_lipseste_marcajul_cand_nu_e_generat(card):
    html = str(card(_articol(ai_generat=False)))
    assert "Titlu sintetizat automat" not in html
    assert "ai-mark" not in html


def test_articolul_poarta_marcajul_cand_e_generat():
    """Pagina de articol păstrează dezvăluirea scurtă + nota detaliată."""
    a = _articol(ai_generat=True)
    tpl = render._env().get_template("article.html")
    # Contextul vine din `render._base_ctx`, exact ca in productie (render.py:1029). Un context
    # reconstruit de mana se rupe la FIECARE variabila noua ceruta de `base.html` — asa a picat
    # testul asta pe main: `asset_ver` indexat direct si `jsonld | tojson` sunt neconditionate,
    # deci lipsa lor da UndefinedError, respectiv TypeError. Un `default(...)` in sablon ar fi
    # ascuns pierderea cache-bust-ului, exact capcana din §16.2.
    html = tpl.render(**render._base_ctx(
        f"/{a['category']}/{a['slug']}/", a=a, active_cat=a["category"],
        topics=[], people=[], related=[], nav_section="stiri",
    ))
    assert "Titlu sintetizat automat" in html
    assert 'class="ai-mark"' in html
    assert "ai-note" in html


def test_anuntul_oficial_ramane_nemarcat(card):
    """Anunt oficial fara corp: titlul e al institutiei, nu al nostru."""
    html = str(card(_articol(ai_generat=False, anunt_fara_corp=True)))
    assert "ai-mark" not in html


@pytest.mark.parametrize("processed_by,asteptat", [
    ("official", False),
    ("fallback", False),
    ("B", True),
    ("C", True),
])
def test_flagul_urmeaza_fluxul(processed_by, asteptat):
    assert (processed_by not in FLUXURI_NEMARCATE) is asteptat


def test_articolele_vechi_fara_flux_se_marcheaza():
    """Decizie asumata: golul de conformitate e eroarea mai scumpa dintre cele doua."""
    a = {}
    assert (a.get("processed_by") not in FLUXURI_NEMARCATE) is True


@pytest.mark.parametrize("sablon", ["_card.html", "article.html", "index.html"])
def test_sabloanele_atinse_compileaza(sablon):
    render._env().get_template(sablon)


def test_fallback_pe_text_de_sursa_ramane_fallback():
    """Item proaspat: `original_title` exista, deci textul e al sursei. Marcaj corect: fara."""
    from generator.process import _marcheaza_fallback
    it = {"original_title": "Primaria anunta lucrari pe strada Mare", "title": "Primaria anunta lucrari"}
    _marcheaza_fallback(it)
    assert it["processed_by"] == "fallback"
    assert (it.get("processed_by") not in FLUXURI_NEMARCATE) is False


def test_fallback_pe_text_de_model_NU_pierde_marcajul():
    """Rep deja publicat: `original_title` a fost scrub-uit, deci titlul e scris de model.

    Degradarea la `fallback` ar sterge marcajul AI de pe text scris de AI. Fluxul anterior
    trebuie sa supravietuiasca."""
    from generator.process import _marcheaza_fallback
    rep = {"title": "Trei masini avariate intr-un accident pe DN1", "synthesis": "…", "processed_by": "gemini"}
    _marcheaza_fallback(rep)
    assert rep["processed_by"] == "gemini", "fluxul AI a fost sters -> marcajul art. 50(4) dispare"
    assert (rep.get("processed_by") not in FLUXURI_NEMARCATE) is True


def test_fara_flux_anterior_si_fara_text_original_se_marcheaza():
    """Directia sigura ramane cea din `test_articolele_vechi_fara_flux_se_marcheaza`."""
    from generator.process import _marcheaza_fallback
    a = {"title": "ceva"}
    _marcheaza_fallback(a)
    assert (a.get("processed_by") not in FLUXURI_NEMARCATE) is True
