"""Parsarea raspunsurilor JSON de la provider (regresie: Gemini 3.x poate
impacheta obiectul intr-o lista -> AttributeError 'list' has no 'get',
build-urile din 2026-07-24)."""
from generator.process import (
    _cross_item_contamination,
    _parse_json,
    _parse_json_array,
    _synthesis_title_is_supported,
)


def test_parse_json_plain_object():
    assert _parse_json('{"title": "T"}') == {"title": "T"}


def test_parse_json_list_wrapped_object():
    assert _parse_json('[{"title": "T"}]') == {"title": "T"}


def test_parse_json_fenced():
    assert _parse_json('```json\n{"title": "T"}\n```') == {"title": "T"}


def test_parse_json_garbage_returns_empty_dict():
    assert _parse_json("nu e json") == {}
    assert _parse_json("[1, 2, 3]") == {}


def test_parse_json_array_accepts_dict_wrapping():
    assert _parse_json_array('{"items": [{"a": 1}]}') == [{"a": 1}]


def test_cross_item_contamination_rejects_foreign_fact_anchor():
    own = "Apple schimbă regulile pentru dezvoltatorii din Uniunea Europeană."
    peer = "PESA depune oferta pentru trenurile metropolitane din Cluj."
    candidate = "Apple modifică regulile pentru aplicații, iar PESA depune oferta pentru trenurile din Cluj."
    assert _cross_item_contamination(candidate, own, [peer]) is True


def test_cross_item_contamination_allows_supported_summary():
    own = "Apple schimbă regulile pentru aplicații și dezvoltatori în Uniunea Europeană."
    peer = "PESA depune oferta pentru trenurile metropolitane din Cluj."
    candidate = "Apple modifică regulile pentru aplicații și dezvoltatori în Uniunea Europeană."
    assert _cross_item_contamination(candidate, own, [peer]) is False


def test_synthesis_title_rejects_identity_claim_rewritten_as_feeling():
    context = (
        "Suspecții au pretins că sunt lucrători antidrog și s-au dat drept polițiști "
        "pentru a opri o autoutilitară."
    )
    assert _synthesis_title_is_supported(
        "Doi bărbați, arestați după ce au simțit polițiști antidrog", context
    ) is False


def test_synthesis_title_allows_supported_identity_claim():
    context = "Suspecții au pretins că sunt lucrători antidrog și s-au dat drept polițiști."
    assert _synthesis_title_is_supported(
        "Doi bărbați, arestați după ce s-au dat drept polițiști antidrog", context
    ) is True
