from __future__ import annotations

import pytest

from generator import moderation


def test_validate_rejects_unknown_key():
    with pytest.raises(moderation.ModerationConfigCorrupt):
        moderation._validate({**moderation.DEFAULTS, "unexpected": True})


def test_validate_rejects_wrong_types():
    with pytest.raises(moderation.ModerationConfigCorrupt):
        moderation._validate({**moderation.DEFAULTS, "hold_important": "true"})
    with pytest.raises(moderation.ModerationConfigCorrupt):
        moderation._validate({**moderation.DEFAULTS, "blocklist_keywords": ["ok", 1]})


def test_validate_accepts_repo_shape():
    value = moderation._validate({
        "blocklist_urls": [],
        "blocklist_keywords": ["torrent"],
        "suppress_sources": ["example"],
        "corrections": {"https://example.test/a": {"title": "Corect"}},
        "featured": [],
        "hold_important": False,
        "approved": [],
    })
    assert value["blocklist_keywords"] == ["torrent"]


def test_human_gate_env_invalid_is_fail_closed(monkeypatch):
    monkeypatch.setenv(moderation.REQUIRE_HUMAN_GATE_ENV, "yes")
    with pytest.raises(moderation.ModerationConfigCorrupt):
        moderation._human_gate_required()


def test_human_gate_env_true_requires_approval_for_model_c(monkeypatch):
    monkeypatch.setenv(moderation.REQUIRE_HUMAN_GATE_ENV, "true")
    article = {
        "url": "https://example.test/c",
        "original_title": "Alfa Beta Gamma",
        "title": "Alfa Beta Gamma",
        "model": "C",
        "published": "2026-09-05T08:00:00+00:00",
        "sources": [{"url": "https://example.test/source"}],
    }
    result = moderation.apply([article.copy()], moderation.DEFAULTS)
    assert result == []


def test_human_gate_env_true_allows_explicit_approval(monkeypatch):
    monkeypatch.setenv(moderation.REQUIRE_HUMAN_GATE_ENV, "true")
    url = "https://example.test/c"
    article = {
        "url": url,
        "original_title": "Alfa Beta Gamma",
        "title": "Alfa Beta Gamma",
        "model": "C",
        "published": "2026-09-05T08:00:00+00:00",
        "sources": [{"url": "https://example.test/source"}],
    }
    result = moderation.apply([article.copy()], {**moderation.DEFAULTS, "approved": [url]})
    assert len(result) == 1
    assert result[0]["url"] == url
