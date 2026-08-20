"""Marcajul AI Act art. 50(4) — apare pe articolele generate, lipseste pe celelalte.

DE CE EXISTA: marcajul a fost scris pe 2026-08-17 in 5 fisiere si predat NERULAT. Suita de
atunci (934 de teste) trecea, dar niciun test nu atingea elementul nou — deci "testele trec"
nu putea distinge "marcajul apare" de "marcajul lipseste complet". Fisierul asta inchide gaura.

CE ACOPERA: randarea reala a macro-ului `card()` cu mediul Jinja din `render._env()`, plus
expresia care decide flagul. CE NU ACOPERA: aspectul vizual, CSS-ul, pagina completa.

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


def test_marcajul_apare_cand_e_generat(card):
    html = str(card(_articol(ai_generat=True)))
    assert "Titlu sintetizat automat" in html
    assert 'class="ai-mark"' in html


def test_marcajul_lipseste_cand_nu_e_generat(card):
    html = str(card(_articol(ai_generat=False)))
    assert "Titlu sintetizat automat" not in html
    assert "ai-mark" not in html


def test_marcajul_sta_in_meta_nu_in_badge(card):
    """Eticheta aurie `.badge` e eyebrow de CATEGORIE; o dezvaluire pusa acolo s-ar citi ca tema."""
    html = str(card(_articol(ai_generat=True)))
    assert html.find('class="ai-mark"') > html.find('class="meta"')
    assert html.find('class="ai-mark"') > html.find('class="badge')


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


# --- gaura inchisa 2026-08-20 (audit, [C1]) -------------------------------------------------
# Testele de mai sus verifica MAPAREA `processed_by -> ai_generat`. Nu verificau de unde vine
# textul pe care il descrie fluxul. Pe reprezentantii deja publicati, textul original e sters de
# `state._scrub_processed`, deci calea fara provider pastra titlul si sinteza scrise de model si
# le marca `fallback` -> `ai_generat=False` -> text de AI publicat fara marcajul art. 50(4).

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
