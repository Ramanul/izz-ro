"""Rubrica geografica se decide din TEXT, la orice sursa (owner 2026-08-02): LOCAL =
unde se intampla, nu cine publica. Vezi process._resolve_category."""
from generator import config
from generator.process import _resolve_category


def test_local_source_no_place_leaves_to_ai_topic():
    # Ziar judetean, dar textul (gol aici) nu numeste niciun loc -> pleaca pe tema AI.
    item = {"category": "local", "source": "stiridecluj"}
    assert _resolve_category(item, "sport") == "sport"


def test_non_local_source_follows_ai_category():
    item = {"category": "general", "source": "digi24"}
    assert _resolve_category(item, "economic") == "economic"


def test_non_local_source_invalid_ai_falls_back_to_source():
    item = {"category": "politic", "source": "g4media"}
    assert _resolve_category(item, "inexistent") == "politic"


def test_pinned_categories_are_subset_of_categories():
    assert config.PINNED_CATEGORIES <= set(config.CATEGORIES)
