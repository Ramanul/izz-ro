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
