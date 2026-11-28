"""Semnul „Subiect greu” apare pe card doar la titluri despre moarte/violență; nu ascunde nimic."""
from generator import render


def _card(a: dict) -> str:
    env = render._env()
    tpl = env.from_string("{% from '_card.html' import card with context %}{{ card(a) }}")
    return tpl.render(a=a, base="")


def _art(titlu: str, categorie: str = "local") -> dict:
    return {"title": titlu, "category": categorie, "slug": "x", "teaser": "Rezumat.",
            "source_name": "Sursa", "original_link": "https://example.com/x",
            "published": "2026-11-28T10:00:00+00:00", "published_human": "azi"}


def test_cardul_greu_are_semn_si_ramane_cu_titlu_si_link():
    html = _card(_art("Doi tineri au murit într-un accident la Arad"))
    assert "Subiect greu" in html
    assert 'href="/local/x/"' in html
    assert "Doi tineri au murit" in html


def test_cardul_obisnuit_nu_are_semn():
    assert "Subiect greu" not in _card(_art("Primăria a deschis un parc nou în Iași"))
    assert "Subiect greu" not in _card(_art("Masacru pe bursă după raportul băncii", "economic"))
