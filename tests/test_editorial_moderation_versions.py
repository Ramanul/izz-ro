"""Tests for public moderation footprint and non-destructive synthesis versions (E4)."""
import copy
from datetime import datetime, timezone

import pytest

from generator import config, editorial, moderation, publication, render, state


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


def _article(model="B"):
    article = {
        "url": "https://example.test/stire",
        "title": "Participarea cetățenilor la ședința publică locală",
        "teaser": "La ședință au participat 120 de persoane.",
        "synthesis": "La ședință au participat 120 de persoane.",
        "model": model, "category": "local", "slug": "sedinta-publica",
        "published": datetime.now(timezone.utc).isoformat(),
    }
    if model == "C":
        article.update(story_id="version-test", dialectic={
            "state": "SYNTHESIS_VALID",
            "common": [{"text": article["synthesis"], "src": ["Primăria", "Consiliul"]}],
        })
    return article


def _record(article, **extra):
    return {
        "key": editorial.annotation_key(article),
        "public_paths": [editorial.public_path(article)], "state": "corrected",
        "notice": "Numărul participanților a fost rectificat.",
        "evidence_url": "https://example.test/rectificare/",
        "review": {"state": "approved", "kind": "documentary", "reviewer": "test-only",
                   "reviewed_at": "2026-10-28T12:00:00Z",
                   "input_fingerprint": editorial.source_fingerprint(article)},
        "presentation": {"synthesis": "La ședință au participat 12 persoane."},
        **extra,
    }


def _publish(article, record):
    return publication.apply([article], {record["key"]: record})[0]


def _html(article):
    return render._env().get_template("article.html").render(
        **render._base_ctx("/local/sedinta-publica/", a=article))


def test_initial_summary_survives_real_state_reruns(tmp_path, monkeypatch):
    article = _article()
    mod = {**moderation.DEFAULTS, "corrections": {
        article["url"]: {"title": "Primul titlu corectat al ședinței publice"}}}
    monkeypatch.setattr(state, "STATE_PATH", str(tmp_path / "articles.json"))
    rows = [article]
    original = {field: article[field] for field in ("title", "teaser", "synthesis")}
    for title in ("Primul titlu corectat al ședinței publice",
                  "Al doilea titlu corectat al ședinței publice"):
        mod["corrections"][article["url"]]["title"] = title
        moderation.apply(rows, mod)
        state.save(rows)
        rows = state.load()
        assert rows[0]["initial_version"] == original
        assert rows[0]["title"] == title


def test_publication_preserves_prior_moderation_snapshot_without_aliasing():
    article = _article()
    original = copy.deepcopy(article)
    mod = {**moderation.DEFAULTS, "corrections": {
        article["url"]: {"title": "Titlul ajustat manual înaintea corecției"}}}
    moderated = moderation.apply([article], mod)[0]
    before = copy.deepcopy(moderated)
    view = _publish(moderated, _record(moderated))
    assert moderated == before
    assert view["initial_version"]["title"] == original["title"]
    view["initial_version"]["title"] = "Independent copy"
    assert moderated["initial_version"]["title"] == original["title"]


@pytest.mark.parametrize("mechanism", ["moderation", "publication"])
def test_structured_body_is_invalidated_when_summary_is_corrected(mechanism):
    article = _article("C")
    corrected = "La ședință au participat 12 persoane."
    if mechanism == "moderation":
        mod = {**moderation.DEFAULTS, "corrections": {
            article["url"]: {"synthesis": corrected}}}
        view = moderation.apply([article], mod)[0]
    else:
        view = _publish(article, _record(article))
    html = _html(view)
    assert 'class="dialectic"' not in html
    assert corrected in html
    assert "120 de persoane" not in html


def test_manual_correction_does_not_recreate_old_claim_in_source_timeline(monkeypatch):
    article = _article("C")
    article["members"] = [
        {"url": f"https://{domain}.test/stire", "title": "Au participat 120 de persoane",
         "published": article["published"], "source": domain}
        for domain in ("one", "two", "three")
    ]
    assert len(render._timeline(article)) == 3
    mod = {**moderation.DEFAULTS, "corrections": {
        article["url"]: {"synthesis": "La ședință au participat 12 persoane."}}}
    view = moderation.apply([article], mod)[0]
    monkeypatch.setattr(render, "_index_ghiduri", lambda: [])
    monkeypatch.setattr(render, "_registru_memorie", lambda: [])
    render._ataseaza_legaturi([view])
    assert view["timeline"] is None
    html = _html(view)
    assert "La ședință au participat 12 persoane." in html
    assert "120 de persoane" not in html


@pytest.mark.parametrize("mechanism", ["moderation", "publication"])
@pytest.mark.parametrize("flag", [None, False, True])
def test_initial_summary_is_visible_only_with_explicit_opt_in(mechanism, flag):
    article = _article()
    extra = {} if flag is None else {"show_initial_version": flag}
    if mechanism == "moderation":
        mod = {**moderation.DEFAULTS, "corrections": {
            article["url"]: {"teaser": "La ședință au participat 12 persoane.", **extra}}}
        view = moderation.apply([article], mod)[0]
    else:
        record = _record(article, **extra)
        record["presentation"] = {"teaser": "La ședință au participat 12 persoane."}
        view = _publish(article, record)
    html = _html(view)
    assert ('class="version-toggle"' in html) is (flag is True)
    assert ("120 de persoane" in html) is (flag is True)
    if flag is True:
        assert "Rezumat înainte de corecție" in html
        assert 'data-pagefind-ignore="all"' in html


def test_persisted_opt_in_is_not_authority_when_manual_correction_is_removed():
    article = _article()
    article["initial_version"] = {field: article[field] for field in ("title", "teaser", "synthesis")}
    article["show_initial_version"] = True
    view = moderation.apply([article], moderation.DEFAULTS)[0]
    assert 'class="version-toggle"' not in _html(view)
    assert view.get("show_initial_version") is not True


@pytest.mark.parametrize("mechanism", ["moderation", "publication"])
@pytest.mark.parametrize("flag", [None, 0, 1, "true", [], {}])
def test_public_history_opt_in_requires_a_strict_boolean(mechanism, flag):
    article = _article()
    if mechanism == "moderation":
        mod = {**moderation.DEFAULTS, "corrections": {
            article["url"]: {"title": "Titlu nou verificat", "show_initial_version": flag}}}
        with pytest.raises(moderation.ModerationConfigCorrupt):
            moderation.apply([article], mod)
    else:
        with pytest.raises(editorial.EditorialError):
            _publish(article, _record(article, show_initial_version=flag))


@pytest.mark.parametrize("mechanism", ["moderation", "publication"])
@pytest.mark.parametrize("snapshot", [None, [], {"title": "incomplete"},
                                       {"title": "t", "teaser": "r", "synthesis": False}])
def test_corrupt_existing_snapshot_blocks_correction(mechanism, snapshot):
    article = _article()
    article["initial_version"] = snapshot
    with pytest.raises(editorial.EditorialError, match="initial_version"):
        if mechanism == "moderation":
            mod = {**moderation.DEFAULTS, "corrections": {
                article["url"]: {"title": "Titlul corectat al ședinței publice"}}}
            moderation.apply([article], mod)
        else:
            _publish(article, _record(article))


def test_initial_summary_is_escaped_and_not_part_of_news_source_fingerprint():
    article = _article()
    fingerprint = editorial.source_fingerprint(article)
    article["initial_version"] = {"title": "<script>alert(1)</script>",
                                  "teaser": "<img src=x onerror=alert(1)>", "synthesis": ""}
    article["show_initial_version"] = True
    assert editorial.source_fingerprint(article) == fingerprint
    record = _record(article, show_initial_version=True)
    html = _html(_publish(article, record))
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<img src=x onerror=alert(1)>" not in html
    record["review"]["input_fingerprint"] = "0" * 64
    with pytest.raises(editorial.EditorialError, match="source changed"):
        _publish(article, record)


def test_publication_record_controls_history_after_manual_opt_in():
    article = _article()
    mod = {**moderation.DEFAULTS, "corrections": {article["url"]: {
        "title": "Titlul corectat al ședinței publice", "show_initial_version": True}}}
    moderated = moderation.apply([article], mod)[0]
    view = _publish(moderated, _record(moderated))
    assert 'class="version-toggle"' not in _html(view)


def test_history_permission_changes_the_revision_signal():
    article = _article()
    record = _record(article)
    before = publication.revisions({record["key"]: record})
    record["show_initial_version"] = True
    after = publication.revisions({record["key"]: record})
    assert before["version"] != after["version"]
    record["show_initial_version"] = False
    assert publication.revisions({record["key"]: record}) == before


def test_withdrawal_and_takedown_never_expose_initial_summary(monkeypatch):
    article = _article()
    article["initial_version"] = {field: article[field] for field in ("title", "teaser", "synthesis")}
    article["show_initial_version"] = True
    row = _record(article, state="withdrawn", presentation={})
    assert publication.apply([article], {row["key"]: row}) == []
    html = render._env().get_template("withdrawn.html").render(**render._base_ctx(
        "/local/sedinta-publica/", correction=publication.public_notice(row), active_path=None, a=article))
    assert "120 de persoane" not in html
    assert "version-toggle" not in html
    row["show_initial_version"] = True
    with pytest.raises(editorial.EditorialError):
        publication.apply([article], {row["key"]: row})
    monkeypatch.setattr(moderation, "_inregistreaza_takedown", lambda entries: None)
    mod = {**moderation.DEFAULTS, "takedowns": {article["url"]: "Retragere de test"}}
    assert moderation.apply([article], mod) == []
