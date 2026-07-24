"""Parsarea raspunsurilor JSON de la provider (regresie: Gemini 3.x poate
impacheta obiectul intr-o lista -> AttributeError 'list' has no 'get',
build-urile din 2026-07-24)."""
from generator.process import _parse_json, _parse_json_array


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
