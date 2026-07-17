"""Categoriile geografice (PINNED_CATEGORIES, ex. 'local') sunt o axa proprie:
AI-ul nu le muta pe axa de tema. Vezi process._resolve_category."""
from generator import config
from generator.process import _resolve_category


def test_local_source_stays_local_despite_ai_topic():
    # articol de la un ziar judetean: fetch pune category='local'; AI zice 'sport'
    item = {"category": "local", "source": "stiridecluj"}
    assert _resolve_category(item, "sport") == "local"


def test_non_local_source_follows_ai_category():
    item = {"category": "general", "source": "digi24"}
    assert _resolve_category(item, "economic") == "economic"


def test_non_local_source_invalid_ai_falls_back_to_source():
    item = {"category": "politic", "source": "g4media"}
    assert _resolve_category(item, "inexistent") == "politic"


def test_pinned_categories_are_subset_of_categories():
    assert config.PINNED_CATEGORIES <= set(config.CATEGORIES)
