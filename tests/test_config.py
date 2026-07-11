"""Validarea configului: surse complete, categorii consistente, praguri sane."""
from slugify import slugify

from generator import config


def test_sources_have_required_fields_and_valid_category():
    for key, src in config.SOURCES.items():
        assert src.get("name"), key
        assert str(src.get("url", "")).startswith("http"), key
        assert src.get("category") in config.CATEGORIES, key


def test_agency_blocklist_is_lowercase():
    assert all(d == d.lower() for d in config.AGENCY_BLOCKLIST)


def test_thresholds_sane():
    assert config.ARTICLE_TTL_DAYS > 0
    assert config.CLUSTER_MIN_SOURCES >= 2
    assert 0 < config.TEASER_MAX_WORDS < config.SYNTHESIS_MAX_WORDS


def test_slugify_romanian_titles_are_urlsafe():
    s = slugify("Șefa BNR anunță măsuri: dobânzi & inflație (2026)!")[:80]
    assert s and all(c.isalnum() or c == "-" for c in s)
