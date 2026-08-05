"""Slug-ul se atribuie O SINGURA DATA si intra in stare — permalink stabil.

Pana acum `assign_slugs` recalcula slug-ul din titlu la FIECARE randare si nu-l salva
nicaieri, pentru ca rula in `render.build`, adica dupa `state.save`. Cat timp titlurile nu
se schimbau, nimeni nu observa. Se schimba insa in doua cazuri reale: un bump de
`PROMPT_VERSION` reproceseaza articolele B (`upgrade_fallbacks`), iar decizia IZZ-0151 cere
ca o sinteza C sa se ACTUALIZEZE cand absoarbe o stire noua — cu titlu nou, dar cu acelasi
permalink. Fara slug persistat, fiecare astfel de rescriere muta URL-ul unei pagini deja
indexate.
"""
import json

import pytest

from generator import main, render, state


def test_slugul_stocat_supravietuieste_schimbarii_de_titlu():
    arts = [{"slug": "titlul-de-la-prima-publicare", "category": "extern",
             "title": "Sinteza s-a actualizat si titlul e cu totul altul"}]
    render.assign_slugs(arts)
    assert arts[0]["slug"] == "titlul-de-la-prima-publicare"


def test_articolul_fara_slug_il_primeste_din_titlu_ca_pana_acum():
    arts = [{"title": "Guvernul a aprobat bugetul pe 2026", "category": "politic"}]
    render.assign_slugs(arts)
    assert arts[0]["slug"] == "guvernul-a-aprobat-bugetul-pe-2026"


def test_slugul_stocat_isi_rezerva_locul_iar_noul_titlu_primeste_sufixul():
    """Ordinea conteaza: daca articolul nou ar fi servit primul, ar fi furat slug-ul
    unei pagini deja publicate si ar fi suprascris-o la randare."""
    arts = [{"slug": "acelasi-titlu", "category": "extern", "title": "Alt titlu intre timp"},
            {"title": "Acelasi titlu", "category": "extern"}]
    render.assign_slugs(arts)
    assert [a["slug"] for a in arts] == ["acelasi-titlu", "acelasi-titlu-2"]


def test_numerotarea_ramane_cea_de_dinainte_cand_nimic_nu_e_stocat():
    arts = [{"title": "Acelasi titlu", "category": "extern"},
            {"title": "Acelasi titlu", "category": "extern"},
            {"title": "Acelasi titlu", "category": "extern"}]
    render.assign_slugs(arts)
    assert [a["slug"] for a in arts] == ["acelasi-titlu", "acelasi-titlu-2", "acelasi-titlu-3"]


def test_a_doua_atribuire_nu_schimba_nimic():
    arts = [{"title": "Stire oarecare", "category": "extern"},
            {"title": "Stire oarecare", "category": "extern"}]
    render.assign_slugs(arts)
    inainte = [a["slug"] for a in arts]
    render.assign_slugs(arts)
    assert [a["slug"] for a in arts] == inainte


@pytest.fixture
def ruleaza(tmp_path, monkeypatch):
    """`main.run` complet (deci CU save), fara retea, fara AI si fara randare pe disc."""
    p = tmp_path / "articles.json"
    p.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(state, "STATE_PATH", str(p))
    monkeypatch.setattr(main, "get_provider", lambda: None)
    monkeypatch.setattr(render, "build", lambda *a, **k: None)

    def _run(items):
        monkeypatch.setattr(main.fetch, "fetch_all", lambda: (items, []))
        main.run(dry_run=False)
        return json.loads(p.read_text(encoding="utf-8"))
    return _run


def _item(url: str, titlu: str) -> dict:
    return {"url": url, "source": "test_src", "source_name": "Test", "title": titlu,
            "original_title": titlu, "description": "", "category": "extern", "model": None,
            "published": "2099-01-01T10:00:00+00:00"}


def test_slugul_ajunge_in_articles_json_si_nu_se_mai_schimba(ruleaza):
    stare = ruleaza([_item("https://x.ro/a", "Un titlu de proba")])
    assert len(stare) == 1
    assert stare[0]["slug"] == "un-titlu-de-proba"

    # a doua rulare, fara iteme noi, dar cu titlul rescris in stare (cazul sintezei
    # actualizate): slug-ul trebuie sa ramana cel de la prima publicare
    stare[0]["title"] = "Titlu complet diferit dupa actualizare"
    import os
    with open(state.STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(stare, fh, ensure_ascii=False)
    assert os.path.exists(state.STATE_PATH)

    stare2 = ruleaza([])
    assert stare2[0]["title"] == "Titlu complet diferit dupa actualizare"
    assert stare2[0]["slug"] == "un-titlu-de-proba"
