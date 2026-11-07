"""Teste pentru E1 — metadată secă de editor / grup media și alinierea transparenței."""
from __future__ import annotations

import os
import pytest
from jinja2 import Environment

from generator import config, render, source_publishers


def test_registrul_editorilor_e_valid_si_corespunde_surselor_configurate():
    pubs = source_publishers.load()
    assert len(pubs) >= 20  # 9 înregistrări ascunse până la verificare manuală (vezi PR)
    domenii_configurate = {
        source_publishers.canonical_domain(meta["url"])
        for meta in config.SOURCES.values()
    }
    for dom, rec in pubs.items():
        assert dom in domenii_configurate, f"{dom} nu corespunde niciunei surse din config.SOURCES"
        assert rec["evidence_url"].startswith("https://")
        assert rec["label"]


def test_garda_anti_evaluare_respinge_judecatile_de_valoare():
    baza = {
        "publisher": "Exemplu Media S.R.L.",
        "group": None,
        "funding_note": None,
        "evidence_url": "https://exemplu.ro/termeni",
        "verified_at": "2026-11-07",
    }
    for interzis in (
        "Publicație independentă",
        "Sursă de încredere",
        "Presă credibilă",
        "Tabloid comercial",
        "Grup partizan",
    ):
        with pytest.raises(ValueError, match="evaluativ"):
            source_publishers.validate_record("exemplu.ro", {**baza, "funding_note": interzis})
    with pytest.raises(ValueError, match="https://"):
        source_publishers.validate_record("exemplu.ro", {**baza, "evidence_url": "http://exemplu.ro/t"})


def test_grupuri_comune_apar_doar_la_cel_putin_doua_publicatii():
    pubs = source_publishers.load()
    assert source_publishers.shared_groups(
        [{"name": "G4Media", "url": "https://www.g4media.ro/x"}], pubs,
    ) == []
    assert source_publishers.shared_groups(
        [
            {"name": "G4Media", "url": "https://www.g4media.ro/x"},
            {"name": "HotNews", "url": "https://hotnews.ro/y"},
        ],
        pubs,
    ) == []
    comune = source_publishers.shared_groups(
        [
            {"name": "G4Media", "url": "https://www.g4media.ro/x"},
            {"name": "Economedia", "url": "https://economedia.ro/y"},
        ],
        pubs,
    )
    # Economedia (Grupul ARCMEDIA) e ascunsă până la verificare: grupul nu apare comun acum.
    assert comune == []


def test_catalogul_surse_ataseaza_editorul_doar_unde_exista_act_verificat():
    cat, _, _ = render._source_catalog([])
    toate = {}
    for g in cat:
        for s in g["with_stats"] + g["without_stats"]:
            toate[s["name"]] = s
        for r in g.get("regions", []):
            for c in r["counties"]:
                for s in c["with_stats"] + c["without_stats"]:
                    toate[s["name"]] = s

    assert "publisher_info" not in toate["Digi24"]  # ascunsă până la verificare manuală
    assert toate["BBC Europe"]["url"] == "https://bbc.co.uk/"
    assert "British Broadcasting Corporation" in toate["BBC Europe"]["publisher_info"]["label"]
    assert toate["DW Europe"]["url"] == "https://dw.com/"
    assert toate["Timiș Online"]["publisher_info"]["group"] == "Russmedia"
    # Domeniu neexaminat / primărie: nicio etichetă ghicită
    assert "publisher_info" not in toate["Caon.ro"]


def test_randare_grup_comun_in_article_html():
    env: Environment = render._env()
    tpl = env.get_template("article.html")
    art = {
        "title": "Știre de test",
        "slug": "stire-test",
        "category": "economie",
        "model": "C",
        "published": "2026-11-07T08:00:00+00:00",
        "url": "https://www.g4media.ro/x",
        "source": "G4Media",
        "sources": [
            {"name": "G4Media", "url": "https://www.g4media.ro/x"},
            {"name": "Economedia", "url": "https://economedia.ro/y"},
        ],
        "synthesis": "Rezumat scurt.",
    }
    fara_grup = tpl.render(**render._base_ctx(
        "/economie/stire-test/", a=art, active_cat="economie",
        topics=[], people=[], arhiva=None, related=[], og_image=None,
        grupuri_comune=[],
    ))
    assert "Același grup media" not in fara_grup

    cu_grup = tpl.render(**render._base_ctx(
        "/economie/stire-test/", a=art, active_cat="economie",
        topics=[], people=[], arhiva=None, related=[], og_image=None,
        grupuri_comune=[{"group": "Grupul ARCMEDIA", "members": ["Economedia", "G4Media"]}],
    ))
    assert "Același grup media (din casetele editoriale verificate): Economedia, G4Media — Grupul ARCMEDIA." in cu_grup


def test_method_md_si_index_html_sunt_aliniate_la_article_ttl_days():
    with open(os.path.join(config.ROOT, "content", "legal", "method.md"), encoding="utf-8") as fh:
        method = fh.read()
    assert f"pe {config.ARTICLE_TTL_DAYS} zile" in method
    assert f"fereastra de {config.ARTICLE_TTL_DAYS} zile" in method
    assert "12 zile" not in method
    assert "23 octombrie 2026" not in method
    assert "/corectii/feed.xml" in method

    with open(os.path.join(config.ROOT, "templates", "index.html"), encoding="utf-8") as fh:
        idx = fh.read()
    assert "{{ ttl_days }} zile" in idx
    assert "12 zile" not in idx
