"""Contractele din planul de pe 8 octombrie, fara randare completa.

Nu urca TTL-ul si nu verifica oglinda live. Asta e codul care se poate dovedi local.
"""
from datetime import datetime, timedelta, timezone

import pytest

from generator import config, process, render, state


def test_gridul_nu_depaseste_ecranul_de_320():
    css = open("static/styles.css", encoding="utf-8").read()
    assert "minmax(min(310px, 100%), 1fr)" in css
    assert "minmax(310px, 1fr)" not in css


def test_subnavul_nu_e_sticky_pe_mobil():
    css = open("static/styles.css", encoding="utf-8").read()
    bloc = css.split("@media (max-width: 720px)", 1)[1].split("@media", 1)[0]
    assert ".site-header-group { position: static; }" in bloc


def test_process_cluster_pune_members_si_story_id():
    grup = [
        {"url": "https://a.ro/1", "original_link": "https://a.ro/1", "source_name": "A",
         "title": "Titlu vechi", "published": "2026-08-04T05:00:00+00:00", "source_lang": "ro"},
        {"url": "https://b.ro/2", "original_link": "https://b.ro/2", "source_name": "B",
         "title": "Titlu nou", "published": "2026-08-04T06:00:00+00:00", "source_lang": "ro"},
    ]
    rep = process.process_cluster(grup, None)
    assert rep["model"] == "C"
    assert rep["story_id"].startswith("st-")
    assert rep["members"]
    assert {m["url"] for m in rep["members"]} == {"https://a.ro/1", "https://b.ro/2"}


def test_repararea_nu_inventeaza_timeline_si_nu_redenumeste():
    vechi = {"model": "C", "url": "https://a.ro/1", "title": "T", "source_name": "A",
             "published": "2026-08-04T05:00:00+00:00", "story_id": "st-pastrat"}
    gol = {"model": "C", "url": "https://b.ro/2", "title": "U", "source_name": "B",
           "published": "2026-08-04T06:00:00+00:00"}
    n = process.repara_identitate_cluster([vechi, gol, {"model": "B", "url": "https://c.ro/3"}])
    assert vechi["story_id"] == "st-pastrat"
    assert "members" not in vechi or vechi.get("members")
    assert gol["story_id"].startswith("st-")
    assert gol["members"] == [{
        "published": gol["published"], "title": "U", "source": "B", "url": "https://b.ro/2",
    }]
    assert n == 3  # story_id + members pe gol, members pe vechi


def test_merge_uneste_variantele_de_tracking():
    existing = [{"url": "https://exemplu.ro/a", "title": "pastrat"}]
    new = [{"url": "https://exemplu.ro/a?utm_source=newsletter", "title": "duplicat"}]
    out = state.merge(existing, new)
    assert len(out) == 1
    assert out[0]["title"] == "pastrat"


def test_sitemapul_foloseste_updated_nu_doar_published():
    publicat = datetime(2026, 8, 1, tzinfo=timezone.utc)
    actualizat = publicat + timedelta(days=2)
    art = {"category": "general", "slug": "sinteza", "title": "T",
           "published": publicat.isoformat(), "updated": actualizat.isoformat()}
    assert render._zi_modificare(art) == "2026-08-03"


def test_pagina_2_si_404_nu_se_indexeaza_ca_pagina_de_aterizare():
    doi = render._env().get_template("category.html").render(**render._base_ctx(
        "/sport/2/", category="sport", articles=[], noindex=True))
    assert "noindex, follow" in doi
    assert 'href="https://izz.ro/sport/2/"' in doi
    patru = render._env().get_template("category.html").render(**render._base_ctx(
        "/404.html", category="Pagina negăsită", articles=[], noindex=True, canonical=""))
    assert "noindex, follow" in patru
    assert 'rel="canonical"' not in patru


def test_judetul_are_link_in_html_inainte_de_js():
    stiri = [{
        "category": "local", "slug": "podul", "title": "Podul",
        "source": "pr_buzau", "source_name": "Primăria Buzău",
        "published_human": "8 octombrie",
    }]
    html = render._html_lista_stiri(render._stiri_pentru_judet(stiri, "BUZAU"))
    assert 'href="/local/podul/"' in html
    assert "Primăria Buzău" in html
    assert "Se încarcă" not in html


def test_feedul_spune_categoria_si_sursa_si_nu_pune_coperta_de_categorie():
    art = {"title": "T", "slug": "t", "category": "local", "model": "B",
           "published": "2026-08-06T07:30:00+00:00", "teaser": "corp",
           "source_name": "Primăria", "original_link": "https://primarie.ro/a",
           "cover_url": "https://izz.ro/og/local.jpg", "cover_propriu": False}
    xml = render._feed_xml([art], "T", "https://izz.ro", "D")
    assert "<category>local</category>" in xml
    assert "Primăria" in xml
    assert "media:content" not in xml
    art["cover_propriu"] = True
    xml = render._feed_xml([art], "T", "https://izz.ro", "D")
    assert "media:content" in xml
    assert "https://izz.ro/og/local.jpg" in xml


def test_ghidul_se_leaga_de_stire_fara_potrivire_vaga():
    index = render._index_ghiduri()
    gasit = render._ghid_pentru(
        {"title": "Guvernul a majorat salariul minim de la 1 iulie", "teaser": ""}, index)
    assert gasit and gasit["id"] == "salariul-minim"
    assert render._ghid_pentru({"title": "O știre despre vreme", "teaser": "ploaie"}, index) is None


def test_timeline_doar_cu_trei_domenii_pe_modelul_c():
    doi = {"model": "C", "members": [
        {"url": "https://a.ro/1", "published": "2026-10-01"},
        {"url": "https://b.ro/2", "published": "2026-10-02"},
    ]}
    assert render._timeline(doi) is None
    trei = {"model": "C", "members": [
        {"url": "https://c.ro/3", "published": "2026-10-03", "title": "C"},
        {"url": "https://a.ro/1", "published": "2026-10-01", "title": "A"},
        {"url": "https://b.ro/2", "published": "2026-10-02", "title": "B"},
    ]}
    ordine = [m["title"] for m in render._timeline(trei)]
    assert ordine == ["A", "B", "C"]
    assert render._timeline(dict(trei, model="B")) is None


def test_save_refuza_sinteza_c_ramasa_fara_story_id(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "STATE_PATH", str(tmp_path / "articles.json"))
    monkeypatch.setattr("generator.process.repara_identitate_cluster", lambda articole: 0)
    with pytest.raises(RuntimeError, match="story_id"):
        state.save([{"model": "C", "url": "https://a.ro/1", "title": "T"}])


def test_ecranul_intai_taie_cardurile_in_sablon_nu_in_css():
    css = open("static/styles.css", encoding="utf-8").read()
    assert ".grid .home-extra { display: none; }" not in css
    index = open("templates/index.html", encoding="utf-8").read()
    assert "items[:2]" in index
    assert 'template class="home-wide"' in index
    assert "Ce s-a întâmplat azi" in index
    assert 'id="judet-meu"' in index
    assert 'href="{{ base }}/azi/"' in index
    articol = open("templates/article.html", encoding="utf-8").read()
    assert "a.timeline" in articol and "a.ghid" in articol


def test_briefingul_de_azi_nu_inventeaza_text(monkeypatch):
    class _Acum(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 8, 12, 0, tzinfo=tz)

    monkeypatch.setattr(render, "datetime", _Acum)
    articole = [
        {"title": "Azi", "slug": "azi", "category": "social",
         "published": "2026-10-08T08:00:00+00:00", "model": "B"},
        {"title": "Ieri", "slug": "ieri", "category": "social",
         "published": "2026-10-07T08:00:00+00:00", "model": "B"},
    ]
    alese = render._briefing_de_azi(articole)
    assert [a["title"] for a in alese] == ["Azi"]
