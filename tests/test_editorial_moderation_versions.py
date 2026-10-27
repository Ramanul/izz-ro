"""Tests for public moderation footprint and non-destructive synthesis versions (E4)."""
from generator import config, editorial, moderation, publication, render


def test_moderation_accepts_reason_and_motiv():
    valid = moderation._validate({
        **moderation.DEFAULTS,
        "corrections": {
            "https://example.test/stire": {
                "title": "Titlu Corectat",
                "motiv": "rectificare oficială comunicat",
            }
        }
    })
    assert "https://example.test/stire" in valid["corrections"]


def test_moderation_apply_sets_footprint_and_initial_version():
    art = {
        "url": "https://example.test/stire",
        "title": "Titlu Vechi",
        "teaser": "Teaser Vechi",
        "synthesis": "Sinteză Veche",
        "model": "C",
    }
    mod = {
        **moderation.DEFAULTS,
        "corrections": {
            "https://example.test/stire": {
                "title": "Titlu Nou",
                "synthesis": "Sinteză Nouă",
                "motiv": "cifră rectificată de minister",
            }
        }
    }
    applied = moderation.apply([art.copy()], mod)
    assert len(applied) == 1
    res = applied[0]
    assert res["title"] == "Titlu Nou"
    assert res["synthesis"] == "Sinteză Nouă"
    assert res["teaser"] == "Teaser Vechi"
    assert res["moderation_note"] == "cluster ajustat manual: cifră rectificată de minister"
    assert res["initial_version"] == {
        "title": "Titlu Vechi",
        "teaser": "Teaser Vechi",
        "synthesis": "Sinteză Veche",
    }


def test_publication_apply_preserves_initial_version():
    art = {
        "model": "B",
        "category": "politic",
        "slug": "test-versioning",
        "title": "Titlu Original din Stare",
        "teaser": "Teaser Original din Stare",
        "original_link": "https://primaria.example/anunt/",
        "source_name": "Primăria",
        "url": "https://primaria.example/anunt/",
        "source": "pl_arad_primarie",
        "published": "2026-10-20T10:00:00Z",
    }
    row = {
        "key": editorial.annotation_key(art),
        "public_paths": [editorial.public_path(art)],
        "state": "corrected",
        "notice": "Rectificare număr participanți.",
        "evidence_url": "https://primaria.example/erata/",
        "review": {
            "state": "approved",
            "kind": "documentary",
            "reviewer": "test-reviewer",
            "reviewed_at": "2026-10-25T12:00:00Z",
            "input_fingerprint": editorial.source_fingerprint(art),
        },
        "presentation": {
            "title": "Titlu Corectat și Verificat",
        },
    }
    applied = publication.apply([art], {row["key"]: row})
    assert len(applied) == 1
    res = applied[0]
    assert res["title"] == "Titlu Corectat și Verificat"
    assert res["initial_version"]["title"] == "Titlu Original din Stare"
    assert res["initial_version"]["teaser"] == "Teaser Original din Stare"


def test_article_template_renders_moderation_note():
    env = render._env()

    art = {
        "model": "C",
        "category": "politic",
        "slug": "test-slug",
        "title": "Titlu Sinteză",
        "display_title": "Titlu Sinteză",
        "published": "2026-10-25T10:00:00Z",
        "published_human": "25 octombrie 2026",
        "moderation_note": "cluster ajustat manual: verificare oficială la cerere",
        "url": "https://exemplu.ro/stire",
    }

    ctx = render._base_ctx("/politic/test-slug/", a=art)
    rendered = env.get_template("article.html").render(**ctx)

    assert "cluster ajustat manual: verificare oficială la cerere" in rendered
    assert "class=\"notice moderation-notice\"" in rendered


def test_card_template_renders_moderation_note():
    env = render._env()

    art = {
        "model": "C",
        "category": "economic",
        "slug": "cluster-ajustat",
        "title": "Titlu Cluster",
        "display_title": "Titlu Cluster",
        "synthesis": "Sinteză Cluster",
        "published": "2026-10-25T10:00:00Z",
        "published_human": "25 octombrie 2026",
        "moderation_note": "cluster ajustat manual: corectură cifră BNR",
        "url": "https://exemplu.ro/bnr",
        "sources": [{"name": "BNR", "url": "https://bnr.ro"}],
    }

    tpl = env.from_string("{% import '_card.html' as c %}{{ c.card(a) }}")
    rendered = tpl.render(a=art, base=config.SITE["url"])

    assert "cluster ajustat manual: corectură cifră BNR" in rendered
    assert "class=\"moderation-note\"" in rendered
